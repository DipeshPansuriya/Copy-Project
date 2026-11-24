"""SQLite metadata store (one row per clipboard entry).

The blob itself lives in object storage (MinIO or local disk); SQLite only
keeps the small metadata needed for retrieval, accounting and purging.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any, Optional

import aiosqlite

from .config import settings

# Lockout settings for brute-force protection (from config)
MAX_FAILED_ATTEMPTS = settings.max_failed_attempts
LOCKOUT_SECONDS = settings.lockout_seconds

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    code         TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,              -- 'text' | 'image' | 'file'
    filename     TEXT,
    content_type TEXT,
    size         INTEGER NOT NULL,
    object_key   TEXT NOT NULL,
    created_at   REAL NOT NULL,
    expires_at   REAL NOT NULL,
    one_shot     INTEGER NOT NULL DEFAULT 0,
    retrieved_at REAL,
    downloads    INTEGER NOT NULL DEFAULT 0,
    failed_attempts INTEGER NOT NULL DEFAULT 0,   -- consecutive wrong code attempts
    locked_until  REAL,                             -- lockout timestamp (epoch), NULL if not locked
    password_hash TEXT                               -- optional bcrypt hash for password-protected clips
);
CREATE INDEX IF NOT EXISTS idx_items_expires ON items (expires_at);
CREATE INDEX IF NOT EXISTS idx_items_locked ON items (locked_until);
"""


def _row_to_dict(row: aiosqlite.Row) -> dict[str, Any]:
    return {key: row[idx] for idx, key in enumerate(row.keys())}


class Database:
    """Small async wrapper around a single SQLite connection."""

    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        async with self._lock:
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.executescript(SCHEMA)
            await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        assert self._conn is not None
        async with self._lock:
            await self._conn.execute(sql, params)
            await self._conn.commit()

    async def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        assert self._conn is not None
        async with self._lock:
            cur = await self._conn.execute(sql, params)
            rows = await cur.fetchall()
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            """,
            (
                code,
                kind,
                filename,
                content_type,
                size,
                object_key,
                now,
                now + ttl,
                1 if one_shot else 0,
                password_hash,
            ),
        )

    async def increment_failed_attempt(self, code: str) -> int:
        """Increment failed attempt counter and return new count."""
        now = time.time()
        await self.execute(
            """
            UPDATE items
            SET failed_attempts = failed_attempts + 1,
                locked_until = CASE
                    WHEN failed_attempts + 1 >= ? THEN ?
                    ELSE locked_until
                END
            WHERE code = ?
            """,
            (MAX_FAILED_ATTEMPTS, now + LOCKOUT_SECONDS, code),
        )
        row = await self.get_item(code)
        return int(row["failed_attempts"]) + 1 if row else 0

    async def reset_failed_attempts(self, code: str) -> None:
        """Reset failed attempts and clear lockout on successful retrieval."""
        await self.execute(
            "UPDATE items SET failed_attempts = 0, locked_until = NULL WHERE code = ?",
            (code,),
        )

    async def is_locked(self, code: str) -> tuple[bool, Optional[float]]:
        """Check if item is locked. Returns (is_locked, unlock_time)."""
        rows = await self.query(
            "SELECT locked_until FROM items WHERE code = ?", (code,)
        )
        if not rows:
            return False, None
        locked_until = rows[0]["locked_until"]
        if locked_until is None:
            return False, None
        now = time.time()
        if locked_until > now:
            return True, locked_until
        # Lock expired, clear it
        await self.execute(
            "UPDATE items SET locked_until = NULL WHERE code = ?", (code,)
        )
        return False, None

    async def get_item(self, code: str) -> Optional[dict[str, Any]]:
        rows = await self.query("SELECT * FROM items WHERE code = ?", (code,))
        return rows[0] if rows else None

    async def increment_download(self, code: str) -> None:
        await self.execute(
            "UPDATE items SET downloads = downloads + 1 WHERE code = ?", (code,)
        )

    async def mark_retrieved(self, code: str) -> None:
        await self.execute(
            "UPDATE items SET retrieved_at = ? WHERE code = ?", (time.time(), code)
        )

    async def delete_item(self, code: str) -> None:
        await self.execute("DELETE FROM items WHERE code = ?", (code,))

    async def expired_items(self, now: Optional[float] = None) -> list[dict[str, Any]]:
        """Items past their TTL, or one-shot items that were already retrieved."""
        now = now or time.time()
        return await self.query(
            """
            SELECT * FROM items
            WHERE expires_at < ? OR (one_shot = 1 AND retrieved_at IS NOT NULL)
            """,
            (now,),
        )

    async def stats(self) -> dict[str, int]:
        rows = await self.query(
            """
            SELECT COUNT(*) AS active, COALESCE(SUM(size), 0) AS bytes
            FROM items WHERE expires_at >= ?
            """,
            (time.time(),),
        )
        row = rows[0] if rows else {"active": 0, "bytes": 0}
        return {"active": int(row["active"]), "bytes": int(row["bytes"])}

    # -- admin methods ------------------------------------------------------

    async def list_entries(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent clipboard entries (metadata only)."""
        return await self.query(
            """
            SELECT code, kind, filename, content_type, size, created_at, expires_at,
                   one_shot, retrieved_at, downloads, failed_attempts, locked_until
            FROM items
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        )

    async def delete_entry(self, code: str) -> bool:
        """Delete a clipboard entry (admin override). Returns True if deleted."""
        row = await self.get_item(code)
        if row is None:
            return False
        await self.execute("DELETE FROM items WHERE code = ?", (code,))
        return True

    async def get_locked_items(self) -> list[dict[str, Any]]:
        """List all currently locked items."""
        now = time.time()
        return await self.query(
            """
            SELECT code, kind, size, failed_attempts, locked_until
            FROM items
            WHERE locked_until IS NOT NULL AND locked_until > ?
            """,
            (now,),
        )
