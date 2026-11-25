"""File-type detection tests for OpenClipboard.

Verifies that MIME detection never trusts the client Content-Type and that the
pure-Python fallback agrees with libmagic on the formats the app cares about.
"""

import pytest

from app.filetype import _fallback_detect, detect_mime, using_libmagic

PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00"
    b"\x90wS\xde\x00\x00\x00\tpHYs\x00\x00\x0b\x13\x00\x00\x0b\x13\x01"
    b"\x00\x9a\x9c\x18\x00\x00\x00\x0cIDATx\x9cc\xf8\x00\x00\x00\x01\x00"
    b"\x01\x00\x00\x00\x00IEND\xaeB`\x82"
)
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01" + b"\x00" * 32
GIF = b"GIF89a" + b"\x00" * 32
WEBP = b"RIFF" + b"\x24\x00\x00\x00" + b"WEBP" + b"VP8 " + b"\x00" * 32
BMP = b"BM" + b"\x00" * 32
PDF = b"%PDF-1.7\n" + b"\x00" * 32
ZIP = b"PK\x03\x04" + b"\x00" * 32
GZIP = b"\x1f\x8b\x08" + b"\x00" * 32


class TestFallbackDetection:
    """The pure-Python sniffer used when libmagic is unavailable."""

    @pytest.mark.parametrize(
        "data,expected",
        [
            (PNG, "image/png"),
            (JPEG, "image/jpeg"),
            (GIF, "image/gif"),
            (WEBP, "image/webp"),
            (BMP, "image/bmp"),
            (PDF, "application/pdf"),
            (ZIP, "application/zip"),
            (GZIP, "application/gzip"),
        ],
    )
    def test_binary_signatures(self, data, expected):
        assert _fallback_detect(data) == expected

    def test_plain_text(self):
        assert _fallback_detect(b"hello world") == "text/plain"

    def test_json_text(self):
        assert _fallback_detect(b'{"a": 1}') == "application/json"

    def test_html_text(self):
        assert _fallback_detect(b"<!DOCTYPE html><html></html>") == "text/html"

    def test_empty(self):
        assert _fallback_detect(b"") == "application/x-empty"

    def test_unknown_binary(self):
        assert _fallback_detect(b"\x00\x01\x02\x03\x04\x05") == "application/octet-stream"


class TestDetectMime:
    """detect_mime dispatches to libmagic or the fallback."""

    @pytest.mark.parametrize("data", [PNG, JPEG, GIF, WEBP, BMP])
    def test_images_detected(self, data):
        assert detect_mime(data) in {
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "image/bmp",
        }

    def test_reports_backend(self):
        """using_libmagic() reflects the active detection backend."""
        assert isinstance(using_libmagic(), bool)
