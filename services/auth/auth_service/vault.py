from __future__ import annotations

import asyncio
import hmac
import logging
from dataclasses import dataclass
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

from .config import Settings, TokenParts
from .state import SecretCache

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SecretMatch:
    secret_value: Optional[str]
    matched: bool


def create_secret_client(settings: Settings) -> SecretClient:
    credential_kwargs: dict[str, str] = {}
    if settings.managed_identity_client_id:
        credential_kwargs["managed_identity_client_id"] = settings.managed_identity_client_id
    credential = DefaultAzureCredential(**credential_kwargs)
    return SecretClient(vault_url=settings.key_vault_url, credential=credential)


def secret_name(prefix: str, key_id: str) -> str:
    return f"{prefix}-api-key-{key_id}"


def _match_secret(stored: Optional[str], provided: str) -> SecretMatch:
    if stored is None:
        return SecretMatch(secret_value=None, matched=False)
    return SecretMatch(secret_value=stored, matched=hmac.compare_digest(stored, provided))


async def validate_token(
    *,
    token_parts: TokenParts,
    client: SecretClient,
    cache: SecretCache,
) -> SecretMatch:
    name = secret_name(token_parts.prefix, token_parts.key_id)
    hit, cached = cache.get(name)
    if hit:
        return _match_secret(cached, token_parts.secret)

    try:
        secret = await asyncio.to_thread(client.get_secret, name)
    except ResourceNotFoundError:
        cache.set(name, None)
        return SecretMatch(secret_value=None, matched=False)
    except Exception as exc:
        logger.exception("Key Vault lookup failed", extra={"secret_name": name})
        raise RuntimeError("Key Vault lookup failed") from exc

    value = secret.value or ""
    cache.set(name, value or None)
    return _match_secret(value or None, token_parts.secret)


__all__ = ["SecretMatch", "create_secret_client", "secret_name", "validate_token"]
