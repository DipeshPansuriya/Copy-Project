# Setup and Initialisation

## 1. First-Time Setup

### Option A: Docker (Recommended)

```bash
# 1. Clone or navigate to project
cd "/Users/dipesh/Desktop/Dipesh/Project/Copy Project"

# 2. Copy environment template
cp .env.example .env
# (Optional) Edit .env for your needs

# 3. Build and start
docker compose up --build

# 4. Open the app
open http://localhost:8000
```

### Option B: Local Python

```bash
# 1. Navigate to backend
cd backend

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp ../.env.example .env

# 5. Start the server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 6. Open the app
open http://127.0.0.1:8000
```

## 2. Data Directory Initialisation

The app automatically creates:

- `backend/data/` — directory for SQLite DB and local blobs
- `backend/data/clipboard.db` — SQLite metadata database
- `backend/data/blobs/` — local file storage (if `CLIP_STORAGE=local`)

No manual migration or schema creation is needed; the schema is created on startup.

## 3. Configuration

Edit `.env` for your deployment:

```bash
# Storage
CLIP_STORAGE=local          # or minio

# Limits
CLIP_MAX_UPLOAD_MB=50
CLIP_DEFAULT_TTL=900
CLIP_MAX_TTL=86400

# Security
CLIP_ALLOWED_HOSTS=localhost,127.0.0.1
CLIP_CORS_ORIGINS=*
CLIP_RATE_LIMIT_SEND=20/minute
```

## 4. Verification Checklist

- [ ] `docker compose ps` shows `openclipboard-app` as `Up`
- [ ] `curl http://localhost:8000/health` returns `{"status":"ok"}`
- [ ] Send text returns a 12-character code
- [ ] Retrieve with that code returns the text
- [ ] Image upload and download works
- [ ] One-shot content deletes after download
- [ ] Expired content is purged

## 5. Stopping and Cleaning Up

```bash
# Stop containers (keeps data volumes)
docker compose stop

# Stop and remove containers (keeps data volumes)
docker compose down

# Stop and remove everything including data
docker compose down -v

# Local Python
pkill -f "uvicorn app.main:app"
rm -rf backend/data/
```

## 6. Upgrading

```bash
docker compose pull          # if using remote images
docker compose up --build    # rebuild local image
docker compose up -d         # restart
```

Data in `clip-data` volume persists across upgrades.
