# 04-arch-deployment-topology.md

# Deployment Topology

## 1. Development (Local)

```
┌─────────────────────────────────────────────────┐
│              DEVELOPER MACHINE                   │
│                                                 │
│  ┌──────────────┐    ┌──────────────┐           │
│  │  Web Browser │    │   Terminal   │           │
│  │  (localhost) │    │   (curl)     │           │
│  └──────┬───────┘    └──────┬───────┘           │
│         │                   │                   │
│         └───────────────────┴───────────────────┘
│                         │
│                         ▼
│              ┌──────────────────┐
│              │  OpenClipboard   │
│              │  (uvicorn:8000)  │
│              │                  │
│              │  SQLite DB       │  data/clipboard.db
│              │  Local blobs     │  data/blobs/
│              └──────────────────┘
└─────────────────────────────────────────────────┘
```

## 2. Production (Single Instance)

```
┌─────────────────────────────────────────────────────────────┐
│                     INTERNET                                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              REVERSE PROXY (Caddy / Nginx / Traefik)         │
│  • TLS termination (HTTPS)                                   │
│  • Edge rate limiting                                        │
│  • WAF rules                                                 │
│  • Client max body size                                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼ (HTTP, 127.0.0.1:8000)
┌─────────────────────────────────────────────────────────────┐
│                 DOCKER HOST / VM                              │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Container: openclipboard-app                       │   │
│  │  ├── uvicorn app.main:app --host 0.0.0.0 --port 8000│   │
│  │  ├── CLIP_STORAGE=local \| minio                    │   │
│  │  └── Volume: clip-data → /data                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  (Optional) Container: openclipboard-minio          │   │
│  │  ├── S3-compatible object storage                   │   │
│  │  └── Volume: clip-minio → /data                     │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 3. Network Topology

| Layer | Port | Protocol | Access |
|-------|------|----------|--------|
| External HTTPS | 443 | HTTPS | Public |
| Reverse Proxy → App | 8000 | HTTP | Internal only |
| MinIO API | 9000 | HTTP | Internal only |
| MinIO Console | 9001 | HTTP | Internal/admin only |

## 4. Volume Mounts

| Volume | Container Path | Host Path | Persistence |
|--------|---------------|-----------|-------------|
| `clip-data` | `/data` | Docker volume | Yes |
| `clip-minio` | `/data` | Docker volume | Yes |

## 5. Environment Variables (Production)

| Variable | Production Value |
|----------|-----------------|
| `CLIP_STORAGE` | `minio` (recommended for scale) |
| `CLIP_ALLOWED_HOSTS` | `clipboard.yourdomain.com` |
| `CLIP_CORS_ORIGINS` | `https://clipboard.yourdomain.com` |
| `CLIP_MAX_UPLOAD_MB` | `50` |
| `CLIP_DEFAULT_TTL` | `900` |
| `MINIO_ROOT_USER` | `change-in-production` |
| `MINIO_ROOT_PASSWORD` | `change-in-production` |

## 6. Scaling Considerations

| Component | Limitation | Solution |
|-----------|------------|----------|
| SQLite | Single writer | Single instance; no horizontal scaling |
| Local disk | Not shared | Use MinIO for multi-node |
| Rate limiter | In-memory | Per-instance; add Redis for distributed |
| Purge worker | Single task | One instance runs the worker |

## 7. High Availability (Future)

- Run multiple app instances behind a load balancer
- Use MinIO for shared blob storage
- Use PostgreSQL instead of SQLite for shared metadata
- Use Redis for distributed rate limiting
