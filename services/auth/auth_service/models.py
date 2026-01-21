from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TokenRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    token: Optional[str] = None


class UsageConsumer(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    user_id: Optional[str] = None


class UsageDetails(BaseModel):
    model_config = ConfigDict(extra="allow")

    total_tokens: int = Field(default=0, ge=0)


class UsageReport(BaseModel):
    model_config = ConfigDict(extra="allow")

    token: Optional[str] = None
    model_name: Optional[str] = None
    api_endpoint: Optional[str] = None
    consumer: Optional[UsageConsumer] = None
    usage: Optional[UsageDetails] = None
    labels: Optional[Dict[str, Any]] = None


class RateLimitRule(BaseModel):
    model_config = ConfigDict(extra="ignore")

    occurrence: int = Field(ge=0)
    periodSeconds: int = Field(ge=1)
    effectiveFrom: Optional[str] = None
    expiresAt: Optional[str] = None


class UserWallet(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_balance: int = Field(ge=0)
    total_used: Optional[int] = Field(default=None, ge=0)


class UserData(BaseModel):
    model_config = ConfigDict(extra="ignore")

    user_id: str
    full_name: str
    wallet: UserWallet
    metadata: Optional[Dict[str, Any]] = None
    customRateLimits: Optional[Dict[str, List[RateLimitRule]]] = None


class AuthResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    data: UserData


__all__ = [
    "AuthResponse",
    "TokenRequest",
    "UsageReport",
    "UsageConsumer",
    "UsageDetails",
    "UserData",
    "UserWallet",
    "RateLimitRule",
]
