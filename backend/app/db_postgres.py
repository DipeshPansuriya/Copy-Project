"""PostgreSQL metadata store (one row per clipboard entry).

Implements the same interface as db.py (SQLite) so the app can switch
backends via CLIP_DB_BACKEND=postgres without changing the API layer.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import asyncpg

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    code            TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,              -- 'text' | 'image' | 'file'
    filename        TEXT,
    content_type    TEXT,
    size            BIGINT NOT NULL,
    object_key      TEXT NOT NULL,
    created_at      DOUBLE PRECISION NOT NULL,
    expires_at      DOUBLE PRECISION NOT NULL,
    one_shot        BOOLEAN NOT NULL DEFAULT FALSE,
    retrieved_at    DOUBLE PRECISION,
    downloads       BIGINT NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,
    locked_until    DOUBLE PRECISION,           -- lockout timestamp (epoch), NULL if not locked
    password_hash   TEXT                         -- optional bcrypt hash for password-protected clips
);
CREATE INDEX IF NOT EXISTS idx_items_expires ON items (expires_at);
CREATE INDEX IF NOT EXISTS idx_items_locked ON items (locked_until) WHERE locked_until IS NOT NULL;
"""


def _row_to_dict(row: asyncpg.Record) -> dict[str, Any]:
    return dict(row)


class Database:
    """PostgreSQL connection pool wrapper with the same interface as db.py."""

    def __init__(self) -> None:
        self._pool: Optional[asyncpg.Pool] = None

    async def connect(self) -> None:
        self._pool = await asyncpg.create_pool(
            settings.pg_dsn,
            min_size=2,
            max_size=10,
            command_timeout=60,
        )
        async with self._pool.acquire() as conn:
            await conn.execute(SCHEMA)

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            await conn.execute(sql, *params)

    async def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        assert self._pool is not None
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
            return [_row_to_dict(r) for r in rows]

    # -- item operations -------------------------------------------------

    async def create_item(
        self,
        *,
        code: str,
        kind: str,
        filename: Optional[str],
        content_type: str,
        size: int,
        object_key: str,
        ttl: int,
        one_shot: bool,
        password_hash: Optional[str] = None,
    ) -> None:
        now = time.time()
        await self.execute(
            """
            INSERT INTO items
                (code, kind, filename, content_type, size, object_key,
                 created_at, expires_at, one_shot, downloads, password_hash)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, 0, $10)
            """,
            code,
            kind,
            filename,
            content_type,
            size,
            object_key,
            now,
            now + ttl,
            one_shot,
            password_hash,
        )

    async def get_item(self, code: str) -> Optional[dict[str, Any]]:
        rows = await self.query("SELECT * FROM items WHERE code = $1", (code,))
        return rows[0] if rows else None

    async def increment_download(self, code: str) -> None:
        await self.execute(
            "UPDATE items SET downloads = downloads + 1 WHERE code = $1", (code,)
        )

    async def mark_retrieved(self, code: str) -> None:
        await self.execute(
            "UPDATE items SET retrieved_at = $1 WHERE code = $2", (time.time(), code)
        )

    async def delete_item(self, code: str) -> None:
        await self.execute("DELETE FROM items WHERE code = $1", (code,))

    async def expired_items(self, now: Optional[float] = None) -> list[dict[str, Any]]:
        """Items past their TTL, or one-shot items that were already retrieved."""
        now = now or time.time()
        return await self.query(
            """
            SELECT * FROM items
            WHERE expires_at < $1 OR (one_shot = TRUE AND retrieved_at IS NOT NULL)
            """,
            (now,),
        )

    async def stats(self) -> dict[str, int]:
        rows = await self.query(
            """
            SELECT COUNT(*) AS active, COALESCE(SUM(size), 0) AS bytes
            FROM items WHERE expires_at >= $1
            """,
            (time.time(),),
        )
        row = rows[0] if rows else {"active": 0, "bytes": 0}
        return {"active": int(row["active"]), "bytes": int(row["bytes"])}

    # -- lockout / failed attempts ---------------------------------------

    async def increment_failed_attempt(self, code: str) -> int:
        """Increment failed attempt counter and return new count."""
        now = time.time()
        await self.execute(
            """
            UPDATE items
            SET failed_attempts = failed_attempts + 1,
                locked_until = CASE
                    WHEN failed_attempts + 1 >= $1 THEN $2
                    ELSE locked_until
                END
            WHERE code = $3
            """,
            settings.max_failed_attempts,
            now + settings.lockout_seconds,
            code,
        )
        row = await self.get_item(code)
        return int(row["failed_attempts"]) + 1 if row else 0

    async def reset_failed_attempts(self, code: str) -> None:
        """Reset failed attempts and clear lockout on successful retrieval."""
        await self.execute(
            "UPDATE items SET failed_attempts = 0, locked_until = NULL WHERE code = $1",
            (code,),
        )

    async def is_locked(self, code: str) -> tuple[bool, Optional[float]]:
        """Check if item is locked. Returns (is_locked, unlock_time)."""
        rows = await self.query(
            "SELECT locked_until FROM items WHERE code = $1", (code,)
        )
        if not rows:
            return False, None
        locked_until = rows[0]["locked_until"]
        if locked_until is None:
            return False, None
        now = time.time()
        if float(locked_until) > now:
            return True, float(locked_until)
        # Lock expired, clear it
        await self.execute(
            "UPDATE items SET locked_until = NULL WHERE code = $1", (code,)
        )
        return False, None

    # -- admin methods ------------------------------------------------------

    async def list_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent clipboard entries (metadata only)."""
        return await self.query(
            """
            SELECT code, kind, filename, content_type, size, created_at, expires_at,
                   one_shot, retrieved_at, downloads, failed_attempts, locked_until
            FROM items
            ORDER BY created_at DESC
            LIMIT $1
            """,
            (limit,),
        )

    async def delete_entry(self, code: str) -> bool:
        """Delete a clipboard entry (admin override). Returns True if deleted."""
        row = await self.get_item(code)
        if row is None:
            return False
        await self.execute("DELETE FROM items WHERE code = $1", (code,))
        return True

    async def get_locked_items(self) -> list[dict[str, Any]]:
        """List all currently locked items."""
        now = time.time()
        return await self.query(
            """
            SELECT code, kind, size, failed_attempts, locked_until
            FROM items
            WHERE locked_until IS NOT NULL AND locked_until > $1
            """,
            (now,),
        )
