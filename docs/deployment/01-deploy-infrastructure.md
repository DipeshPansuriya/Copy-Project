# 01-deploy-infrastructure.md

# Infrastructure Deployment

## 1. Supported Platforms

| Platform | Method | Notes |
|----------|--------|-------|
| Docker Compose | `docker compose up` | Recommended for single-node |
| Docker | `docker run` | Single container |
| Bare Metal | Python + uvicorn | Development or simple prod |
| Kubernetes | (Future) | Helm chart not yet available |

## 2. Docker Compose (Production)

```yaml
services:
  app:
    build: ./backend
    container_name: openclipboard-app
    ports:
      - "127.0.0.1:8000:8000"  # Bind to localhost only behind reverse proxy
    volumes:
      - clip-data:/data
    environment:
      CLIP_STORAGE: minio
      CLIP_ALLOWED_HOSTS: clipboard.yourdomain.com
      CLIP_CORS_ORIGINS: https://clipboard.yourdomain.com
      CLIP_MAX_UPLOAD_MB: "50"
      CLIP_DEFAULT_TTL: "900"
      CLIP_MIN_TTL: "30"
      CLIP_MAX_TTL: "86400"
      CLIP_PURGE_INTERVAL: "30"
      CLIP_RATE_LIMIT_SEND: "20/minute"
      CLIP_RATE_LIMIT_RETRIEVE: "30/minute"
      CLIP_RATE_LIMIT_FILE: "30/minute"
      CLIP_RATE_LIMIT_DELETE: "10/minute"
      MINIO_ENDPOINT: minio:9000
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
      MINIO_BUCKET: clipboard
      MINIO_SECURE: "false"
    depends_on:
      minio:
        condition: service_healthy
    restart: unless-stopped

  minio:
    image: minio/minio:latest
    container_name: openclipboard-minio
    ports:
      - "127.0.0.1:9000:9000"
      - "127.0.0.1:9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ROOT_USER}
      MINIO_ROOT_PASSWORD: ${MINIO_ROOT_PASSWORD}
    volumes:
      - clip-minio:/data
    command: server /data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    restart: unless-stopped

volumes:
  clip-data:
  clip-minio:
```

## 3. Reverse Proxy (Caddy Example)

```caddyfile
clipboard.yourdomain.com {
    encode gzip zstd
    
    reverse_proxy localhost:8000 {
        header_up Host {upstream_hostport}
        header_up X-Real-IP {remote}
        header_up X-Forwarded-Proto {scheme}
    }
    
    # Security headers for all responses
    header {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "no-referrer"
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
    }
}
```

## 4. Resource Requirements

| Component | CPU | Memory | Disk |
|-----------|-----|--------|------|
| OpenClipboard app | 0.25–1 vCPU | 256–512 MB | Minimal (code only) |
| SQLite DB | — | — | Scales with active items |
| Local blobs | — | — | Scales with uploads |
| MinIO | 0.5–2 vCPU | 512 MB–2 GB | Scales with uploads |

## 5. Backup Strategy

| Data | Backup Method | Frequency |
|------|--------------|-----------|
| SQLite DB | Copy `data/clipboard.db` | Daily |
| Local blobs | Copy `data/blobs/` | Daily |
| MinIO | `mc mirror` or MinIO backup | Daily |
| Config | `.env` and `docker-compose.yml` | Version control |

> ⚠️ Content is ephemeral by design. Backups are for disaster recovery, not content archival.

## 6. Monitoring

| Check | Method | Endpoint |
|-------|--------|----------|
| Health | HTTP GET | `/health` |
| Uptime | Ping | Port 8000 |
| Disk usage | `df -h` | Host or volume |
| Active items | HTTP GET | `/api/stats` |

## 7. Logs

| Source | Location | Rotation |
|--------|----------|----------|
| App stdout/stderr | Docker logs | Docker log rotation |
| Access logs | Uvicorn access log | Configure in reverse proxy |
| Purge logs | App logs | Included in app logs |
