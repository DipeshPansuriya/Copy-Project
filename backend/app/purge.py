"""Background purge worker.

A single async loop sweeps the database every `purge_interval` seconds and
permanently deletes everything that is past its TTL (or a one-shot item that
has already been retrieved): both the object-storage blob and the metadata row.
"""
from __future__ import annotations

import asyncio
import logging
import time

from .config import settings
from .db import Database
from .storage import Storage

log = logging.getLogger("openclip.purge")


async def purge_once(db: Database, storage: Storage) -> int:
    deleted = 0
    for row in await db.expired_items():
        try:
            await storage.delete(row["object_key"])
        except Exception:
            log.exception("failed deleting blob %s", row["object_key"])
            continue
        try:
            await db.delete_item(row["code"])
            deleted += 1
            log.info("purged item %s (%s, %s bytes)", row["code"], row["kind"], row["size"])
        except Exception:
            log.exception("failed deleting row %s", row["code"])
    return deleted


async def purge_loop(db: Database, storage: Storage) -> None:
    while True:
        await asyncio.sleep(settings.purge_interval)
        try:
            await purge_once(db, storage)
        except Exception:
            log.exception("purge sweep failed")
