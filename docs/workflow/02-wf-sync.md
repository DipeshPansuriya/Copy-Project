# 02-wf-sync.md

# Workflow: Sync

## 1. Overview

OpenClipboard v1 is a single-instance application with no distributed state synchronization. All data lives in a single SQLite database and local/MinIO storage.

## 2. Current Sync Model

| Component | Sync Mechanism | Scope |
|-----------|---------------|-------|
| SQLite DB | Single file, local WAL mode | Single instance |
| Local blobs | Local filesystem | Single instance |
| MinIO | S3-compatible, eventually consistent | Shared bucket (if used) |
| Rate limiter | In-memory (`slowapi`) | Per-process only |

## 3. Data Flow (Single Instance)

```
┌─────────────────────────────────────────────────────────────┐
│                     SINGLE INSTANCE                          │
│                                                               │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │   API Server │    │   SQLite DB  │    │   Storage    │   │
│  │  (uvicorn)   │    │   (WAL mode) │    │  (local/minio│   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘   │
│         │                   │                   │           │
│         │ writes            │ stores            │ stores    │
│         │ metadata          │ rows              │ blobs     │
│         └───────────────────┴───────────────────┘           │
│                                                               │
│  All reads/writes go through this single instance             │
└─────────────────────────────────────────────────────────────┘
```

## 4. Sync Limitations (v1)

| Limitation | Impact | Mitigation |
|------------|--------|------------|
| No multi-instance | Cannot scale horizontally | Single-node self-hosting |
| In-memory rate limiter | Rate limits reset per restart | Acceptable for v1 |
| No replication | Single point of failure | Regular backups |
| No pub/sub | No real-time sync across nodes | Not needed for single instance |

## 5. Future Sync Architecture (v2)

If horizontal scaling is needed:

```
┌─────────────────────────────────────────────────────────────┐
│                    LOAD BALANCER                              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│  Instance 1 │       │  Instance 2 │       │  Instance N │
│  (uvicorn)  │       │  (uvicorn)  │       │  (uvicorn)  │
└──────┬──────┘       └──────┬──────┘       └──────┬──────┘
       │                     │                     │
       └─────────────────────┼─────────────────────┘
                             │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   PostgreSQL│       │    Redis    │       │    MinIO    │
│  (shared DB)│       │  (rate limit│       │ (blob store)│
│             │       │   + cache)  │       │             │
└─────────────┘       └─────────────┘       └─────────────┘
```

### New Components for Sync

| Component | Purpose |
|-----------|---------|
| **PostgreSQL** | Shared metadata across instances |
| **Redis** | Distributed rate limiting + cache |
| **MinIO** | Shared blob storage (required for multi-node) |
| **Load Balancer** | Distribute traffic across instances |

## 6. Sync Conventions

- Single writer to metadata DB (PostgreSQL handles concurrency)
- Rate limiter backed by Redis (not in-memory)
- Blob storage via MinIO (shared S3-compatible)
- Health checks for load balancer rotation
