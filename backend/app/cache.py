"""Cache layer for OpenClipboard.

Uses Redis when available (multi-instance deployments), falls back to
in-memory caching for single-instance SQLite deployments.

Cached items:
- Rate limit counters (shared across instances via Redis)
- Health/stats snapshots (short TTL)
- Hot clipboard entries (metadata only, short TTL)
"""
from __future__ import annotations

import json
import time
from typing import Any, Optional

try:
    import redis.asyncio as redis

    _REDIS_AVAILABLE = True
except ImportError:  # pragma: no cover
    redis = None  # type: ignore
    _REDIS_AVAILABLE = False

from .config import settings


class Cache:
    """Async cache with Redis backend, in-memory fallback."""

    def __init__(self) -> None:
        self._redis: Optional[object] = None
        self._memory: dict[str, tuple[float, Any]] = {}  # key -> (expiry, value)

    async def connect(self) -> None:
        """Connect to Redis if configured and available."""
        if not _REDIS_AVAILABLE:
            return
        redis_url = os_getenv("REDIS_URL", "redis://localhost:6379/0")
        try:
            self._redis = await redis.from_url(redis_url, encoding="utf-8", decode_responses=True)
            await self._redis.ping()
        except Exception:
            self._redis = None  # fall back to in-memory

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.close()
            except Exception:
                pass
            self._redis = None

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from cache."""
        # Try Redis first
        if self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw is not None:
                    return json.loads(raw)
            except Exception:
                pass
        # Fall back to in-memory
        entry = self._memory.get(key)
        if entry is None:
            return None
        expiry, value = entry
        if time.time() > expiry:
            del self._memory[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int = 60) -> None:
        """Set a value in cache with TTL in seconds."""
        payload = json.dumps(value, default=str)
        expiry = time.time() + ttl

        if self._redis is not None:
            try:
                await self._redis.setex(key, ttl, payload)
                return
            except Exception:
                pass
        self._memory[key] = (expiry, value)

    async def delete(self, key: str) -> None:
        """Delete a key from cache."""
        if self._redis is not None:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
        self._memory.pop(key, None)

    async def incr(self, key: str, ttl: int = 60) -> int:
        """Increment a counter and return new value."""
        if self._redis is not None:
            try:
                val = await self._redis.incr(key)
                if val == 1:
                    await self._redis.expire(key, ttl)
                return int(val)
            except Exception:
                pass
        # In-memory fallback
        entry = self._memory.get(key)
        now = time.time()
        if entry is None or now > entry[0]:
            self._memory[key] = (now + ttl, 1)
            return 1
        self._memory[key] = (entry[0], entry[1] + 1)
        return entry[1] + 1

    async def clear_expired_memory(self) -> None:
        """Clean up expired in-memory entries (call periodically)."""
        now = time.time()
        expired = [k for k, (e, _) in self._memory.items() if now > e]
        for k in expired:
            del self._memory[k]


def os_getenv(name: str, default: str = "") -> str:
    import os

    return os.getenv(name, default)


cache = Cache()
