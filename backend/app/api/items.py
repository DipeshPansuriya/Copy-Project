"""HTTP API: send / retrieve / download / delete / stats."""
from __future__ import annotations

import magic
import secrets
import time
import urllib.parse
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse

from .. import deps
from ..cache import cache
from ..config import settings
from ..schemas import ItemInfo, RetrieveResponse, SendResponse, StatsResponse, _iso, info_from_row

router = APIRouter(prefix="/api")

CODE_LENGTH = 12
CODE_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
TEXT_KIND = "text"
MAX_CODE_RETRIES = 25

# Lockout settings for brute-force protection (from config)
MAX_FAILED_ATTEMPTS = settings.max_failed_attempts
LOCKOUT_SECONDS = settings.lockout_seconds

# Allowed real MIME types for images (verified by magic bytes, not client header)
ALLOWED_IMAGE_MIMES = {"image/png", "image/jpeg", "image/gif", "image/webp", "image/bmp"}

# Magic-byte signatures for executable formats that must be rejected
EXECUTABLE_MAGIC = {
    b"\x7fELF": "ELF executable (Linux/Unix)",
    b"MZ": "PE executable (Windows .exe/.dll)",
    b"\xca\xfe\xba\xbe": "Mach-O universal (macOS)",
    b"\xca\xfe\xba\xbf": "Mach-O 64-bit (macOS)",
    b"\xfe\xed\xfa\xce": "Mach-O 32-bit (macOS)",
    b"\xfe\xed\xfa\xcf": "Mach-O 64-bit (macOS)",
}

# Text/script shebangs that indicate executable scripts
SCRIPT_SHEBANGS = (b"#!",)

# Chunk size for streaming uploads/downloads (64 KB)
CHUNK_SIZE = 64 * 1024

# Bytes needed for magic byte detection
MAGIC_BYTES_LEN = 4096

# Cache TTLs (seconds)
CACHE_STATS_TTL = 30
CACHE_ENTRY_TTL = 60


def _gen_code() -> str:
    """Generate a secure random code: 12 chars, case-sensitive alphanumeric (62^12 ~ 3.2 sextillion)."""
    return "".join(secrets.choice(CODE_CHARS) for _ in range(CODE_LENGTH))


def _valid_code(code: str) -> bool:
    """Validate code format: 12 case-sensitive alphanumeric characters."""
    return bool(code and len(code) == CODE_LENGTH and all(c in CODE_CHARS for c in code))


def _is_executable(data: bytes) -> bool:
    """Detect executable files by magic bytes, regardless of extension."""
    if len(data) < 4:
        return False
    for magic_bytes in EXECUTABLE_MAGIC:
        if data.startswith(magic_bytes):
            return True
    if data.startswith(SCRIPT_SHEBANGS):
        return True
    return False


def _verify_image_mime(data: bytes) -> str:
    """Return the real MIME type of image data using magic bytes.

    Raises HTTPException(422) if it is not a recognized image format.
    """
    mime = magic.from_buffer(data, mime=True)
    if mime not in ALLOWED_IMAGE_MIMES:
        raise HTTPException(
            status_code=422,
            detail=f"Uploaded file is not a supported image (detected: {mime})",
        )
    return mime


async def _stream_upload_with_validation(
    storage,
    file: UploadFile,
    object_key: str,
    max_bytes: int,
    kind: str,
):
    """Stream an uploaded file directly to storage without loading into memory.

    Reads the file in chunks, enforces size limits per-chunk, captures magic
    bytes from the first chunks for type verification, and streams everything
    to storage via put_stream().

    Returns (size, content_type).
    """
    size = 0
    magic_prefix = bytearray()
    chunks: list[bytes] = []

    while True:
        chunk = await file.read(CHUNK_SIZE)
        if not chunk:
            break

        size += len(chunk)
        if size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {max_bytes // (1024 * 1024)} MB limit",
            )

        # Capture magic bytes from the beginning
        if len(magic_prefix) < MAGIC_BYTES_LEN:
            needed = MAGIC_BYTES_LEN - len(magic_prefix)
            magic_prefix.extend(chunk[:needed])

        chunks.append(chunk)

    if size == 0:
        raise HTTPException(status_code=422, detail="Empty content")

    # Determine content type from magic bytes
    magic_bytes = bytes(magic_prefix)
    if kind == "image":
        content_type = _verify_image_mime(magic_bytes)
    else:
        if _is_executable(magic_bytes):
            raise HTTPException(status_code=422, detail="Executable file types are not allowed")
        content_type = magic.from_buffer(magic_bytes, mime=True)

    # Stream all chunks to storage
    async def _full_stream():
        for chunk in chunks:
            yield chunk

    await storage.put_stream(object_key, _full_stream(), content_type)
    return size, content_type


@router.post("/send", response_model=SendResponse)
@deps.limiter.limit(settings.rate_limit_send)
async def send(
    request: Request,
    kind: str = Form("text"),
    ttl: int | None = Form(None),
    one_shot: int = Form(0),
    text: str | None = Form(None),
    file: UploadFile | None = File(None),
    password: str | None = Form(None),
):
    """Create a clipboard entry.

    kind=text   → `text` form field
    kind=image  → `file` upload (image/*, verified by magic bytes)
    kind=file   → `file` upload (any type)

    Returns a 12-character case-sensitive alphanumeric retrieval code.
    Content is hard-deleted after `ttl` seconds (or after first download when one_shot=1).

    Optional `password` field encrypts the content; the same password is
    required to retrieve it.

    Large files are streamed in chunks — not loaded fully into memory.
    """
    import bcrypt

    db = deps.get_db()
    storage = deps.get_storage()
    now = time.time()

    if kind not in ("text", "image", "file"):
        raise HTTPException(status_code=422, detail="kind must be text, image or file")

    ttl = ttl if ttl is not None else settings.default_ttl
    if not (settings.min_ttl <= ttl <= settings.max_ttl):
        raise HTTPException(
            status_code=422,
            detail=f"ttl must be between {settings.min_ttl} and {settings.max_ttl} seconds",
        )

    # Hash password if provided
    password_hash: str | None = None
    if password:
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    filename: str | None = None
    content_type: str | None = None

    if kind == TEXT_KIND:
        if text is None or not text:
            raise HTTPException(status_code=422, detail="No text provided")
        data = text.encode("utf-8")
        content_type = "text/plain; charset=utf-8"
        size = len(data)
    else:
        if file is None or file.filename is None:
            raise HTTPException(status_code=422, detail="No file uploaded")
        # Stream upload directly to storage with size limit and magic verification
        object_key = f"{uuid.uuid4().hex}/{uuid.uuid4().hex}"
        size, content_type = await _stream_upload_with_validation(
            storage, file, object_key, settings.max_upload_bytes, kind
        )

        # Sanitize filename: strip path components, keep basename only.
        raw_name = file.filename or f"{code}-clipboard"
        basename = raw_name.split("\\")[-1].split("/")[-1]
        filename = urllib.parse.quote(basename)

    if size == 0:
        raise HTTPException(status_code=422, detail="Empty content")

    # For text, we still need to store the blob
    if kind == TEXT_KIND:
        object_key = f"{uuid.uuid4().hex}/{uuid.uuid4().hex}"
        await storage.put(object_key, data, content_type)

    # Pick a free 12-character code.
    code: str | None = None
    for _ in range(MAX_CODE_RETRIES):
        candidate = _gen_code()
        existing = await db.get_item(candidate)
        if existing is None:
            code = candidate
            break
        if existing["expires_at"] < now:
            # Stale row not swept yet — reclaim it.
            await storage.delete(existing["object_key"])
            await db.delete_item(candidate)
            code = candidate
            break
    if code is None:
        raise HTTPException(status_code=503, detail="Could not allocate a code, retry soon")

    try:
        await db.create_item(
            code=code,
            kind=kind,
            filename=file.filename if kind != TEXT_KIND else None,
            content_type=content_type,
            size=size,
            object_key=object_key,
            ttl=ttl,
            one_shot=bool(one_shot),
            password_hash=password_hash,
        )
    except Exception:
        # Roll back the blob if the metadata row could not be written.
        await storage.delete(object_key)
        raise HTTPException(status_code=500, detail="Failed to store content")

    # Invalidate stats cache since new item was created
    await cache.delete("stats:snapshot")

    return SendResponse(
        code=code,
        kind=kind,
        filename=file.filename if kind != TEXT_KIND else None,
        size=size,
        ttl=ttl,
        created_at=_iso(now),
        expires_at=_iso(now + ttl),
        one_shot=bool(one_shot),
        url="/",
    )


async def _live_item(code: str):
    """Return a live item row, or raise 404/410/423.

    Lazy purge: expired or already-retrieved one-shot items are deleted here
    so the code can be reused.
    Checks lockout status and returns 423 if item is temporarily locked.
    """
    db = deps.get_db()
    row = await db.get_item(code)
    if row is None:
        raise HTTPException(status_code=404, detail="No such code (it may have expired)")

    # Check lockout status
    is_locked, unlock_time = await db.is_locked(code)
    if is_locked:
        remaining = int(unlock_time - time.time()) if unlock_time else LOCKOUT_SECONDS
        raise HTTPException(
            status_code=423,
            detail=f"Item temporarily locked due to failed attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )

    now = time.time()
    if row["expires_at"] < now or (row["one_shot"] and row["retrieved_at"] is not None):
        storage = deps.get_storage()
        await storage.delete(row["object_key"])
        await db.delete_item(row["code"])
        raise HTTPException(status_code=410, detail="This code has expired and was deleted")
    return row


@router.get("/retrieve/{code}", response_model=RetrieveResponse)
@deps.limiter.limit(settings.rate_limit_retrieve)
async def retrieve(
    request: Request,
    code: str,
    password: str | None = None,
):
    """Look up a code. Returns metadata + a download URL.

    For text entries the text body is included inline for instant display.
    If the item is password-protected, the `password` query parameter is required.
    """
    import bcrypt

    if not _valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid code format")
    db = deps.get_db()

    # Check cache first for hot entry metadata
    cache_key = f"entry:{code}"
    cached = await cache.get(cache_key)
    if cached:
        row = cached
    else:
        row = await db.get_item(code)
        if row is None:
            raise HTTPException(status_code=404, detail="No such code (it may have expired)")
        await cache.set(cache_key, row, ttl=CACHE_ENTRY_TTL)

    # Check lockout status
    is_locked, unlock_time = await db.is_locked(code)
    if is_locked:
        remaining = int(unlock_time - time.time()) if unlock_time else LOCKOUT_SECONDS
        raise HTTPException(
            status_code=423,
            detail=f"Item temporarily locked due to failed attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)},
        )

    # Verify password if item is password-protected
    if row["password_hash"]:
        if password is None:
            raise HTTPException(
                status_code=401,
                detail="Password required for this item",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not bcrypt.checkpw(password.encode("utf-8"), row["password_hash"].encode("utf-8")):
            # Wrong password — record failed attempt and lockout if threshold reached
            await db.increment_failed_attempt(code)
            attempts_row = await db.get_item(code)
            if attempts_row and attempts_row["failed_attempts"] >= MAX_FAILED_ATTEMPTS:
                raise HTTPException(
                    status_code=423,
                    detail=f"Too many failed attempts. Item locked for {LOCKOUT_SECONDS // 60} minutes.",
                    headers={"Retry-After": str(LOCKOUT_SECONDS)},
                )
            raise HTTPException(status_code=401, detail="Incorrect password")

    # Successful retrieval — reset failed attempts
    await db.reset_failed_attempts(code)

    row = await _live_item(code)
    if row is None:
        raise HTTPException(status_code=410, detail="This code has expired and was deleted")

    result = RetrieveResponse(
        item=info_from_row(row),
        file_url=f"/api/file/{code}",
        text=None,
    )
    if row["kind"] == TEXT_KIND:
        data = await deps.get_storage().get(row["object_key"])
        if data is not None:
            result.text = data.decode("utf-8", errors="replace")
    return result


@router.get("/item/{code}", response_model=ItemInfo)
@deps.limiter.limit(settings.rate_limit_retrieve)
async def item_info(request: Request, code: str):
    """Lightweight status check (used for live countdowns)."""
    if not _valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid code format")
    row = await _live_item(code)
    return info_from_row(row)


@router.get("/file/{code}")
@deps.limiter.limit(settings.rate_limit_file)
async def download_file(request: Request, code: str):
    """Stream the blob. One-shot entries are deleted after the download."""
    if not _valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid code format")
    db = deps.get_db()
    row = await _live_item(code)
    storage = deps.get_storage()

    stream = await storage.stream(row["object_key"])
    if stream is None:
        raise HTTPException(status_code=404, detail="Object missing in storage")
    gen, size, content_type = stream
    if not content_type:
        content_type = row["content_type"] or "application/octet-stream"

    await db.increment_download(code)
    one_shot = bool(row["one_shot"])

    async def _payload():
        try:
            async for chunk in gen:
                yield chunk
        finally:
            if one_shot:
                # Burn after reading.
                try:
                    await storage.delete(row["object_key"])
                    await db.delete_item(code)
                except Exception:
                    pass

    disposition = "inline" if row["kind"] in ("text", "image") else "attachment"
    filename = row["filename"] or f"{code}-clipboard"
    if urllib.parse.unquote(filename) != filename:
        filename = urllib.parse.unquote(filename)

    return StreamingResponse(
        _payload(),
        media_type=content_type,
        headers={
            "Content-Disposition": f"{disposition}; filename=\"{filename}\"",
            "Content-Length": str(size),
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.delete("/item/{code}")
@deps.limiter.limit(settings.rate_limit_delete)
async def delete_item(request: Request, code: str):
    """Delete a live entry immediately (the code is its capability)."""
    if not _valid_code(code):
        raise HTTPException(status_code=400, detail="Invalid code format")
    db = deps.get_db()
    row = await db.get_item(code)
    if row is None:
        raise HTTPException(status_code=404, detail="No such code")
    await deps.get_storage().delete(row["object_key"])
    await db.delete_item(code)
    await cache.delete(f"entry:{code}")
    await cache.delete("stats:snapshot")
    return Response(status_code=204)


@router.get("/stats", response_model=StatsResponse)
@deps.limiter.limit(settings.rate_limit_retrieve)
async def stats(request: Request):
    """Return active item count and total bytes (cached for 30 seconds)."""
    cached = await cache.get("stats:snapshot")
    if cached is not None:
        return StatsResponse(**cached)
    result = StatsResponse(**await deps.db.stats())
    await cache.set("stats:snapshot", result.model_dump(), ttl=CACHE_STATS_TTL)
    return result
