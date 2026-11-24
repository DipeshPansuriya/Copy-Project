"""Pydantic response models."""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel


def _iso(ts: float | None) -> Optional[str]:
    if ts is None:
        return None
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


class SendResponse(BaseModel):
    code: str
    kind: str
    filename: Optional[str] = None
    size: int
    ttl: int
    created_at: str
    expires_at: str
    one_shot: bool
    url: str


class ItemInfo(BaseModel):
    code: str
    kind: str
    filename: Optional[str] = None
    content_type: Optional[str] = None
    size: int
    created_at: str
    expires_at: str
    one_shot: bool
    retrieved_at: Optional[str] = None
    downloads: int
    expired: bool


class RetrieveResponse(BaseModel):
    item: ItemInfo
    file_url: str
    text: Optional[str] = None


class StatsResponse(BaseModel):
    active: int
    bytes: int


def info_from_row(row: dict) -> ItemInfo:
    return ItemInfo(
        code=row["code"],
        kind=row["kind"],
        filename=row["filename"],
        content_type=row["content_type"],
        size=int(row["size"]),
        created_at=_iso(row["created_at"]),
        expires_at=_iso(row["expires_at"]),
        one_shot=bool(row["one_shot"]),
        retrieved_at=_iso(row["retrieved_at"]),
        downloads=int(row["downloads"]),
        expired=row["expires_at"] < time.time(),
    )
