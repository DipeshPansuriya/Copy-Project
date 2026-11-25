"""Storage backend tests for OpenClipboard."""

import pytest


class TestLocalStorage:
    """Tests for LocalStorage backend."""

    async def test_put_and_get(self, client):
        """Storing and retrieving data works."""
        from app.storage import LocalStorage
        from app.config import settings
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tempfile.TemporaryDirectory().name if False else tmpdir)
            await storage.put("test/key", b"hello world", "text/plain")

            data = await storage.get("test/key")
            assert data == b"hello world"

            stat = await storage.stat("test/key")
            assert stat is not None
            assert stat[0] == len(b"hello world")

            await storage.delete("test/key")
            data = await storage.get("test/key")
            assert data is None

    async def test_put_stream(self, client):
        """Streaming upload works."""
        from app.storage import LocalStorage
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)

            async def stream():
                yield b"chunk1"
                yield b"chunk2"
                yield b"chunk3"

            size = await storage.put_stream("stream/key", stream(), "text/plain")
            assert size == 18  # "chunk1" + "chunk2" + "chunk3" = 6 bytes each

            data = await storage.get("stream/key")
            assert data == b"chunk1chunk2chunk3"
