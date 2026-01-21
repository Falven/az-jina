from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request
from azure.keyvault.secrets import SecretClient

from .auth import build_user, parse_token, require_dashboard_api_key
from .config import Settings, TokenParts
from .logging import configure_logging
from .models import AuthResponse, TokenRequest, UsageReport
from .state import RateLimiter, SecretCache, UsageTracker
from .vault import create_secret_client, validate_token

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AppState:
    settings: Settings
    secret_cache: SecretCache
    usage_tracker: UsageTracker
    rate_limiter: RateLimiter
    secret_client: SecretClient


def _require_token(token: str | None, settings: Settings) -> TokenParts:
    if token is None or token.strip() == "":
        raise HTTPException(status_code=401, detail="Missing API key")
    parts = parse_token(token, settings.api_key_prefix)
    if parts is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return parts


async def _validate_token(
    *,
    token: str | None,
    state: AppState,
) -> TokenParts:
    parts = _require_token(token, state.settings)
    try:
        match = await validate_token(
            token_parts=parts,
            client=state.secret_client,
            cache=state.secret_cache,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="Auth backend unavailable") from exc
    if not match.matched:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return parts


def _check_rate_limit(state: AppState, key_id: str) -> None:
    if not state.rate_limiter.allow(key_id):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings()
    configure_logging(settings.log_level)
    logger.info("Starting auth service", extra={"vault": settings.key_vault_url})
    secret_client = create_secret_client(settings)
    state = AppState(
        settings=settings,
        secret_cache=SecretCache(settings.api_key_cache_ttl_seconds),
        usage_tracker=UsageTracker(settings.default_wallet_balance),
        rate_limiter=RateLimiter(settings.rate_limit_per_minute),
        secret_client=secret_client,
    )
    app.state.auth = state
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/authorization", response_model=AuthResponse, response_model_exclude_none=True)
async def authorization(payload: TokenRequest, request: Request) -> AuthResponse:
    state: AppState = request.app.state.auth
    require_dashboard_api_key(request, state.settings.auth_dashboard_api_key)
    parts = await _validate_token(token=payload.token, state=state)
    key_id = parts.key_id
    _check_rate_limit(state, key_id)
    usage_state = state.usage_tracker.get_state(key_id)
    if usage_state.balance <= 0:
        raise HTTPException(status_code=402, detail="Out of quota")
    user = build_user(key_id=key_id, balance=usage_state.balance, used=usage_state.used)
    return AuthResponse(data=user)


@app.post("/validate", response_model=AuthResponse, response_model_exclude_none=True)
async def validate(payload: TokenRequest, request: Request) -> AuthResponse:
    state: AppState = request.app.state.auth
    require_dashboard_api_key(request, state.settings.auth_dashboard_api_key)
    parts = await _validate_token(token=payload.token, state=state)
    key_id = parts.key_id
    _check_rate_limit(state, key_id)
    usage_state = state.usage_tracker.get_state(key_id)
    if usage_state.balance <= 0:
        raise HTTPException(status_code=402, detail="Out of quota")
    user = build_user(key_id=key_id, balance=usage_state.balance, used=usage_state.used)
    return AuthResponse(data=user)


@app.post("/usage", response_model=AuthResponse, response_model_exclude_none=True)
async def usage(payload: UsageReport, request: Request) -> AuthResponse:
    state: AppState = request.app.state.auth
    require_dashboard_api_key(request, state.settings.auth_dashboard_api_key)
    parts = await _validate_token(token=payload.token, state=state)
    key_id = parts.key_id
    _check_rate_limit(state, key_id)
    tokens = payload.usage.total_tokens if payload.usage else 0
    usage_state, out_of_quota = state.usage_tracker.consume(key_id, tokens)
    if out_of_quota:
        raise HTTPException(status_code=402, detail="Out of quota")
    user = build_user(key_id=key_id, balance=usage_state.balance, used=usage_state.used)
    return AuthResponse(data=user)


__all__ = ["app"]
