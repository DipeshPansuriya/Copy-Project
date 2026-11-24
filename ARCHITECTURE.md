# Architecture

## 1. System Context

```
┌─────────────────────────────────────────────────────────────┐
│                     EXTERNAL USERS                          │
│  (Sender Device)                    (Receiver Device)       │
│  ┌─────────────┐                   ┌─────────────┐         │
│  │  Web Browser│                   │  Web Browser│         │
│  │  (send UI)  │                   │  (retrieve  │         │
│  └──────┬──────┘                   │   UI)       │         │
│         │                          └──────┬──────┘         │
│         │ 6-digit code                   │ 6-digit code     │
│         └────────────────────────────────┘                │
│                           Internet / LAN                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                 OPENCLIPBOARD APP (FastAPI)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐   │
│  │  API Layer   │  │  Purge       │  │  Static File   │   │
│  │  (send/get/  │  │  Worker      │  │  Serving       │   │
│  │   delete)    │  │  (expiry)    │  │  (UI assets)   │   │
│  └──────┬───────┘  └──────┬───────┘  └───────┬────────┘   │
│         │                 │                  │              │
│         └─────────────────┴──────────────────┘              │
│                           │                                  │
│         ┌─────────────────┼─────────────────┐               │
│         ▼                 ▼                 ▼               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   SQLite     │  │   Local Disk │  │   MinIO      │   │
│  │   (metadata) │  │   (blobs)    │  │   (blobs,    │   │
│  │              │  │   (default)  │  │    optional) │   │
│  └──────────────┘  └──────────────┘  └──────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## 2. Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        FASTAPI APPLICATION                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌───────────────────────┐   │
│  │  Router     │  │  Middleware │  │  Lifespan (startup/   │   │
│  │  /api/*     │  │  (CORS,     │  │   shutdown, purge)    │   │
│  │             │  │  TrustedHost,│  │                       │   │
│  │  send/      │  │  Security   │  └───────────────────────┘   │
│  │  retrieve/  │  │  Headers,   │  ┌───────────────────────┐   │
│  │  file/      │  │  RateLimit) │  │  Purge Worker         │   │
│  │  delete/    │  │             │  │  (async loop, 30s)    │   │
│  │  stats/     │  └─────────────┘  └───────────────────────┘   │
│  │  health     │                                               │
│  └──────┬──────┘                                               │
│         │                                                      │
│  ┌──────▼──────┐      ┌──────────────────────────────────┐    │
│  │   Deps      │──────▶│  SQLite (aiosqlite)              │    │
│  │   (singleton│      │  - items table                     │    │
│  │   DB,       │      │  - code, kind, size, object_key    │    │
│  │   Storage,  │      │  - created_at, expires_at, ttl     │    │
│  │   Limiter)  │      │  - one_shot, retrieved_at          │    │
│  └──────┬──────┘      └──────────────────────────────────┘    │
│         │                                                      │
│         │                          ┌─────────────────┐        │
│         └─────────────────────────▶│  Storage        │        │
│                                    │  (Local or MinIO)│        │
│                                    │  - put/get/stream │        │
│                                    │  - delete         │        │
│                                    └─────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Data Flow

### Send Flow
1. Client POSTs `multipart/form-data` to `/api/send`
2. Rate limit checked (20/min per IP)
3. File type verified via `python-magic` (executables rejected)
4. 6-digit code generated via `secrets.randbelow`
5. Blob written to storage (UUID key, not user filename)
6. Metadata row inserted into SQLite (TTL = now + ttl)
7. Code returned to client

### Retrieve Flow
1. Client GETs `/api/retrieve/{code}`
2. Code format validated (`^\d{6}$`)
3. Row looked up in SQLite
4. Expired or consumed one-shot rows are lazily purged (410)
5. Metadata + (optional) text body returned

### Download Flow
1. Client GETs `/api/file/{code}`
6. Blob streamed from storage
7. Download counter incremented
8. If one-shot: blob + metadata deleted after stream completes

### Purge Flow
1. Background async loop wakes every `CLIP_PURGE_INTERVAL` seconds
2. Queries SQLite for rows where `expires_at < now` OR (`one_shot` AND `retrieved_at IS NOT NULL`)
3. Deletes blob from storage, then deletes SQLite row

## 4. Deployment Topology

```
┌─────────────────────────────────────────────────────────────┐
│                     REVERSE PROXY (optional)                  │
│              (Caddy / Nginx / Traefik)                        │
│  TLS termination • Rate limiting • WAF • Body size limits     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    DOCKER CONTAINER                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  uvicorn app.main:app --host 0.0.0.0 --port 8000  │    │
│  │                                                     │    │
│  │  Volume: /data  (SQLite DB + local blobs)           │    │
│  │  Env: CLIP_STORAGE=local\|minio                     │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 5. Design Decisions

| Decision | Rationale |
|----------|-----------|
| SQLite (not PostgreSQL) | Zero-config, single file, sufficient for single-instance self-hosting |
| Local disk default (MinIO optional) | Works without Docker Compose services; MinIO for production scale |
| 6-digit numeric code | Easy to type on mobile; 1M space with rate limiting is secure enough for v1 |
| Capability-based access (no auth) | Simplest UX; no accounts to manage |
| Lazy purge on retrieve + background sweep | Ensures expired codes can be reclaimed even if sweep missed them |
| Magic-byte file verification | Prevents extension spoofing and executable uploads |
