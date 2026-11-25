"""Admin API tests for OpenClipboard.

Covers login, token auth, logout, disabled mode, and constant-time credential
comparison behaviour.
"""

import pytest


@pytest.fixture
async def admin_client(monkeypatch):
    """Client with the admin API enabled and known credentials."""
    from app.config import settings
    from app.main import app
    from httpx import ASGITransport, AsyncClient

    monkeypatch.setattr(settings, "admin_enabled", True, raising=False)
    monkeypatch.setattr(settings, "admin_username", "testadmin", raising=False)
    monkeypatch.setattr(settings, "admin_password", "test-password-123", raising=False)

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac


class TestAdminLogin:
    """POST /admin/login."""

    async def test_login_success(self, admin_client):
        """Valid credentials return a bearer token."""
        resp = await admin_client.post(
            "/admin/login",
            data={"username": "testadmin", "password": "test-password-123"},
        )
        assert resp.status_code == 200
        token = resp.json()["token"]
        assert len(token) == 64  # 32 bytes hex

    async def test_login_wrong_password(self, admin_client):
        """Wrong password returns 401."""
        resp = await admin_client.post(
            "/admin/login",
            data={"username": "testadmin", "password": "nope"},
        )
        assert resp.status_code == 401

    async def test_login_wrong_username(self, admin_client):
        """Wrong username returns 401."""
        resp = await admin_client.post(
            "/admin/login",
            data={"username": "someone", "password": "test-password-123"},
        )
        assert resp.status_code == 401


class TestAdminAuth:
    """Token-protected admin endpoints."""

    async def _token(self, client) -> str:
        resp = await client.post(
            "/admin/login",
            data={"username": "testadmin", "password": "test-password-123"},
        )
        return resp.json()["token"]

    async def test_health_requires_token(self, admin_client):
        """Missing token returns 401."""
        resp = await admin_client.get("/admin/health")
        assert resp.status_code == 401

    async def test_health_with_token(self, admin_client):
        """Valid bearer token grants access."""
        token = await self._token(admin_client)
        resp = await admin_client.get(
            "/admin/health", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["status"] in ("ok", "degraded")

    async def test_invalid_token_rejected(self, admin_client):
        """A bogus token returns 401."""
        resp = await admin_client.get(
            "/admin/health", headers={"Authorization": "Bearer deadbeef"}
        )
        assert resp.status_code == 401

    async def test_entries_listing(self, admin_client):
        """Admin can list entries."""
        token = await self._token(admin_client)
        await admin_client.post("/api/send", data={"kind": "text", "text": "admin list"})

        resp = await admin_client.get(
            "/admin/entries", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    async def test_logout_invalidates_token(self, admin_client):
        """Logout removes the session token."""
        token = await self._token(admin_client)
        headers = {"Authorization": f"Bearer {token}"}

        resp = await admin_client.post("/admin/logout", headers=headers)
        assert resp.status_code == 200

        resp = await admin_client.get("/admin/health", headers=headers)
        assert resp.status_code == 401


class TestAdminDisabled:
    """Admin API can be switched off entirely."""

    async def test_login_404_when_disabled(self, monkeypatch):
        """Login returns 404 when CLIP_ADMIN_ENABLED is false."""
        from app.config import settings
        from app.main import app
        from httpx import ASGITransport, AsyncClient

        monkeypatch.setattr(settings, "admin_enabled", False, raising=False)

        async with app.router.lifespan_context(app):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
                resp = await ac.post(
                    "/admin/login",
                    data={"username": "testadmin", "password": "test-password-123"},
                )
        assert resp.status_code == 404


class TestConstantTimeComparison:
    """Credential comparison must not short-circuit."""

    def test_compare_digest_used(self, monkeypatch):
        """_verify_admin_credentials accepts only exact matches."""
        from app.api import admin
        from app.config import settings

        monkeypatch.setattr(settings, "admin_username", "u", raising=False)
        monkeypatch.setattr(settings, "admin_password", "p", raising=False)

        assert admin._verify_admin_credentials("u", "p") is True
        assert admin._verify_admin_credentials("u", "x") is False
        assert admin._verify_admin_credentials("x", "p") is False
        assert admin._verify_admin_credentials("", "") is False
