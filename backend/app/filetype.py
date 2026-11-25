"""File-type detection with a pure-Python fallback.

`python-magic` (libmagic) is the preferred detector and is what the Docker image
installs. On hosts where libmagic is unavailable (e.g. a bare macOS dev box or a
CI runner without the shared library) importing `magic` raises ImportError. To
keep the security guarantees identical — never trust the client Content-Type —
we fall back to an explicit magic-byte sniffer that covers every format this
application accepts or rejects.
"""
from __future__ import annotations

import logging

log = logging.getLogger("openclip.filetype")

try:  # pragma: no cover - depends on host libraries
    import magic as _magic

    _HAS_LIBMAGIC = True
except Exception:  # pragma: no cover - depends on host libraries
    _magic = None
    _HAS_LIBMAGIC = False
    log.warning(
        "libmagic not available — falling back to built-in magic-byte detection"
    )

# --- Signature tables -------------------------------------------------------

# (offset, signature, mime) checked in order; first match wins.
_SIGNATURES: tuple[tuple[int, bytes, str], ...] = (
    (0, b"\x89PNG\r\n\x1a\n", "image/png"),
    (0, b"\xff\xd8\xff", "image/jpeg"),
    (0, b"GIF87a", "image/gif"),
    (0, b"GIF89a", "image/gif"),
    (0, b"BM", "image/bmp"),
    (0, b"RIFF", "application/octet-stream"),  # refined below for WEBP
    (0, b"%PDF-", "application/pdf"),
    (0, b"PK\x03\x04", "application/zip"),
    (0, b"PK\x05\x06", "application/zip"),
    (0, b"\x1f\x8b", "application/gzip"),
    (0, b"BZh", "application/x-bzip2"),
    (0, b"\xfd7zXZ\x00", "application/x-xz"),
    (0, b"7z\xbc\xaf\x27\x1c", "application/x-7z-compressed"),
    (0, b"Rar!\x1a\x07", "application/vnd.rar"),
    (0, b"OggS", "application/ogg"),
    (0, b"ID3", "audio/mpeg"),
    (0, b"fLaC", "audio/flac"),
    (0, b"\x00\x00\x00\x18ftyp", "video/mp4"),
    (0, b"\x00\x00\x00\x20ftyp", "video/mp4"),
    (0, b"\x1aE\xdf\xa3", "video/webm"),
    (0, b"SQLite format 3\x00", "application/vnd.sqlite3"),
    (0, b"{\\rtf", "application/rtf"),
)

_TEXT_PREFIXES = (
    b"<?xml",
    b"<!DOCTYPE",
    b"<html",
    b"<HTML",
    b"{",
    b"[",
)


def _detect_webp(data: bytes) -> bool:
    return len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _looks_like_text(data: bytes) -> bool:
    """Heuristic: valid UTF-8 with no NUL bytes in the sampled prefix."""
    if not data:
        return False
    if b"\x00" in data:
        return False
    try:
        data.decode("utf-8")
    except UnicodeDecodeError:
        return False
    return True


def _fallback_detect(data: bytes) -> str:
    """Pure-Python MIME detection used when libmagic is unavailable."""
    if not data:
        return "application/x-empty"

    for offset, signature, mime in _SIGNATURES:
        if data[offset : offset + len(signature)] == signature:
            if signature == b"RIFF" and _detect_webp(data):
                return "image/webp"
            if signature == b"RIFF" and data[8:12] == b"WAVE":
                return "audio/wav"
            if signature == b"RIFF" and data[8:12] == b"AVI ":
                return "video/x-msvideo"
            if signature == b"RIFF":
                continue
            return mime

    if _looks_like_text(data):
        lowered = data.lstrip()[:16]
        for prefix in _TEXT_PREFIXES:
            if lowered.startswith(prefix):
                if prefix in (b"<?xml",):
                    return "text/xml"
                if prefix in (b"<!DOCTYPE", b"<html", b"<HTML"):
                    return "text/html"
                if prefix in (b"{", b"["):
                    return "application/json"
        return "text/plain"

    return "application/octet-stream"


def detect_mime(data: bytes) -> str:
    """Return the detected MIME type for a byte prefix.

    Uses libmagic when present, otherwise the built-in signature sniffer.
    The client-supplied Content-Type is never consulted.
    """
    if _HAS_LIBMAGIC and _magic is not None:
        try:
            return _magic.from_buffer(data, mime=True)
        except Exception:  # pragma: no cover - libmagic runtime failure
            log.exception("libmagic detection failed — using fallback")
    return _fallback_detect(data)


def using_libmagic() -> bool:
    """True when libmagic backs detection (used by /health and tests)."""
    return _HAS_LIBMAGIC
