# OpenClipboard

Open-source, self-hosted cross-device clipboard — a drop-in replacement for
[Online Clipboard](https://online-clipboard.online/online-clipboard/) with
enhancements: **file uploads**, **configurable expiry**, **one-shot burn-after-read**,
**in-app delete**, **image preview**, and **paste-from-clipboard** support.

Everything here is open source — no proprietary SaaS, no sign-up, no tracking.

## 🔒 Security & Governance

This repository follows the same branch protection, push policy, and security
hardening as
[DipeshPansuriya/MLX_Model_App](https://github.com/DipeshPansuriya/MLX_Model_App).

| Document | Description |
|----------|-------------|
| [SECURITY.md](./SECURITY.md) | Security policy, threat model, vulnerability reporting |
| [docs/GITHUB-POLICY.md](./docs/GITHUB-POLICY.md) | Repository governance and settings |
| [docs/BRANCH-POLICY.md](./docs/BRANCH-POLICY.md) | Branch protection rules for `main` |
| [docs/PUSH-POLICY.md](./docs/PUSH-POLICY.md) | Push restrictions and pre-push checks |
| [docs/REPO-HARDENING-CHECKLIST.md](./docs/REPO-HARDENING-CHECKLIST.md) | Full hardening checklist |
| [docs/SECURITY-AUDIT.md](./docs/SECURITY-AUDIT.md) | Security audit procedure and 21 checks |
| [CONTRIBUTING.md](./CONTRIBUTING.md) | How to contribute |
| [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) | Community code of conduct |

### Branch Protection (`main`)

- Pull requests required before merging
- 1 approving review required (from CODEOWNER)
- Status checks must pass (security scan, quality checks, Docker build)
- Direct pushes to `main` are blocked — for all users including administrators
- Signed commits required
- Linear history required

### Pre-Commit / Pre-Push Hooks

Local Git hooks enforce security on every commit and push:

```bash
./scripts/install_hooks.sh
```

- **pre-commit**: secret scan, `.env` exclusion, quick security audit
- **pre-push**: secret scan, branch check, full security audit

See [scripts/](./scripts/) for the hook implementations.

## What it does

1. **Send**: paste text, drop an image, or upload a file → get a 12-character code.
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
| **No account** | The 12-character code is the only capability needed |

## File retention

- Metadata lives in SQLite (`data/clipboard.db`).
- Blobs live in object storage (MinIO bucket `clipboard` or `data/blobs/` on disk).
- A background loop deletes every expired row + its blob. Expired codes can be reused.
- One-shot entries are deleted right after the first successful download.

## Project layout

```
backend/
  app/
    main.py        # FastAPI app, security middleware, static serving, lifespan
    config.py      # env-driven settings
    db.py          # SQLite metadata store
    db_postgres.py # PostgreSQL metadata store (same interface)
    cache.py       # Redis + in-memory cache
    storage.py     # LocalStorage + MinioStorage backends
    filetype.py    # magic-byte MIME detection (libmagic + pure-Python fallback)
    purge.py       # background expiry sweeper
    api/items.py   # /api/send, /api/retrieve/{code}, /api/file/{code}, ...
    api/admin.py   # /admin/login, /admin/health, /admin/entries, ...
    schemas.py     # Pydantic models
    deps.py        # app singletons
  static/
    index.html     # single-page UI
    style.css
    app.js
  tests/           # pytest suite (API, security, storage, rate limiting)
  Dockerfile
  requirements.txt # all open-source deps
  pytest.ini
scripts/
  check_secrets.py     # 19-rule secret scanner
  security_audit.sh    # 21-point security audit
  install_hooks.sh     # installs .githooks into git config
.githooks/
  pre-commit           # secret scan + .env guard + quick audit
  pre-push             # full secret scan + branch guard + full audit
.github/
  workflows/           # security.yml, quality.yml, pr-review.yml
  CODEOWNERS
  dependabot.yml
  ISSUE_TEMPLATE/
docker-compose.yml      # app + optional MinIO
docker-compose.prod.yml # production compose
.env.example
```

## Testing

The project ships an automated `pytest` suite covering the API, security
controls, storage backends, and rate limiting.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt pytest pytest-asyncio httpx

pytest tests/ -v
```

| Test file | Coverage |
|-----------|----------|
| `tests/test_api.py` | send, retrieve, item info, download, delete, stats, health, security headers |
| `tests/test_security.py` | executable rejection, SQL injection, path traversal, XSS, lockout, empty content |
| `tests/test_storage.py` | local storage put/get/stat/delete and streaming |
| `tests/test_rate_limit.py` | slowapi 429 behaviour and configured limits |

Run the security tooling as well:

```bash
./scripts/security_audit.sh --full
python3 scripts/check_secrets.py --push
```

## Security notes

- The 12-character code is the capability: anyone with it can retrieve/delete the content.
- Content is stored at rest; enable HTTPS/TLS (reverse proxy) for production.
- One-shot + short TTL is recommended for sensitive snippets.
- Optional per-clip password protection (bcrypt) with brute-force lockout.

## License

MIT — use, modify, and self-host freely.
