"""Blob storage backends.

- MinioStorage: open-source MinIO object storage (S3 API) — the production
  backend. Supports streaming uploads/downloads.
- LocalStorage: plain files on disk, for quick local development without MinIO.
  Supports streaming uploads/downloads.

Both implement the same async interface so the rest of the app is agnostic.
"""
from __future__ import annotations

import io
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from anyio import to_thread

from .config import settings


class Storage:
    async def put(self, key: str, data: bytes, content_type: str) -> None: ...
    async def put_stream(
        self, key: str, stream: AsyncIterator[bytes], content_type: str
    ) -> int: ...  # returns total size
    async def get(self, key: str) -> Optional[bytes]: ...
    async def stat(self, key: str) -> Optional[tuple[int, str]]: ...  # (size, content_type)
    async def delete(self, key: str) -> None: ...
    async def stream(self, key: str) -> Optional[tuple[AsyncIterator[bytes], int, str]]: ...


class LocalStorage(Storage):
    """Files under <data_dir>/blobs. For development only."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self.root / key

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        def _write() -> None:
            path = self._path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)

        await to_thread.run_sync(_write)

    async def put_stream(
        self, key: str, stream: AsyncIterator[bytes], content_type: str
    ) -> int:
        """Stream chunks directly to disk without loading full file into memory."""
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)

        total = 0
        with path.open("wb") as fh:
            async for chunk in stream:
                total += len(chunk)
                await to_thread.run_sync(fh.write, chunk)
        return total

    async def get(self, key: str) -> Optional[bytes]:
        path = self._path(key)

        def _read() -> Optional[bytes]:
            try:
                return path.read_bytes()
            except FileNotFoundError:
                return None

        return await to_thread.run_sync(_read)

    async def stat(self, key: str) -> Optional[tuple[int, str]]:
        path = self._path(key)

        def _stat() -> Optional[tuple[int, str]]:
            try:
                return path.stat().st_size, ""
            except FileNotFoundError:
                return None

        return await to_thread.run_sync(_stat)

    async def delete(self, key: str) -> None:
        path = self._path(key)

        def _unlink() -> None:
            try:
                path.unlink()
            except FileNotFoundError:
                pass

        await to_thread.run_sync(_unlink)

    async def stream(self, key: str) -> Optional[tuple[AsyncIterator[bytes], int, str]]:
        stat = await self.stat(key)
        if stat is None:
            return None

        async def _gen() -> AsyncIterator[bytes]:
            path = self._path(key)
            with path.open("rb") as fh:
                while chunk := await to_thread.run_sync(fh.read, 64 * 1024):
                    yield chunk

        return _gen(), stat[0], stat[1]


class MinioStorage(Storage):
    """Open-source MinIO object storage (S3-compatible)."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = False,
    ) -> None:
        from minio import Minio

        self._client = Minio(
            endpoint, access_key=access_key, secret_key=secret_key, secure=secure
        )
        self._bucket = bucket

    def _ensure_bucket_sync(self) -> None:
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)

    async def ensure_bucket(self) -> None:
        await to_thread.run_sync(self._ensure_bucket_sync)

    async def put(self, key: str, data: bytes, content_type: str) -> None:
        def _put() -> None:
            self._client.put_object(
                self._bucket,
                key,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )

        await to_thread.run_sync(_put)

    async def put_stream(
        self, key: str, stream: AsyncIterator[bytes], content_type: str
    ) -> int:
        """Stream chunks to MinIO using a temp file (MinIO SDK needs seekable stream).

        For very large files, this writes chunks to a temp file then streams
        from disk to MinIO, avoiding full memory load.
        """
        import tempfile

        total = 0
        # Write chunks to a temp file on disk
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
            try:
                async for chunk in stream:
                    total += len(chunk)
                    await to_thread.run_sync(tmp.write, chunk)
            finally:
                await to_thread.run_sync(tmp.close)

        # Stream from temp file to MinIO
        def _put_from_file() -> None:
            with open(tmp_path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                file_size = fh.tell()
                fh.seek(0)
                self._client.put_object(
                    self._bucket,
                    key,
                    fh,
                    length=file_size,
                    content_type=content_type,
                )

        await to_thread.run_sync(_put_from_file)
        os.unlink(tmp_path)
        return total

    async def get(self, key: str) -> Optional[bytes]:
        def _get() -> Optional[bytes]:
            from minio.error import S3Error

            try:
                obj = self._client.get_object(self._bucket, key)
            except S3Error:
                return None
            try:
                return obj.read()
            finally:
                obj.close()
                obj.release_conn()

        return await to_thread.run_sync(_get)

    async def stat(self, key: str) -> Optional[tuple[int, str]]:
        def _stat() -> Optional[tuple[int, str]]:
            from minio.error import S3Error

            try:
                obj = self._client.stat_object(self._bucket, key)
            except S3Error:
                return None
            content_type = (obj.metadata or {}).get("content-type", "application/octet-stream")
            return int(obj.size), content_type

        return await to_thread.run_sync(_stat)

    async def delete(self, key: str) -> None:
        def _delete() -> None:
            from minio.error import S3Error

            try:
                self._client.remove_object(self._bucket, key)
            except S3Error:
                pass  # already gone

        await to_thread.run_sync(_delete)

    async def stream(self, key: str) -> Optional[tuple[AsyncIterator[bytes], int, str]]:
        stat = await self.stat(key)
        if stat is None:
            return None
        size, content_type = stat

        def _open():
            return self._client.get_object(self._bucket, key)

        obj = await to_thread.run_sync(_open)

        async def _gen() -> AsyncIterator[bytes]:
            try:
                while chunk := await to_thread.run_sync(obj.read, 64 * 1024):
                    yield chunk
            finally:
                await to_thread.run_sync(obj.close)
                try:
                    await to_thread.run_sync(obj.release_conn)
                except Exception:
                    pass

        return _gen(), size, content_type


def create_storage() -> Storage:
    if settings.storage_backend == "minio":
        return MinioStorage(
            endpoint=settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            bucket=settings.minio_bucket,
            secure=settings.minio_secure,
        )
    return LocalStorage(settings.data_dir / "blobs")


def ensure_storage_dirs() -> None:
    os.makedirs(settings.data_dir, exist_ok=True)
