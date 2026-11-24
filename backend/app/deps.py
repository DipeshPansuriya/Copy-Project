"""Application singletons, wired together in main.py."""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from .cache import cache
from .config import settings
from .storage import Storage

db: "DatabaseProtocol" | None = None
storage: Storage | None = None

# Rate limiter keyed by client IP. Limits applied per-route in api/items.py.
limiter = Limiter(key_func=get_remote_address)


# Database protocol — both sqlite.db.Database and db_postgres.Database implement this
class DatabaseProtocol:
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def execute(self, sql: str, params: tuple = ()) -> None: ...
    async def query(self, sql: str, params: tuple = ()) -> list[dict]: ...
    async def create_item(self, *, code: str, kind: str, filename: str | None,
                          content_type: str, size: int, object_key: str,
                          ttl: int, one_shot: bool,
                          password_hash: str | None = None) -> None: ...
    async def get_item(self, code: str) -> dict | None: ...
    async def increment_download(self, code: str) -> None: ...
    async def mark_retrieved(self, code: str) -> None: ...
    async def delete_item(self, code: str) -> None: ...
    async def expired_items(self, now: float | None = None) -> list[dict]: ...
    async def stats(self) -> dict: ...
    async def increment_failed_attempt(self, code: str) -> int: ...
    async def reset_failed_attempts(self, code: str) -> None: ...
    async def is_locked(self, code: str) -> tuple[bool, float | None]: ...


def get_db() -> DatabaseProtocol:
    assert db is not None, "app not started"
    return db


def get_storage() -> Storage:
    assert storage is not None, "app not started"
    return storage


def create_database() -> DatabaseProtocol:
    """Factory: create the right database backend based on settings."""
    if settings.db_backend == "postgres":
        from .db_postgres import Database as PostgresDatabase
        return PostgresDatabase()
    else:
        from .db import Database as SqliteDatabase
        return SqliteDatabase(str(settings.data_dir / "clipboard.db"))
