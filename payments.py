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

# Zibal works in Rial; the site shows Toman.
TOMAN_TO_RIAL = 10

# Coffee tiers. The price lives here on the server - the browser only sends a
# tier id.
COFFEE_TIERS = {
    "espresso": {"name_en": "Espresso", "name_fa": "اسپرسو", "toman": 50000},
    "americano": {"name_en": "Americano", "name_fa": "آمریکانو", "toman": 75000},
    "coldbrew": {"name_en": "Cold Brew", "name_fa": "کلد برو", "toman": 100000},
}

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
    tier = COFFEE_TIERS.get(tier_id)
    if tier is None:
        raise ValueError(f"Unknown tier: {tier_id}")

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
