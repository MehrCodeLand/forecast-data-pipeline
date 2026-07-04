"""Admin authentication for the admin panel.

Credentials live in admin_config.json (no database in this version).
The password is stored as a sha256 hex digest. Sessions are opaque
random tokens kept in memory and delivered as an HttpOnly cookie.
"""

import hashlib
import hmac
import json
import os
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import HTTPException, Request
from loguru import logger

ADMIN_CONFIG_FILE = os.getenv("ADMIN_CONFIG_FILE", "admin_config.json")
SESSION_COOKIE = "admin_session"

_DEFAULTS = {
    "admin_path": "/wx-admin",
    "username": "admin",
    # sha256 of "admin123" - change it for any real deployment
    "password_sha256": "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9",
    "session_hours": 8,
}


def load_admin_config() -> Dict:
    config = dict(_DEFAULTS)
    try:
        with open(ADMIN_CONFIG_FILE) as f:
            config.update(json.load(f))
    except FileNotFoundError:
        logger.warning(f"{ADMIN_CONFIG_FILE} not found, using built-in admin defaults")
    except (json.JSONDecodeError, OSError) as e:
        logger.error(f"Invalid admin config {ADMIN_CONFIG_FILE}: {e}, using defaults")

    if not str(config["admin_path"]).startswith("/"):
        config["admin_path"] = "/" + str(config["admin_path"])
    config["admin_path"] = str(config["admin_path"]).rstrip("/")
    return config


admin_config = load_admin_config()

_sessions: Dict[str, datetime] = {}


def verify_credentials(username: str, password: str) -> bool:
    expected_user = str(admin_config["username"])
    expected_hash = str(admin_config["password_sha256"]).lower()
    given_hash = hashlib.sha256(password.encode()).hexdigest()

    user_ok = hmac.compare_digest(username.encode(), expected_user.encode())
    pass_ok = hmac.compare_digest(given_hash.encode(), expected_hash.encode())
    return user_ok and pass_ok


def create_session() -> str:
    _prune_expired()
    token = secrets.token_urlsafe(32)
    lifetime = timedelta(hours=float(admin_config.get("session_hours", 8)))
    _sessions[token] = datetime.now() + lifetime
    return token


def destroy_session(token: Optional[str]) -> None:
    if token:
        _sessions.pop(token, None)


def is_valid_session(token: Optional[str]) -> bool:
    if not token:
        return False
    expiry = _sessions.get(token)
    if expiry is None:
        return False
    if expiry < datetime.now():
        _sessions.pop(token, None)
        return False
    return True


def _prune_expired() -> None:
    now = datetime.now()
    for token in [t for t, exp in _sessions.items() if exp < now]:
        _sessions.pop(token, None)


def require_admin(request: Request) -> None:
    """FastAPI dependency: reject the request unless it carries a valid session."""
    if not is_valid_session(request.cookies.get(SESSION_COOKIE)):
        raise HTTPException(status_code=401, detail="Not authenticated")
