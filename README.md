# OpenClipboard

Open-source, self-hosted cross-device clipboard — a drop-in replacement for
[Online Clipboard](https://online-clipboard.online/online-clipboard/) with
enhancements: **file uploads**, **configurable expiry**, **one-shot burn-after-read**,
**in-app delete**, **image preview**, and **paste-from-clipboard** support.

Everything here is open source — no proprietary SaaS, no sign-up, no tracking.

## What it does

1. **Send**: paste text, drop an image, or upload a file → get a 6-digit code.
2. **Retrieve**: enter the code on any other device → view/download the content.
3. **Expire**: content is permanently deleted after its time-to-live (default 15 min,
   adjustable from 30 s to 24 h). One-shot entries delete after the first download.

## Stack (100% open source)

| Layer | Technology | License |
|-------|-----------|---------|
| Backend API | [FastAPI](https://fastapi.tiangolo.com/) | MIT |
| Web server | [Uvicorn](https://www.uvicorn.org/) | BSD |
| Metadata DB | [SQLite](https://www.sqlite.org/) (via aiosqlite) | Public domain |
| Object storage | [MinIO](https://min.io/) (S3-compatible) or local disk | Apache-2.0 / AGPLv3 |
| Frontend | Vanilla HTML/CSS/JS (no build step) | MIT |
| Container | Docker / Docker Compose | Apache-2.0 |

## Quick start

### Option A — Docker Compose (recommended)

```bash
git clone <this-repo>
cd <this-repo>

# local-disk storage (no extra services)
docker compose up --build

# then open http://localhost:8000
```

With **MinIO** (uncomment the MinIO block in `docker-compose.yml` and set `CLIP_STORAGE: minio`):

```bash
docker compose up --build
# MinIO console: http://localhost:9001  (minioadmin / minioadmin)
```

### Option B — plain Python (dev)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# local storage (default)
uvicorn app.main:app --reload --port 8000

# open http://localhost:8000
```

Configure via environment variables (see `.env.example`).

## Key features

| Feature | How |
|---------|-----|
| **Text** | Paste or type, click Send |
| **Image** | Drop an image or paste from clipboard |
| **File** | Any file up to `CLIP_MAX_UPLOAD_MB` (default 50 MB) |
| **Expiry** | 30 s … 24 h; background purge worker sweeps every 30 s |
| **One-shot** | Delete after first download (burn after read) |
| **Manual delete** | "Delete now" button removes content immediately |
| **No account** | The 6-digit code is the only capability needed |

## File retention

- Metadata lives in SQLite (`data/clipboard.db`).
- Blobs live in object storage (MinIO bucket `clipboard` or `data/blobs/` on disk).
- A background loop deletes every expired row + its blob. Expired codes can be reused.
- One-shot entries are deleted right after the first successful download.

## Project layout

```
backend/
  app/
    main.py        # FastAPI app, static-file serving, lifespan
    config.py      # env-driven settings
    db.py          # SQLite metadata store
    storage.py     # LocalStorage + MinioStorage backends
    purge.py       # background expiry sweeper
    api/items.py   # /api/send, /api/retrieve/{code}, /api/file/{code}, ...
    schemas.py     # Pydantic models
    deps.py        # app singletons
  static/
    index.html     # single-page UI
    style.css
    app.js
  Dockerfile
  requirements.txt  # all open-source deps
docker-compose.yml  # app + optional MinIO
.env.example
```

## Security notes

- The 6-digit code is the capability: anyone with it can retrieve/delete the content.
- Content is stored at rest; enable HTTPS/TLS (reverse proxy) for production.
- One-shot + short TTL is recommended for sensitive snippets.

## License

MIT — use, modify, and self-host freely.
