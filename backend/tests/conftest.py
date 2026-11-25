"""Pytest configuration and fixtures for OpenClipboard tests."""

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

# Configure the app for an isolated, fast test run BEFORE importing app modules.
os.environ.setdefault("CLIP_STORAGE", "local")
os.environ.setdefault("CLIP_DB_BACKEND", "sqlite")
os.environ.setdefault("CLIP_DATA_DIR", tempfile.mkdtemp(prefix="openclip-test-"))
os.environ.setdefault("CLIP_MAX_UPLOAD_MB", "10")
os.environ.setdefault("CLIP_MIN_TTL", "30")
os.environ.setdefault("CLIP_DEFAULT_TTL", "300")
os.environ.setdefault("CLIP_MAX_TTL", "86400")
os.environ.setdefault("CLIP_PURGE_INTERVAL", "3600")
os.environ.setdefault("CLIP_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
os.environ.setdefault("CLIP_CORS_ORIGINS", "*")
os.environ.setdefault("CLIP_RATE_LIMIT_SEND", "1000/minute")
os.environ.setdefault("CLIP_RATE_LIMIT_RETRIEVE", "1000/minute")
os.environ.setdefault("CLIP_RATE_LIMIT_FILE", "1000/minute")
os.environ.setdefault("CLIP_RATE_LIMIT_DELETE", "1000/minute")
os.environ.setdefault("CLIP_MAX_FAILED_ATTEMPTS", "5")
os.environ.setdefault("CLIP_LOCKOUT_SECONDS", "300")
os.environ.setdefault("CLIP_PASSWORD_PROTECTION", "true")
os.environ.setdefault("CLIP_ADMIN_ENABLED", "false")


@pytest.fixture
async def client():
    """Async HTTP test client with the FastAPI lifespan started manually.

    httpx's ASGITransport does not run startup/shutdown events, so the
    lifespan context is entered explicitly to initialise the DB, storage,
    cache and purge worker.
    """
    from app.main import app

    async with app.router.lifespan_context(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
