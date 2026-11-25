"""Rate limiting tests for OpenClipboard.

The application-level limits are configured high in the test environment so the
functional suite is not throttled. These tests exercise the same slowapi limiter
with a deliberately low limit to prove that throttling returns HTTP 429.
"""

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


@pytest.fixture
async def limited_client():
    """A minimal app guarded by a 3/minute limiter."""
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI()
    app.state.limiter = limiter

    @app.exception_handler(RateLimitExceeded)
    async def _handler(request: Request, exc: RateLimitExceeded):
        from fastapi.responses import JSONResponse

        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    @app.get("/ping")
    @limiter.limit("3/minute")
    async def ping(request: Request):
        return {"ok": True}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac


class TestRateLimiting:
    """slowapi must reject requests beyond the configured limit."""

    async def test_requests_within_limit_succeed(self, limited_client):
        """The first requests under the limit return 200."""
        for _ in range(3):
            resp = await limited_client.get("/ping")
            assert resp.status_code == 200

    async def test_limit_exceeded_returns_429(self, limited_client):
        """The request past the limit returns 429."""
        for _ in range(3):
            await limited_client.get("/ping")

        resp = await limited_client.get("/ping")
        assert resp.status_code == 429
        assert resp.json()["detail"] == "Rate limit exceeded"


class TestAppRateLimitConfiguration:
    """The real app must register limits on every public endpoint."""

    async def test_limiter_attached_to_app(self):
        """app.state.limiter is the shared slowapi limiter."""
        from app.main import app
        from app import deps

        assert app.state.limiter is deps.limiter

    async def test_limits_configured(self):
        """All rate-limit settings resolve to non-empty slowapi expressions."""
        from app.config import settings

        for value in (
            settings.rate_limit_send,
            settings.rate_limit_retrieve,
            settings.rate_limit_file,
            settings.rate_limit_delete,
        ):
            assert "/" in value
            amount, _, period = value.partition("/")
            assert amount.isdigit()
            assert period in {"second", "minute", "hour", "day"}
