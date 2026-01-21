from __future__ import annotations

import hmac
from typing import Optional

from fastapi import HTTPException, Request

from .config import Settings, TokenParts
from .models import UserData, UserWallet


def parse_token(token: str, expected_prefix: str) -> Optional[TokenParts]:
    raw = token.strip()
    if raw == "":
        return None
    parts = raw.split("_")
    if len(parts) < 3:
        return None
    prefix = parts[0].strip()
    key_id = parts[1].strip()
    secret = "_".join(parts[2:]).strip()
    if prefix == "" or key_id == "" or secret == "":
        return None
    if prefix != expected_prefix:
        return None
    try:
        return TokenParts(prefix=prefix, key_id=key_id, secret=secret)
    except ValueError:
        return None


def require_dashboard_api_key(request: Request, expected_key: str) -> None:
    auth = request.headers.get("authorization")
    if auth is None:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or token.strip() == "":
        raise HTTPException(status_code=401, detail="Invalid Authorization header")
    if not hmac.compare_digest(token.strip(), expected_key):
        raise HTTPException(status_code=401, detail="Invalid dashboard API key")


def build_user(
    *,
    key_id: str,
    balance: int,
    used: Optional[int],
) -> UserData:
    user_id = f"user_{key_id}"
    wallet = UserWallet(total_balance=max(balance, 0), total_used=used)
    return UserData(
        user_id=user_id,
        full_name=user_id,
        wallet=wallet,
        metadata=None,
        customRateLimits=None,
    )


__all__ = ["build_user", "parse_token", "require_dashboard_api_key"]
