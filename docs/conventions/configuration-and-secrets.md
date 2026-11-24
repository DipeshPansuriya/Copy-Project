# Configuration and Secrets

## 1. Configuration Sources

Configuration is loaded from **environment variables** only. There are no config files (YAML/TOML/INI) in v1.

```
Environment Variable → Settings class (backend/app/config.py) → Application
```

## 2. Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `OpenClipboard` | Application display name |
| `CLIP_STORAGE` | `local` | `local` or `minio` |
| `CLIP_DATA_DIR` | `<backend>/data` | Directory for SQLite DB and local blobs |
| `CLIP_MAX_UPLOAD_MB` | `50` | Max upload size in megabytes |
| `CLIP_MIN_TTL` | `30` | Minimum TTL in seconds |
| `CLIP_DEFAULT_TTL` | `900` | Default TTL in seconds (15 min) |
| `CLIP_MAX_TTL` | `86400` | Maximum TTL in seconds (24h) |
| `CLIP_PURGE_INTERVAL` | `30` | Purge worker interval in seconds |
| `CLIP_ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | TrustedHostMiddleware allowlist |
| `CLIP_CORS_ORIGINS` | `*` | CORS allowed origins |
| `CLIP_RATE_LIMIT_SEND` | `20/minute` | Rate limit for `/api/send` |
| `CLIP_RATE_LIMIT_RETRIEVE` | `30/minute` | Rate limit for `/api/retrieve` |
| `CLIP_RATE_LIMIT_FILE` | `30/minute` | Rate limit for `/api/file` |
| `CLIP_RATE_LIMIT_DELETE` | `10/minute` | Rate limit for `/api/item` DELETE |
| `MINIO_ENDPOINT` | `localhost:9000` | MinIO host:port |
| `MINIO_ACCESS_KEY` | `minioadmin` | MinIO access key |
| `MINIO_SECRET_KEY` | `minioadmin` | MinIO secret key |
| `MINIO_BUCKET` | `clipboard` | MinIO bucket name |
| `MINIO_SECURE` | `false` | Use HTTPS for MinIO |

## 3. `.env.example`

Copy `.env.example` to `.env` and edit for your deployment:

```bash
cp .env.example .env
# Edit .env with your values
```

## 4. Docker Compose Environment

Values in `docker-compose.yml` override `.env` for containerized deployment.

## 5. Secrets Handling

- **No secrets in code** — all sensitive values come from env vars
- **No `.env` in git** — `.env` should be gitignored
- **`.env.example` is safe to commit** — contains only defaults and placeholders
- **MinIO credentials** — change `minioadmin` defaults in production
- **Future: Secret manager** — integrate with HashiCorp Vault, AWS Secrets Manager, or Docker secrets when needed

## 6. Validation

Settings are validated at import time:
- TTL values must be integers
- `CLIP_STORAGE` must be `local` or `minio`
- Boolean env vars use `_env_bool()` helper

Invalid values cause the app to fail fast on startup.
