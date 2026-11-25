# DESIGN

## 1. Design Principles

| Principle | Description |
|-----------|-------------|
| **Simplicity first** | Single-file SQLite, no build step for frontend, one Docker container |
| **Open source only** | FastAPI, SQLite, MinIO, python-magic, slowapi — all OSS |
| **Ephemeral by default** | Content dies; nothing persists forever without intent |
| **Capability-based security** | The 12-character code is the key; no passwords, no accounts |
| **Fail closed** | Invalid codes, executables, and oversized files are rejected |

## 2. UI Design

### Layout

```
┌─────────────────────────────────────────────────────────────┐
│  📋 OpenClipboard          [ Stats: 42 active • 1.0 MB ]    │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │      SEND        │  │    RETRIEVE      │                │
│  │                  │  │                  │                │
│  │  [ Text / Image  │  │  [ 123456 ] [Retrieve]            │
│  │    / File tabs ] │  │                  │                │
│  │                  │  │  [Result Panel]  │                │
│  │  [Expires: 15m]  │  │                  │                │
│  │  [One-shot ☐]    │  │                  │                │
│  │  [ Send ]        │  │                  │                │
│  │  Code: 123456    │  │                  │                │
│  └──────────────────┘  └──────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### Tabs

- **Text** — textarea with paste-from-clipboard support
- **Image** — drag-and-drop zone with preview; paste image support
- **File** — drag-and-drop zone; any file type (non-executable)

### Options

- **Expires in** — dropdown: 1 min, 5 min, 15 min (default), 30 min, 1 hour, 24 hours
- **Delete after first download** — toggle switch for burn-after-read

### Result Panel

- Displays the 12-character code in monospace characters
- Shows kind, size, and TTL
- Live countdown to expiry
- "Copy share link" button
- Hint text explaining how to retrieve

### Retrieve Panel

- 12-character code input (alphanumeric, max 12 chars)
- Retrieve button
- Result area: text in `<pre>`, image in ``, file with download link
- "Copy text" button for text entries
- "Delete now" button for immediate removal
- Error messages for invalid/expired codes

## 3. Color Palette

| Role | Hex | Usage |
|------|-----|-------|
| Background | `#0f172a` | Page background |
| Panel | `#1e293b` | Cards and containers |
| Text | `#f8fafc` | Primary text |
| Muted | `#94a3b8` | Secondary text, hints |
| Accent | `#38bdf8` | Primary buttons, links |
| Success | `#4ade80` | Codes, success states, countdowns |
| Error | `#f87171` | Error messages, expired states |

## 4. API Design Principles

- **RESTful** with resource-oriented URLs (`/api/send`, `/api/retrieve/{code}`)
- **Capability-based** — no auth tokens; code is the credential
- **Idempotent deletes** — `DELETE` on already-deleted code returns 404
- **Consistent errors** — all errors return `{"detail": "message"}`
- **Versioned implicitly** — `/api/` prefix; future versions at `/api/v2/`

## 5. Storage Design

### Abstraction

```python
class Storage:
    async def put(key, data, content_type) -> None
    async def get(key) -> Optional[bytes]
    async def stat(key) -> Optional[tuple[int, str]]
    async def delete(key) -> None
    async def stream(key) -> Optional[tuple[async_iterator, int, str]]
```

### Implementations

| Backend | Use Case | Pros | Cons |
|---------|----------|------|------|
| `LocalStorage` | Development, single-node | Zero dependencies, fast | Not shared across instances |
| `MinioStorage` | Production, multi-node | S3-compatible, scalable | Requires MinIO service |

### Object Key Format

```
{uuid4().hex}/{uuid4().hex}
```

- Never uses user-supplied filenames as keys
- Prevents path traversal and collisions
- Enables clean sharding if needed later

## 6. Concurrency Model

- **Async/await** throughout (FastAPI + aiosqlite)
- **SQLite WAL mode** for concurrent reads
- **Single writer** — SQLite limitation; acceptable for v1 self-hosting
- **Purge worker** — single `asyncio.Task` running in background
- **Rate limiter** — in-memory `slowapi` limiter (per-process)

## 7. Frontend Design

- **Vanilla JS** — no frameworks, no build step, no npm
- **ES modules** — IIFE pattern for namespace isolation
- **Fetch API** — all backend communication
- **Blob URLs** — image previews via `URL.createObjectURL`
- **Clipboard API** — `navigator.clipboard` for copy/paste
- **Responsive** — CSS grid, mobile-friendly breakpoints at 480px

## 8. Security Design

### Defense in Depth

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 7: WAF / Reverse Proxy (optional, production)        │
├─────────────────────────────────────────────────────────────┤
│  Layer 6: Rate Limiting (slowapi, per-IP)                   │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Input Validation (regex, MIME magic, size limits) │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Parameterized Queries (aiosqlite, no SQLi)        │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Security Headers (CSP, HSTS, X-Frame-Options)     │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Capability-Based Access (12-character code)            │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Auto-Expiration (TTL + one-shot + purge worker)   │
└─────────────────────────────────────────────────────────────┘
```

## 9. Trade-offs

| Trade-off | Decision | Reason |
|-----------|----------|--------|
| SQLite vs PostgreSQL | SQLite | Zero ops; sufficient for single-instance |
| Local disk vs MinIO | Both | Local for dev; MinIO for prod |
| No auth vs Auth | No auth | Simplest UX; code is the credential |
| No encryption vs Encryption | No encryption | v1 scope; add later if needed |
| 12-character code vs UUID | 12-character | Easy to type on mobile; rate-limited |
