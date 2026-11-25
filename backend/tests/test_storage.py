"""Storage backend tests for OpenClipboard."""

import tempfile

from app.storage import LocalStorage


class TestLocalStorage:
    """Tests for LocalStorage backend."""

    async def test_put_and_get(self, client):
        """Storing and retrieving data works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
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

    async def test_accepts_path_root(self, client):
        """LocalStorage accepts a pathlib.Path as well as a str root."""
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(Path(tmpdir))
            await storage.put("p/key", b"path root", "text/plain")
            assert await storage.get("p/key") == b"path root"

    async def test_missing_key_returns_none(self, client):
        """Reading an absent key returns None instead of raising."""
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            assert await storage.get("nope/missing") is None
            assert await storage.stat("nope/missing") is None
            assert await storage.stream("nope/missing") is None
