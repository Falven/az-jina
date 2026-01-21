from __future__ import annotations

import re
from typing import Annotated

from pydantic import AliasChoices, BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

PREFIX_RE = re.compile(r"^[a-zA-Z0-9-]{3,32}$")
KEY_ID_RE = re.compile(r"^[a-zA-Z0-9-]{6,64}$")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    auth_dashboard_api_key: str = Field(
        ..., validation_alias=AliasChoices("AUTH_DASHBOARD_API_KEY", "DASHBOARD_API_KEY")
    )
    key_vault_url: str = Field(
        ...,
        validation_alias=AliasChoices("KEY_VAULT_URI", "SELF_HOST_TOKENS_VAULT_URL"),
    )
    api_key_prefix: str = Field(
        default="azjina",
        validation_alias=AliasChoices("API_KEY_PREFIX"),
    )
    api_key_cache_ttl_seconds: int = Field(
        default=300,
        validation_alias=AliasChoices("API_KEY_CACHE_TTL_SECONDS"),
    )
    default_wallet_balance: int = Field(
        default=1_000_000,
        validation_alias=AliasChoices("DEFAULT_WALLET_BALANCE"),
    )
    rate_limit_per_minute: int = Field(
        default=0,
        validation_alias=AliasChoices("RATE_LIMIT_PER_MINUTE"),
    )
    managed_identity_client_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("AZURE_CLIENT_ID"),
    )
    host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("HOST"))
    port: int = Field(default=8080, validation_alias=AliasChoices("PORT"))
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))

    @field_validator("auth_dashboard_api_key")
    @classmethod
    def _validate_dashboard_key(cls, value: str) -> str:
        candidate = value.strip()
        if candidate == "":
            raise ValueError("AUTH_DASHBOARD_API_KEY is required.")
        return candidate

    @field_validator("key_vault_url")
    @classmethod
    def _validate_vault_url(cls, value: str) -> str:
        candidate = value.strip()
        if candidate == "":
            raise ValueError("KEY_VAULT_URI is required.")
        return candidate

    @field_validator("api_key_prefix")
    @classmethod
    def _validate_prefix(cls, value: str) -> str:
        candidate = value.strip()
        if candidate == "" or PREFIX_RE.match(candidate) is None:
            raise ValueError("API_KEY_PREFIX must be 3-32 chars (letters, digits, hyphen).")
        return candidate

    @field_validator("api_key_cache_ttl_seconds")
    @classmethod
    def _validate_cache_ttl(cls, value: int) -> int:
        if value < 0:
            raise ValueError("API_KEY_CACHE_TTL_SECONDS must be >= 0.")
        return value

    @field_validator("default_wallet_balance")
    @classmethod
    def _validate_wallet_balance(cls, value: int) -> int:
        if value < 0:
            raise ValueError("DEFAULT_WALLET_BALANCE must be >= 0.")
        return value

    @field_validator("rate_limit_per_minute")
    @classmethod
    def _validate_rate_limit(cls, value: int) -> int:
        if value < 0:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be >= 0.")
        return value


class TokenParts(BaseModel):
    prefix: Annotated[str, Field(min_length=1)]
    key_id: Annotated[str, Field(min_length=1)]
    secret: Annotated[str, Field(min_length=1)]

    @field_validator("prefix")
    @classmethod
    def _validate_prefix_value(cls, value: str) -> str:
        candidate = value.strip()
        if candidate == "" or PREFIX_RE.match(candidate) is None:
            raise ValueError("Invalid token prefix.")
        return candidate

    @field_validator("key_id")
    @classmethod
    def _validate_key_id(cls, value: str) -> str:
        candidate = value.strip()
        if candidate == "" or KEY_ID_RE.match(candidate) is None:
            raise ValueError("Invalid token key id.")
        return candidate

    @field_validator("secret")
    @classmethod
    def _validate_secret(cls, value: str) -> str:
        candidate = value.strip()
        if candidate == "":
            raise ValueError("Invalid token secret.")
        return candidate


__all__ = ["KEY_ID_RE", "PREFIX_RE", "Settings", "TokenParts"]
