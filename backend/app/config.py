"""Runtime configuration. Everything is configurable via environment variables."""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # backend/


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    """App settings, resolved once at import time."""

    app_name: str = "OpenClipboard"

    # Where the SQLite metadata DB and (for the local backend) blobs live.
    data_dir: Path = Path(os.getenv("CLIP_DATA_DIR", str(BASE_DIR / "data")))

    # Storage backend: "minio" (open-source S3 object storage) or "local" disk.
    storage_backend: str = os.getenv("CLIP_STORAGE", "local").lower()

    # MinIO / S3-compatible object storage.
    minio_endpoint: str = os.getenv("MINIO_ENDPOINT", "localhost:9000")
    minio_access_key: str = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
    minio_secret_key: str = os.getenv("MINIO_SECRET_KEY", "minioadmin")
    minio_bucket: str = os.getenv("MINIO_BUCKET", "clipboard")
    minio_secure: bool = _env_bool("MINIO_SECURE", False)

    # Upload limits.
    max_upload_bytes: int = int(os.getenv("CLIP_MAX_UPLOAD_MB", "50")) * 1024 * 1024

    # Retention: content is hard-deleted after the chosen TTL.
    min_ttl: int = int(os.getenv("CLIP_MIN_TTL", "30"))
    default_ttl: int = int(os.getenv("CLIP_DEFAULT_TTL", "900"))
    max_ttl: int = int(os.getenv("CLIP_MAX_TTL", str(24 * 3600)))

    # How often the purge worker sweeps expired content (seconds).
    purge_interval: float = float(os.getenv("CLIP_PURGE_INTERVAL", "30"))

    # --- Security settings -------------------------------------------------

    # Allowed hosts (Host header validation). Comma-separated. Default allows
    # localhost/127.0.0.1 for development; set your domain(s) in production.
    allowed_hosts: str = os.getenv("CLIP_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0")

    # Allowed CORS origins. Comma-separated. Default "*" (dev); restrict in prod.
    cors_origins: str = os.getenv("CLIP_CORS_ORIGINS", "*")

    # Rate limits (slowapi format, e.g. "10/minute").
    rate_limit_send: str = os.getenv("CLIP_RATE_LIMIT_SEND", "20/minute")
    rate_limit_retrieve: str = os.getenv("CLIP_RATE_LIMIT_RETRIEVE", "30/minute")
    rate_limit_file: str = os.getenv("CLIP_RATE_LIMIT_FILE", "30/minute")
    rate_limit_delete: str = os.getenv("CLIP_RATE_LIMIT_DELETE", "10/minute")

    # Lockout settings for brute-force protection
    max_failed_attempts: int = int(os.getenv("CLIP_MAX_FAILED_ATTEMPTS", "5"))
    lockout_seconds: int = int(os.getenv("CLIP_LOCKOUT_SECONDS", "300"))  # 5 minutes

    # Password protection
    password_protection_enabled: bool = _env_bool("CLIP_PASSWORD_PROTECTION", True)

    # --- Admin / monitoring settings ----------------------------------------

    admin_enabled: bool = _env_bool("CLIP_ADMIN_ENABLED", True)
    admin_username: str = os.getenv("CLIP_ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("CLIP_ADMIN_PASSWORD", "admin")  # ⚠️ change in production!

    # --- Database settings --------------------------------------------------

    # Database backend: "sqlite" (default, single-instance) or "postgres" (multi-instance)
    db_backend: str = os.getenv("CLIP_DB_BACKEND", "sqlite")

    # PostgreSQL connection (used when db_backend=postgres)
    pg_host: str = os.getenv("PG_HOST", "localhost")
    pg_port: int = int(os.getenv("PG_PORT", "5432"))
    pg_user: str = os.getenv("PG_USER", "openclipboard")
    pg_password: str = os.getenv("PG_PASSWORD", "openclipboard")
    pg_database: str = os.getenv("PG_DATABASE", "openclipboard")

    @property
    def pg_dsn(self) -> str:
        return f"postgresql://{self.pg_user}:{self.pg_password}@{self.pg_host}:{self.pg_port}/{self.pg_database}"


settings = Settings()
