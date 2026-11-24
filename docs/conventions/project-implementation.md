# Project Implementation

## 1. Project Structure

```
/Users/dipesh/Desktop/Dipesh/Project/Copy Project/
├── PRD.md                        # Product requirements
├── API.md                        # API reference
├── ARCHITECTURE.md               # System architecture
├── DATABASE.md                   # Database schema
├── DESIGN.md                     # UI/UX and API design
├── SECURITY.md                   # Security policy and controls
├── README.md                     # Quick start and overview
├── .env.example                  # Environment variable template
├── docker-compose.yml            # Docker Compose definition
├── backend/
│   ├── Dockerfile                # Container image
│   ├── requirements.txt          # Python dependencies
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app, security middleware, lifespan
│   │   ├── config.py             # Settings from env vars
│   │   ├── db.py                 # SQLite metadata store
│   │   ├── storage.py            # Local + MinIO blob backends
│   │   ├── purge.py              # Background expiry sweeper
│   │   ├── deps.py               # App singletons + rate limiter
│   │   ├── schemas.py            # Pydantic models
│   │   └── api/
│   │       ├── __init__.py
│   │       └── items.py          # /api/send, /api/retrieve, /api/file, ...
│   ├── static/
│   │   ├── index.html            # Single-page UI
│   │   ├── style.css             # Styles
│   │   └── app.js                # Frontend logic
│   └── data/                     # SQLite DB + local blobs (created at runtime)
├── docs/
│   ├── conventions/              # Development conventions
│   ├── architecture/             # Architecture diagrams
│   ├── deployment/               # Deployment guides
│   ├── workflow/                 # Workflow definitions
│   └── process-flow/             # Process flow diagrams
└── data/                         # (Docker volume mount point)
```

## 2. Technology Stack

| Layer | Technology | License |
|-------|-----------|---------|
| Language | Python 3.13 | PSF |
| Backend Framework | FastAPI | MIT |
| Web Server | Uvicorn | BSD |
| Database | SQLite | Public domain |
| Async DB Driver | aiosqlite | MIT |
| Rate Limiting | slowapi | MIT |
| File Type Verification | python-magic | MIT |
| Object Storage | MinIO (optional) / Local Disk | AGPLv3 / Apache-2.0 |
| Frontend | Vanilla HTML/CSS/JS | — |
| Container | Docker / Compose | Apache-2.0 |

## 3. Implementation Status

| Component | Status |
|-----------|--------|
| Backend API (send/retrieve/file/delete/stats) | ✅ Complete |
| Frontend UI (send/retrieve panels) | ✅ Complete |
| Local disk storage | ✅ Complete |
| MinIO storage backend | ✅ Complete |
| Rate limiting | ✅ Complete |
| Security headers | ✅ Complete |
| Magic-byte file verification | ✅ Complete |
| Executable rejection | ✅ Complete |
| Background purge worker | ✅ Complete |
| Docker Compose | ✅ Complete |
| Documentation (PRD, API, Architecture, etc.) | ✅ Complete |
| User accounts / auth | ❌ Not in v1 |
| End-to-end encryption | ❌ Not in v1 |
| MCP server | ❌ Not in v1 |
| CI/CD pipeline | ❌ Not in v1 |

## 4. Build & Run

```bash
# Docker
docker compose up --build

# Local Python
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload
```

## 5. Testing

Manual testing with `curl` (see `API.md` for examples). Automated test suite not yet implemented.
