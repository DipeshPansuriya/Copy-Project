# SECURITY

## Security Policy

OpenClipboard is a self-hosted, temporary pastebin-style service. Security is designed around **capability-based access** (the 6-digit code) and **automatic data destruction** (TTL expiry + one-shot deletion).

## 1. Threat Model

| Threat | Actor | Mitigation |
|--------|-------|------------|
| Code guessing / brute force | External attacker | 6-digit random code + rate limiting (15 failed attempts triggers 429) |
| SQL injection | External attacker | Parameterized queries via `aiosqlite`; no string interpolation |
| Path traversal | External attacker | Object keys are UUIDs; filenames sanitized to basename only |
| XSS via stored text | External attacker | Frontend `escapeHtml()`; CSP `script-src 'self'` |
| Malicious file upload | External attacker | Magic-byte verification; executables (ELF/PE/Mach-O/shebang) rejected |
| Host header attack | External attacker | `TrustedHostMiddleware` |
| Clickjacking | External attacker | `X-Frame-Options: DENY` |
| MIME sniffing | External attacker | `X-Content-Type-Options: nosniff` |
| Data persistence after expiry | Operator / attacker | Background purge worker + lazy purge on access |

## 2. Authentication & Authorization

v1 has **no user accounts**. The 6-digit code is the capability:

- Anyone with the code can `GET /api/retrieve/{code}`
- Anyone with the code can `DELETE /api/item/{code}`
- Anyone with the code can `GET /api/file/{code}`

> ⚠️ Share codes only through trusted channels. Do not post codes publicly.

### Future (v2)
- Optional JWT auth so only the sender can delete
- API keys for programmatic access
- Password-protected clips

## 3. Rate Limiting

Powered by `slowapi`, keyed by client IP:

| Endpoint | Limit |
|----------|-------|
| `POST /api/send` | 20 / minute |
| `GET /api/retrieve/{code}` | 30 / minute |
| `GET /api/file/{code}` | 30 / minute |
| `GET /api/item/{code}` | 30 / minute |
| `DELETE /api/item/{code}` | 10 / minute |
| `GET /api/stats` | 30 / minute |

Exceeding a limit returns `HTTP 429 Too Many Requests`.

## 4. Input Validation

| Input | Validation |
|-------|------------|
| Code | Regex `^\d{6}$` (6 digits only) |
| `kind` | Must be `text`, `image`, or `file` |
| `ttl` | Integer between `CLIP_MIN_TTL` and `CLIP_MAX_TTL` |
| File size | ≤ `CLIP_MAX_UPLOAD_BYTES` (default 50 MB) |
| File type | Magic-byte verified; executables rejected |
| Filename | Basename only; path separators stripped |

## 5. File Upload Security

- Client `Content-Type` header is **never trusted**
- `python-magic` inspects the first bytes of the file
- Images must match: `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/bmp`
- Executables rejected by magic signature:
  - ELF (`\x7fELF`)
  - PE / Windows (`MZ`)
  - Mach-O / macOS (`\xca\xfe\xba\xbe`, etc.)
  - Shell scripts (`#!`)

## 6. Security Headers

All responses include:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |
| `Content-Security-Policy` | `default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |

## 7. Data Retention & Destruction

- Content is hard-deleted after its TTL (default 15 min, max 24h)
- One-shot content is deleted immediately after first download
- Background purge worker runs every 30s (configurable)
- Lazy purge: expired rows are deleted on access if the worker missed them
- Blobs and metadata are deleted together; no orphaned data

## 8. Deployment Security

### Recommended Production Setup

```
Internet
   │
   ▼
[ Caddy / Nginx / Traefik ]
  - TLS termination (HTTPS)
  - Rate limiting at edge
  - WAF rules
  - Client max body size
   │
   ▼
[ OpenClipboard (uvicorn, 127.0.0.1:8000 only) ]
   │
   ▼
[ SQLite + Local Disk / MinIO ]
```

- Never expose uvicorn directly to the internet
- Bind uvicorn to `127.0.0.1` behind a reverse proxy
- Use `CLIP_ALLOWED_HOSTS` to restrict Host headers
- Use `CLIP_CORS_ORIGINS` to restrict cross-origin requests

## 9. Environment Variables (Security-Related)

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIP_ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | TrustedHostMiddleware allowlist |
| `CLIP_CORS_ORIGINS` | `*` | CORS allowed origins (restrict in prod) |
| `CLIP_RATE_LIMIT_SEND` | `20/minute` | Send endpoint rate limit |
| `CLIP_RATE_LIMIT_RETRIEVE` | `30/minute` | Retrieve endpoint rate limit |
| `CLIP_RATE_LIMIT_FILE` | `30/minute` | File download rate limit |
| `CLIP_RATE_LIMIT_DELETE` | `10/minute` | Delete endpoint rate limit |
| `CLIP_MAX_UPLOAD_MB` | `50` | Max upload size in MB |
| `CLIP_MAX_TTL` | `86400` | Max TTL in seconds (24h) |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minioadmin` | Change in production |

## 10. Known Limitations (v1)

- No end-to-end encryption (content is stored plaintext at rest)
- No user accounts (code is the only credential)
- No audit log of who retrieved/deleted what
- SQLite is single-writer; not suitable for multi-instance horizontal scaling without MinIO + shared DB

## 11. Reporting Security Issues

Please report vulnerabilities privately. Do not file public issues for security bugs.
