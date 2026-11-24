# 02-arch-component.md

# Component Architecture

## 1. Component Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         OPENCLIPBOARD APPLICATION                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────┐                                                    │
│  │   Static Files  │                                                    │
│  │  (index.html,   │                                                    │
│  │   style.css,    │                                                    │
│  │   app.js)       │                                                    │
│  └─────────┬───────┘                                                    │
│           │                                                            │
│  ┌────────▼─────────┐    ┌──────────────────────────────────────┐     │
│  │   API Router     │───▶│           Endpoints                    │     │
│  │   (/api/*)       │    │  POST /send                            │     │
│  │                  │    │  GET  /retrieve/{code}                 │     │
│  │                  │    │  GET  /item/{code}                     │     │
│  │                  │    │  GET  /file/{code}                     │     │
│  │                  │    │  DELETE /item/{code}                   │     │
│  │                  │    │  GET  /stats                           │     │
│  │                  │    │  GET  /health                          │     │
│  └─────────┬────────┘    └──────────────────────────────────────┘     │
│           │                                                            │
│  ┌────────▼─────────┐    ┌──────────────────────────────────────┐     │
│  │   Middleware     │    │  TrustedHost                           │     │
│  │   Stack          │    │  CORS                                  │     │
│  │                  │    │  Security Headers                      │     │
│  │                  │    │  Rate Limiting (slowapi)               │     │
│  └─────────┬────────┘    └──────────────────────────────────────┘     │
│           │                                                            │
│  ┌────────▼─────────┐    ┌──────────────────────────────────────┐     │
│  │   Deps (Singleton│    │  Database (SQLite)                     │     │
│  │   Container)     │    │  Storage (Local/MinIO)                 │     │
│  │                  │    │  Rate Limiter                          │     │
│  └─────────┬────────┘    └──────────────────────────────────────┘     │
│           │                                                            │
│  ┌────────▼─────────┐                                                    │
│  │   Lifespan       │                                                    │
│  │   (startup/      │                                                    │
│  │   shutdown)      │                                                    │
│  └─────────┬────────┘                                                    │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────────────────────────────────────────────────┐      │
│  │   Background Purge Worker (asyncio.Task, runs every 30s)     │      │
│  └──────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
    ┌─────────────────┐             ┌─────────────────┐
    │   SQLite DB     │             │   Storage       │
    │   (metadata)    │             │   (blobs)       │
    │                 │             │                 │
    │ • items table   │             │ • Local Disk    │
    │ • code PK       │             │   (default)     │
    │ • TTL/expiry    │             │ • MinIO         │
    │                 │             │   (optional)    │
    └─────────────────┘             └─────────────────┘
```

## 2. Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Static Files** | Serve HTML/CSS/JS frontend |
| **API Router** | Route HTTP requests to endpoint handlers |
| **Endpoints** | Business logic: send, retrieve, download, delete, stats |
| **Middleware** | Security: CORS, trusted host, headers, rate limiting |
| **Deps** | Singleton container for DB, storage, limiter |
| **Database** | SQLite metadata: item rows, TTL, purge queries |
| **Storage** | Blob abstraction: put/get/stream/delete |
| **Lifespan** | App startup/shutdown: connect DB, ensure bucket, start purge |
| **Purge Worker** | Background loop: delete expired items and blobs |

## 3. Interface Contracts

### Storage Interface

```python
class Storage:
    async def put(key: str, data: bytes, content_type: str) -> None
    async def get(key: str) -> Optional[bytes]
    async def stat(key: str) -> Optional[tuple[int, str]]
    async def delete(key: str) -> None
    async def stream(key: str) -> Optional[tuple[AsyncIterator[bytes], int, str]]
```

### Implementations

- `LocalStorage` — files under `data/blobs/`
- `MinioStorage` — objects in MinIO bucket

### Database Interface

| Method | Description |
|--------|-------------|
| `create_item(...)` | Insert new metadata row |
| `get_item(code)` | Look up row by code |
| `increment_download(code)` | Bump download counter |
| `mark_retrieved(code)` | Set retrieved_at timestamp |
| `delete_item(code)` | Remove metadata row |
| `expired_items(now)` | Query rows past TTL or consumed one-shots |
| `stats()` | Count active items and total bytes |

## 4. Concurrency Model

- **Async/await** throughout
- **Single `asyncio.Task`** for purge worker
- **SQLite WAL mode** for concurrent reads
- **Single writer** to SQLite (acceptable for v1 self-hosting)
