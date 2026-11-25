"""API endpoint tests for OpenClipboard.

Covers: send, retrieve, item info, file download, delete, stats, health.
"""

import io
import time


class TestSendEndpoint:
    """Tests for POST /api/send."""

    async def test_send_text_success(self, client):
        """Sending plain text returns a 12-char code."""
        resp = await client.post(
            "/api/send",
            data={"kind": "text", "text": "hello world", "ttl": "300"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["code"]) == 12
        assert data["kind"] == "text"
        assert data["size"] == len("hello world")
        assert data["ttl"] == 300
        assert data["one_shot"] is False

    async def test_send_text_default_ttl(self, client):
        """Text send without ttl uses default."""
        resp = await client.post(
            "/api/send",
            data={"kind": "text", "text": "default ttl"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ttl"] == 300

    async def test_send_invalid_kind(self, client):
        """Invalid kind returns 422."""
        resp = await client.post(
            "/api/send",
            data={"kind": "invalid", "text": "x"},
        )
        assert resp.status_code == 422

    async def test_send_text_missing_text(self, client):
        """Text kind without text body returns 422."""
        resp = await client.post(
            "/api/send",
            data={"kind": "text"},
        )
        assert resp.status_code == 422

    async def test_send_ttl_out_of_range(self, client):
        """TTL below min or above max returns 422."""
        resp = await client.post(
            "/api/send",
            data={"kind": "text", "text": "x", "ttl": "10"},
        )
        assert resp.status_code == 422

        resp = await client.post(
            "/api/send",
            data={"kind": "text", "text": "x", "ttl": "999999"},
        )
        assert resp.status_code == 422

    async def test_send_one_shot(self, client):
        """One-shot text entry is consumed by the first retrieve."""
        resp = await client.post(
            "/api/send",
            data={"kind": "text", "text": "burn after read", "one_shot": "1"},
        )
        assert resp.status_code == 200
        code = resp.json()["code"]

        # First retrieve succeeds and returns the body
        resp = await client.get(f"/api/retrieve/{code}")
        assert resp.status_code == 200
        assert resp.json()["text"] == "burn after read"

        # Second retrieve returns 410 (consumed)
        resp = await client.get(f"/api/retrieve/{code}")
        assert resp.status_code == 410


class TestRetrieveEndpoint:
    """Tests for GET /api/retrieve/{code}."""

    async def test_retrieve_valid_code(self, client):
        """Retrieving a valid code returns the content."""
        send = await client.post(
            "/api/send",
            data={"kind": "text", "text": "retrieve me"},
        )
        code = send.json()["code"]

        resp = await client.get(f"/api/retrieve/{code}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["item"]["code"] == code
        assert data["text"] == "retrieve me"

    async def test_retrieve_invalid_format(self, client):
        """Non-12-char code returns 400."""
        resp = await client.get("/api/retrieve/short")
        assert resp.status_code == 400

    async def test_retrieve_nonexistent_code(self, client):
        """Unknown 12-char code returns 404."""
        resp = await client.get("/api/retrieve/AAAAAAAAAAAA")
        assert resp.status_code == 404

    async def test_retrieve_expired_code(self, client):
        """Expired code returns 410 and is lazily purged."""
        from app import deps

        send = await client.post(
            "/api/send",
            data={"kind": "text", "text": "soon expired", "ttl": "30"},
        )
        code = send.json()["code"]

        # Force expiry in the metadata store instead of sleeping for the TTL.
        await deps.db.execute(
            "UPDATE items SET expires_at = ? WHERE code = ?", (time.time() - 1, code)
        )

        resp = await client.get(f"/api/retrieve/{code}")
        assert resp.status_code == 410

        # The row was lazily purged, so it is now a plain 404.
        resp = await client.get(f"/api/retrieve/{code}")
        assert resp.status_code == 404


class TestItemInfoEndpoint:
    """Tests for GET /api/item/{code}."""

    async def test_item_info_valid(self, client):
        """Item info returns metadata for valid code."""
        send = await client.post(
            "/api/send",
            data={"kind": "text", "text": "info check"},
        )
        code = send.json()["code"]

        resp = await client.get(f"/api/item/{code}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == code
        assert data["kind"] == "text"

    async def test_item_info_invalid_format(self, client):
        """Invalid code format returns 400."""
        resp = await client.get("/api/item/abc")
        assert resp.status_code == 400


class TestFileDownloadEndpoint:
    """Tests for GET /api/file/{code}."""

    async def test_download_file(self, client):
        """Downloading a file returns the uploaded bytes."""
        content = b"file contents here"
        resp = await client.post(
            "/api/send",
            data={"kind": "file"},
            files={"file": ("test.txt", io.BytesIO(content), "text/plain")},
        )
        assert resp.status_code == 200
        code = resp.json()["code"]

        resp = await client.get(f"/api/file/{code}")
        assert resp.status_code == 200
        assert resp.content == content

    async def test_download_nonexistent(self, client):
        """Downloading unknown code returns 404."""
        resp = await client.get("/api/file/AAAAAAAAAAAA")
        assert resp.status_code == 404


class TestDeleteEndpoint:
    """Tests for DELETE /api/item/{code}."""

    async def test_delete_item(self, client):
        """Deleting an item returns 204 and makes it unretrievable."""
        send = await client.post(
            "/api/send",
            data={"kind": "text", "text": "to be deleted"},
        )
        code = send.json()["code"]

        resp = await client.delete(f"/api/item/{code}")
        assert resp.status_code == 204

        resp = await client.get(f"/api/retrieve/{code}")
        assert resp.status_code == 404


class TestStatsEndpoint:
    """Tests for GET /api/stats."""

    async def test_stats_returns_counts(self, client):
        """Stats returns active count and bytes."""
        await client.post(
            "/api/send",
            data={"kind": "text", "text": "stats test"},
        )

        resp = await client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "active" in data
        assert "bytes" in data
        assert data["active"] >= 1


class TestHealthEndpoint:
    """Tests for GET /health."""

    async def test_health_ok(self, client):
        """Health endpoint returns ok status."""
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] in ("ok", "degraded")
        assert data["app"] == "OpenClipboard"


class TestSecurityHeaders:
    """Tests for security headers on all responses."""

    async def test_security_headers_present(self, client):
        """All responses include required security headers."""
        resp = await client.get("/health")
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("Referrer-Policy") == "no-referrer"
        assert "Content-Security-Policy" in resp.headers
        assert "Strict-Transport-Security" in resp.headers
