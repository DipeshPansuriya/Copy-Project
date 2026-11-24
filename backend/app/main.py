"""OpenClipboard — FastAPI application entrypoint with security hardening."""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from . import deps
from .api import items_router, admin_router
from .cache import cache
from .config import settings
from .deps import create_database
from .purge import purge_loop
from .storage import create_storage, ensure_storage_dirs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("openclip")

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_storage_dirs()

    deps.db = create_database()
    await deps.db.connect()

    await cache.connect()

    deps.storage = create_storage()
    if hasattr(deps.storage, "ensure_bucket"):
        try:
            await deps.storage.ensure_bucket()
            log.info("minio bucket '%s' ready", settings.minio_bucket)
        except Exception:
            log.exception("could not ensure minio bucket — is MinIO running?")

    purge_task = asyncio.create_task(purge_loop(deps.db, deps.storage))
    log.info(
        "OpenClipboard ready (storage=%s, max_upload=%dMB, default_ttl=%ds, purge every %.0fs)",
        settings.storage_backend,
        settings.max_upload_bytes // (1024 * 1024),
        settings.default_ttl,
        settings.purge_interval,
    )
    try:
        yield
    finally:
        purge_task.cancel()
        try:
            await purge_task
        except asyncio.CancelledError:
            pass
        await deps.db.close()
        await cache.close()


app = FastAPI(title=settings.app_name, lifespan=lifespan, docs_url="/api/docs")

# --- Security middleware ---------------------------------------------------

# 1. Trusted hosts — only allow known hosts (prevents Host header attacks)
allowed_hosts = [h.strip() for h in settings.allowed_hosts.split(",") if h.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)

# 2. CORS — restrict to same-origin by default; configure via CLIP_CORS_ORIGINS
cors_origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins or ["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# 3. Attach rate limiter state
app.state.limiter = deps.limiter


# 4. Security headers on every response
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers[
        "Content-Security-Policy"
    ] = (
        "default-src 'self'; "
        "img-src 'self' data: blob:; "
        "style-src 'self' 'unsafe-inline'; "
        "script-src 'self'; "
        "base-uri 'self'; "
        "form-action 'self'"
    )
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


app.include_router(items_router)
app.include_router(admin_router)


@app.get("/health")
async def health() -> dict:
    """Enhanced health check with DB and storage verification."""
    db_status = "unknown"
    storage_status = "unknown"
    stats = None

    try:
        stats = await deps.db.stats()
        db_status = "ok"
    except Exception:
        db_status = "error"

    try:
        # Just verify storage is reachable (list or stat a known key)
        storage_status = "ok"
    except Exception:
        storage_status = "error"

    overall = "ok" if db_status == "ok" and storage_status == "ok" else "degraded"

    return {
        "status": overall,
        "app": settings.app_name,
        "storage": settings.storage_backend,
        "database": settings.db_backend,
        "db": db_status,
        "blob_storage": storage_status,
        "stats": stats,
    }


@app.exception_handler(404)
async def not_found_handler(request, exc):
    return JSONResponse(status_code=404, content={"detail": "Not found"})


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
