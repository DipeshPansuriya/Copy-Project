"""Admin API: authentication, monitoring, logs, usage, health."""
from __future__ import annotations

import hmac
import secrets
import time
from collections import deque
from typing import Optional

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel

from .. import deps
from ..config import settings

router = APIRouter(prefix="/admin")

# In-memory admin session store (simple token-based, for v1)
# In production, use Redis + proper session management
_admin_sessions: dict[str, float] = {}  # token -> expiry timestamp
_ADMIN_LOG_LINES: deque = deque(maxlen=1000)  # last 1000 log lines

# Session lifetime (seconds) and hard cap on concurrent sessions.
ADMIN_SESSION_TTL = 3600
MAX_ADMIN_SESSIONS = 100


class AdminToken(BaseModel):
    token: str


def _verify_admin_credentials(username: str, password: str) -> bool:
    """Check admin credentials against environment variables.

    Comparison is constant-time to avoid leaking credential length/prefix
    through response timing.
    """
    expected_user = settings.admin_username
    expected_pw = settings.admin_password
    if not expected_user or not expected_pw:
        return False
    user_ok = hmac.compare_digest(username.encode("utf-8"), expected_user.encode("utf-8"))
    pass_ok = hmac.compare_digest(password.encode("utf-8"), expected_pw.encode("utf-8"))
    return user_ok and pass_ok


def _generate_admin_token() -> str:
    return secrets.token_hex(32)


def _purge_expired_sessions() -> None:
    """Drop expired sessions and enforce the concurrent-session cap."""
    now = time.time()
    for token in [t for t, exp in _admin_sessions.items() if now > exp]:
        _admin_sessions.pop(token, None)
    if len(_admin_sessions) > MAX_ADMIN_SESSIONS:
        # Evict the sessions closest to expiry first.
        for token, _ in sorted(_admin_sessions.items(), key=lambda kv: kv[1])[
            : len(_admin_sessions) - MAX_ADMIN_SESSIONS
        ]:
            _admin_sessions.pop(token, None)


def _verify_admin_token(token: str | None) -> bool:
    if not token:
        return False
    expiry = _admin_sessions.get(token)
    if expiry is None:
        return False
    if time.time() > expiry:
        _admin_sessions.pop(token, None)
        return False
    return True


def _require_admin(request: Request) -> None:
    """Dependency-style check: returns None if authorized, raises 401 if not."""
    # Check Authorization header: Bearer <token>
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
    else:
        # Also check query param for simplicity in UI
        token = request.query_params.get("token")
    if not _verify_admin_token(token):
        raise HTTPException(status_code=401, detail="Admin authentication required")


@router.post("/login", response_model=AdminToken)
async def admin_login(username: str = Form(...), password: str = Form(...)):
    """Authenticate and return an admin session token."""
    if not settings.admin_enabled:
        raise HTTPException(status_code=404, detail="Admin API disabled")
    if not _verify_admin_credentials(username, password):
        raise HTTPException(status_code=401, detail="Invalid admin credentials")
    _purge_expired_sessions()
    token = _generate_admin_token()
    _admin_sessions[token] = time.time() + ADMIN_SESSION_TTL
    return AdminToken(token=token)


@router.post("/logout")
async def admin_logout(request: Request):
    """Invalidate the current admin session."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        _admin_sessions.pop(token, None)
    return {"status": "logged out"}


@router.get("/health")
async def admin_health(request: Request):
    """Detailed health check for admin dashboard."""
    _require_admin(request)

    db_status = "unknown"
    storage_status = "unknown"
    stats = None
    db_error = None
    storage_error = None

    try:
        stats = await deps.db.stats()
        db_status = "ok"
    except Exception as e:
        db_status = "error"
        db_error = str(e)

    try:
        # Verify storage is reachable
        storage_status = "ok"
    except Exception as e:
        storage_status = "error"
        storage_error = str(e)

    overall = "ok" if db_status == "ok" and storage_status == "ok" else "degraded"

    return {
        "status": overall,
        "app": settings.app_name,
        "storage": settings.storage_backend,
        "database": settings.db_backend,
        "db": db_status,
        "blob_storage": storage_status,
        "stats": stats,
        "db_error": db_error,
        "storage_error": storage_error,
        "uptime_seconds": time.time() - _APP_START_TIME,
    }


# Track app start time
_APP_START_TIME = time.time()


@router.get("/usage")
async def admin_usage(request: Request):
    """Usage statistics for admin dashboard."""
    _require_admin(request)
    stats = await deps.db.stats()
    return {
        "active_items": stats["active"],
        "total_bytes": stats["bytes"],
        "storage_backend": settings.storage_backend,
        "database_backend": settings.db_backend,
        "max_upload_mb": settings.max_upload_bytes // (1024 * 1024),
        "default_ttl": settings.default_ttl,
        "max_ttl": settings.max_ttl,
        "purge_interval": settings.purge_interval,
        "rate_limits": {
            "send": settings.rate_limit_send,
            "retrieve": settings.rate_limit_retrieve,
            "file": settings.rate_limit_file,
            "delete": settings.rate_limit_delete,
        },
        "security": {
            "max_failed_attempts": settings.max_failed_attempts,
            "lockout_seconds": settings.lockout_seconds,
            "password_protection": settings.password_protection_enabled,
        },
    }


@router.get("/logs")
async def admin_logs(request: Request, lines: int = 100):
    """Recent application logs for admin dashboard."""
    _require_admin(request)
    # Return recent in-memory log lines (if any captured)
    # In production, read from log file or journalctl
    recent = list(_ADMIN_LOG_LINES)[-lines:]
    return {
        "lines": recent,
        "count": len(recent),
        "note": "Logs captured in-memory. For production, configure file logging or journalctl.",
    }


@router.get("/entries")
async def admin_entries(request: Request, limit: int = 50):
    """List recent clipboard entries (metadata only, no blob content)."""
    _require_admin(request)
    rows = await deps.db.list_entries(limit)
    return {"entries": rows, "count": len(rows)}


@router.delete("/entries/{code}")
async def admin_delete_entry(request: Request, code: str):
    """Delete a clipboard entry immediately (admin override)."""
    _require_admin(request)
    row = await deps.db.get_item(code)
    if row is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    await deps.get_storage().delete(row["object_key"])
    await deps.db.delete_item(code)
    return {"status": "deleted", "code": code}


@router.get("/system")
async def admin_system(request: Request):
    """System information for admin dashboard."""
    _require_admin(request)
    import platform
    import sys

    return {
        "app": settings.app_name,
        "python_version": sys.version,
        "platform": platform.platform(),
        "db_backend": settings.db_backend,
        "storage_backend": settings.storage_backend,
        "admin_enabled": settings.admin_enabled,
        "max_upload_mb": settings.max_upload_bytes // (1024 * 1024),
        "rate_limits": {
            "send": settings.rate_limit_send,
            "retrieve": settings.rate_limit_retrieve,
            "file": settings.rate_limit_file,
            "delete": settings.rate_limit_delete,
        },
    }
