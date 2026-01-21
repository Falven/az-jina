from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional


@dataclass(frozen=True)
class CacheEntry:
    value: Optional[str]
    expires_at: float


class SecretCache:
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._entries: Dict[str, CacheEntry] = {}

    def get(self, key: str) -> tuple[bool, Optional[str]]:
        if self._ttl_seconds == 0:
            return False, None
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False, None
            if entry.expires_at <= now:
                self._entries.pop(key, None)
                return False, None
            return True, entry.value

    def set(self, key: str, value: Optional[str]) -> None:
        if self._ttl_seconds == 0:
            return
        expires_at = time.monotonic() + self._ttl_seconds
        with self._lock:
            self._entries[key] = CacheEntry(value=value, expires_at=expires_at)


@dataclass
class UsageState:
    balance: int
    used: int


class UsageTracker:
    def __init__(self, default_balance: int) -> None:
        self._default_balance = default_balance
        self._lock = threading.Lock()
        self._state: Dict[str, UsageState] = {}

    def get_state(self, key_id: str) -> UsageState:
        with self._lock:
            state = self._state.get(key_id)
            if state is None:
                state = UsageState(balance=self._default_balance, used=0)
                self._state[key_id] = state
            return UsageState(balance=state.balance, used=state.used)

    def consume(self, key_id: str, tokens: int) -> tuple[UsageState, bool]:
        with self._lock:
            state = self._state.get(key_id)
            if state is None:
                state = UsageState(balance=self._default_balance, used=0)
                self._state[key_id] = state
            out_of_quota = state.balance <= 0 or tokens > state.balance
            if tokens > 0:
                state.balance = max(state.balance - tokens, 0)
                state.used += tokens
            return UsageState(balance=state.balance, used=state.used), out_of_quota


class RateLimiter:
    def __init__(self, limit_per_minute: int) -> None:
        self._limit = limit_per_minute
        self._lock = threading.Lock()
        self._hits: Dict[str, Deque[float]] = {}

    def allow(self, key_id: str) -> bool:
        if self._limit <= 0:
            return True
        now = time.monotonic()
        cutoff = now - 60.0
        with self._lock:
            bucket = self._hits.get(key_id)
            if bucket is None:
                bucket = deque()
                self._hits[key_id] = bucket
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self._limit:
                return False
            bucket.append(now)
            return True


__all__ = ["RateLimiter", "SecretCache", "UsageState", "UsageTracker"]
