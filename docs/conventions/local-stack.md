# Local Stack

## 1. Prerequisites

- Python 3.13+
- Docker & Docker Compose (optional)

## 2. Python Local Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open: `http://127.0.0.1:8000`

## 3. Docker Local Setup

```bash
cd /path/to/project
docker compose up --build
```

Open: `http://localhost:8000`

## 4. Environment

Copy `.env.example` to `.env` for local overrides:

```bash
cp .env.example .env
# Edit CLIP_STORAGE, TTLs, rate limits as needed
```

## 5. Verification

```bash
# Health
curl http://localhost:8000/health

# Send text
curl -X POST http://localhost:8000/api/send -F kind=text -F text="hello"

# Retrieve
curl http://localhost:8000/api/retrieve/<CODE>
```

## 6. Stopping

```bash
# Docker
docker compose down

# Local Python
pkill -f "uvicorn app.main:app"
```

## 7. Data Persistence

| Component | Location | Persists Across Restarts |
|-----------|----------|-------------------------|
| SQLite DB | `backend/data/clipboard.db` | Yes |
| Local blobs | `backend/data/blobs/` | Yes |
| Docker volume | `clip-data` | Yes (unless `docker compose down -v`) |

## 8. Ports

| Service | Port | Description |
|---------|------|-------------|
| OpenClipboard | 8000 | Main app |
| MinIO API | 9000 | Optional object storage |
| MinIO Console | 9001 | Optional web UI |

## 9. Troubleshooting Local

- Port 8000 in use: change `docker-compose.yml` mapping or use `--port 8099`
- Permission denied on `data/`: `chmod -R 777 backend/data/`
- MinIO not needed: default `CLIP_STORAGE=local` works without it
