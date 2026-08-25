"""Zibal payment gateway integration and the record of received payments.

Flow (per Zibal's docs):
  1. request  -> POST /v1/request  with merchant, amount (RIAL), callbackUrl
                 => trackId
  2. start    -> send the user to https://gateway.zibal.ir/start/{trackId}
  3. callback -> Zibal calls our callbackUrl with ?trackId&success&status&orderId
  4. verify   -> POST /v1/verify with merchant, trackId  => final confirmation

Only a payment confirmed by step 4 is marked paid. The amount is always taken
from the server-side tier table, never from the browser, so a tampered client
cannot change the price.
"""

import json
import os
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import httpx
from loguru import logger

from config import settings

logger.add('logs/payments.txt', rotation="1 week")

PAYMENTS_FILE = os.getenv("PAYMENTS_FILE", "data/payments.json")
COFFEE_TIERS_FILE = os.getenv("COFFEE_TIERS_FILE", "data/coffee_tiers.json")

# Zibal works in Rial; the site shows Toman.
TOMAN_TO_RIAL = 10

# Coffee tiers shipped with the app. The admin can change the names, the
# prices and which tiers are offered; the edited list is stored as JSON and
# takes over from these defaults.
DEFAULT_COFFEE_TIERS = [
    {"id": "espresso", "name_en": "Espresso", "name_fa": "اسپرسو",
     "toman": 50000, "enabled": True},
    {"id": "americano", "name_en": "Americano", "name_fa": "آمریکانو",
     "toman": 75000, "enabled": True},
    {"id": "coldbrew", "name_en": "Cold Brew", "name_fa": "کلد برو",
     "toman": 100000, "enabled": True},
]

# Zibal refuses amounts under 1,000 Rial, which is 100 Toman.
MIN_TIER_TOMAN = 100
MAX_TIER_TOMAN = 50_000_000

TIER_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,29}$")
TIER_FIELDS = ("id", "name_en", "name_fa", "toman", "enabled")

# Zibal result codes (responses of request / verify / inquiry).
ZIBAL_RESULTS = {
    100: "success",
    102: "merchant not found",
    103: "merchant is inactive",
    104: "invalid merchant",
    105: "amount must be greater than 1,000 Rial",
    106: "invalid callbackUrl (must start with http or https)",
    107: "invalid percentMode",
    108: "invalid beneficiary in multiplexingInfos",
    109: "inactive beneficiary in multiplexingInfos",
    110: "missing id=self in multiplexingInfos",
    111: "amount does not match the multiplexing shares",
    112: "insufficient fee wallet balance",
    113: "amount exceeds the transaction limit",
    114: "invalid national code",
    115: "your server IP is not registered in the Zibal panel",
    201: "already verified",
    202: "order not paid or unsuccessful",
    203: "invalid trackId",
}

# Zibal transaction status codes.
ZIBAL_STATUSES = {
    -1: "waiting for payment",
    -2: "internal error",
    1: "paid - verified",
    2: "paid - not verified",
    3: "cancelled by user",
    4: "invalid card number",
    5: "insufficient balance",
    6: "incorrect password",
    7: "request count exceeded",
    8: "daily payment count exceeded",
    9: "daily payment amount exceeded",
    10: "invalid card issuer",
    11: "switch error",
    12: "card is not accessible",
    15: "refunded",
    16: "refunding",
    18: "reversed",
    21: "invalid merchant",
}


class CoffeeTierStore:
    """The "buy me a coffee" tiers, editable from the admin panel.

    The price is only ever read from here - the browser sends a tier id and
    nothing else - so changing a price in the admin panel changes what the
    gateway actually charges.
    """

    def __init__(self, path: str = COFFEE_TIERS_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._tiers: List[Dict] = json.loads(json.dumps(DEFAULT_COFFEE_TIERS))
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path) as f:
                stored = json.load(f)
        except FileNotFoundError:
            return
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Invalid coffee tiers file {self.path}: {e}")
            return

        try:
            self._tiers = self._validate(stored)
        except ValueError as e:
            # Never let a bad file take the donate button down: fall back to
            # the defaults and say why in the log.
            logger.error(f"Ignoring invalid coffee tiers in {self.path}: {e}")

    def _validate(self, tiers) -> List[Dict]:
        if not isinstance(tiers, list) or not tiers:
            raise ValueError("At least one coffee tier is required")
        if len(tiers) > 10:
            raise ValueError("At most 10 coffee tiers are supported")

        cleaned, seen = [], set()
        for raw in tiers:
            if not isinstance(raw, dict):
                raise ValueError("Each tier must be an object")

            tier_id = str(raw.get("id", "")).strip().lower()
            if not TIER_ID_PATTERN.match(tier_id):
                raise ValueError(
                    f"Invalid tier id '{tier_id}': use lowercase letters, "
                    "digits, '-' or '_' (max 30 characters)")
            if tier_id in seen:
                raise ValueError(f"Duplicate tier id '{tier_id}'")
            seen.add(tier_id)

            name_en = str(raw.get("name_en", "")).strip()
            name_fa = str(raw.get("name_fa", "")).strip()
            if not name_en or not name_fa:
                raise ValueError(f"Tier '{tier_id}' needs both an English and a Farsi name")

            try:
                toman = int(raw.get("toman"))
            except (TypeError, ValueError):
                raise ValueError(f"Tier '{tier_id}' needs a numeric price in Toman")
            if not MIN_TIER_TOMAN <= toman <= MAX_TIER_TOMAN:
                raise ValueError(
                    f"Tier '{tier_id}' price must be between {MIN_TIER_TOMAN:,} "
                    f"and {MAX_TIER_TOMAN:,} Toman")

            cleaned.append({
                "id": tier_id,
                "name_en": name_en[:60],
                "name_fa": name_fa[:60],
                "toman": toman,
                "enabled": bool(raw.get("enabled", True)),
            })

        if not any(t["enabled"] for t in cleaned):
            raise ValueError("At least one tier must stay enabled")
        return cleaned

    def all(self) -> List[Dict]:
        """Every tier, including disabled ones (admin view)."""
        return [dict(t) for t in self._tiers]

    def enabled(self) -> List[Dict]:
        """Tiers offered to visitors."""
        return [dict(t) for t in self._tiers if t.get("enabled", True)]

    def get(self, tier_id: str) -> Optional[Dict]:
        """An offered tier by id. Disabled tiers are not purchasable."""
        for tier in self._tiers:
            if tier["id"] == tier_id and tier.get("enabled", True):
                return dict(tier)
        return None

    def replace(self, tiers) -> List[Dict]:
        """Validate and store a complete new tier list. Raises ValueError."""
        cleaned = self._validate(tiers)
        with self._lock:
            self._tiers = cleaned
            try:
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
                with open(self.path, 'w') as f:
                    json.dump(self._tiers, f, indent=2, ensure_ascii=False)
                summary = ", ".join("{id}={toman}".format(**t) for t in cleaned)
                logger.info(f"Coffee tiers updated: {summary}")
            except OSError as e:
                logger.error(f"Could not persist coffee tiers: {e}")
            return self.all()


tier_store = CoffeeTierStore()


class PaymentStore:
    """JSON-backed list of payment attempts (newest last)."""

    def __init__(self, path: str = PAYMENTS_FILE):
        self.path = path
        self._lock = threading.Lock()
        self._items: List[Dict] = []
        self._load()

    def _load(self) -> None:
        try:
            with open(self.path) as f:
                data = json.load(f)
            if isinstance(data, list):
                self._items = data
        except FileNotFoundError:
            self._items = []
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Invalid payments file {self.path}: {e}")
            self._items = []

    def _persist(self) -> None:
        try:
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            with open(self.path, 'w') as f:
                json.dump(self._items, f, indent=2, ensure_ascii=False)
        except OSError as e:
            logger.error(f"Could not persist payments: {e}")

    def add(self, record: Dict) -> Dict:
        with self._lock:
            self._items.append(record)
            self._persist()
            return dict(record)

    def update(self, order_id: str, **fields) -> Optional[Dict]:
        with self._lock:
            for item in reversed(self._items):
                if item.get("order_id") == order_id:
                    item.update(fields)
                    self._persist()
                    return dict(item)
        return None

    def get_by_track(self, track_id) -> Optional[Dict]:
        # Newest match wins: Zibal trackIds are unique, but if one were ever
        # reused we must settle the most recent attempt, not an old one.
        for item in reversed(self._items):
            if str(item.get("track_id")) == str(track_id):
                return dict(item)
        return None

    def all(self) -> List[Dict]:
        return [dict(i) for i in self._items]

    def paid(self) -> List[Dict]:
        return [dict(i) for i in self._items if i.get("status") == "paid"]

    def stats(self) -> Dict:
        paid = self.paid()
        return {
            "total_attempts": len(self._items),
            "paid_count": len(paid),
            "total_toman": sum(p.get("amount_toman", 0) for p in paid),
        }


payment_store = PaymentStore()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_payment(first_name: str, last_name: str, tier_id: str,
                         callback_url: str, mobile: Optional[str] = None) -> Dict:
    """Register an order with Zibal and return the redirect URL.

    Raises ValueError for a bad tier and RuntimeError when Zibal refuses the
    request (the caller turns these into a clean API error).
    """
    tier = tier_store.get(tier_id)
    if tier is None:
        raise ValueError(f"Unknown or unavailable tier: {tier_id}")

    order_id = uuid.uuid4().hex[:16]
    amount_toman = tier["toman"]
    amount_rial = amount_toman * TOMAN_TO_RIAL
    description = f'HavaChetor - {tier["name_en"]} ({first_name} {last_name})'.strip()

    payload = {
        "merchant": settings.zibal_merchant,
        "amount": amount_rial,          # Zibal expects Rial
        "callbackUrl": callback_url,
        "description": description,
        "orderId": order_id,
    }
    if mobile:
        payload["mobile"] = mobile

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(settings.zibal_request_url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Zibal request failed: {e}")
        raise RuntimeError("Could not reach the payment gateway") from e

    result = data.get("result")
    if result != 100 or not data.get("trackId"):
        message = data.get("message") or ZIBAL_RESULTS.get(result, "unknown error")
        logger.error(f"Zibal refused the request (result={result}): {message}")
        raise RuntimeError(f"Payment gateway error: {message}")

    track_id = data["trackId"]
    # The tier name and amount are copied into the record, so a later price
    # change in the admin panel never rewrites what someone already paid.
    record = {
        "order_id": order_id,
        "track_id": track_id,
        "first_name": first_name.strip(),
        "last_name": last_name.strip(),
        "tier_id": tier_id,
        "tier_name": tier["name_en"],
        "amount_toman": amount_toman,
        "amount_rial": amount_rial,
        "status": "pending",
        "created_at": _now(),
        "paid_at": None,
        "ref_number": None,
        "card_number": None,
        "zibal_status": None,
        "message": None,
    }
    payment_store.add(record)
    logger.info(f"Payment requested: order={order_id} track={track_id} "
                f"amount={amount_toman} Toman")

    return {
        "order_id": order_id,
        "track_id": track_id,
        "payment_url": f"{settings.zibal_start_url}{track_id}",
        "amount_toman": amount_toman,
    }


async def verify_payment(track_id) -> Dict:
    """Confirm a payment with Zibal and update the stored record.

    Returns the updated record. A payment is only marked "paid" when Zibal
    confirms it AND the amount matches what we requested.
    """
    record = payment_store.get_by_track(track_id)
    if record is None:
        raise ValueError("Unknown trackId")

    # Already settled: don't verify twice (Zibal answers 201 for that).
    if record.get("status") == "paid":
        return record

    payload = {"merchant": settings.zibal_merchant, "trackId": int(track_id)}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(settings.zibal_verify_url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Zibal verify failed for track {track_id}: {e}")
        raise RuntimeError("Could not reach the payment gateway") from e

    result = data.get("result")
    status = data.get("status")
    message = data.get("message") or ZIBAL_RESULTS.get(result, "")

    # result 100 = verified now, 201 = was already verified: both mean paid.
    verified = result in (100, 201)
    amount_ok = data.get("amount") in (None, record["amount_rial"])

    if verified and not amount_ok:
        logger.error(f"Amount mismatch for track {track_id}: "
                     f"expected {record['amount_rial']} got {data.get('amount')}")

    updated = payment_store.update(
        record["order_id"],
        status="paid" if (verified and amount_ok) else "failed",
        paid_at=data.get("paidAt") or (_now() if verified else None),
        ref_number=data.get("refNumber"),
        card_number=data.get("cardNumber"),
        zibal_status=status,
        zibal_status_text=ZIBAL_STATUSES.get(status, ""),
        zibal_result=result,
        message=message,
    )
    logger.info(f"Payment verify: order={record['order_id']} track={track_id} "
                f"result={result} status={status} -> {updated.get('status')}")
    return updated


async def inquiry_payment(track_id) -> Dict:
    """Ask Zibal for the full state of a transaction (report / re-check).

    Used by the admin panel to resolve payments left "pending" because the
    verify call could not run (e.g. a network blip on the callback).
    """
    payload = {"merchant": settings.zibal_merchant, "trackId": int(track_id)}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(settings.zibal_inquiry_url, json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPError as e:
        logger.error(f"Zibal inquiry failed for track {track_id}: {e}")
        raise RuntimeError("Could not reach the payment gateway") from e

    data["status_text"] = ZIBAL_STATUSES.get(data.get("status"), "")
    data["result_text"] = ZIBAL_RESULTS.get(data.get("result"), "")
    return data


def mark_failed(track_id, reason: str) -> Optional[Dict]:
    """Record an unsuccessful/cancelled attempt reported by the callback."""
    record = payment_store.get_by_track(track_id)
    if record is None or record.get("status") == "paid":
        return record
    return payment_store.update(record["order_id"], status="failed", message=reason)
