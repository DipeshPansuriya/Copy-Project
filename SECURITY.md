# SECURITY

## Security Policy

OpenClipboard is a self-hosted, temporary pastebin-style service. Security is designed around **capability-based access** (the code) and **automatic data destruction** (TTL expiry + one-shot deletion).

This repository follows the same security hardening as
[DipeshPansuriya/MLX_Model_App](https://github.com/DipeshPansuriya/MLX_Model_App),
including branch protection, push restrictions, pre-commit/pre-push hooks,
secret scanning, and CI/CD security workflows.

## Repository Security Settings

The following GitHub security features are enabled:

| Feature | Status |
|---------|--------|
| Branch protection (`main`) | ✅ Enabled |
| Required approving reviews | 1 |
| Required status checks | security scan, quality checks, Docker build |
| Dependabot alerts | ✅ Enabled |
| Secret scanning | ✅ Enabled |
| Push protection | ✅ Enabled |
| Code scanning (CodeQL) | ✅ Enabled |
| Signed commits | ✅ Required |

See [docs/GITHUB-POLICY.md](./docs/GITHUB-POLICY.md) for full repository governance.

## 1. Threat Model

| Threat | Actor | Mitigation |
|--------|-------|------------|
| Code guessing / brute force | External attacker | 12-char case-sensitive alphanumeric code (62^12 space) + rate limiting |
| SQL injection | External attacker | Parameterized queries via `aiosqlite`; no string interpolation |
| Path traversal | External attacker | Object keys are UUIDs; filenames sanitized to basename only |
| XSS via stored text | External attacker | Frontend `escapeHtml()`; CSP `script-src 'self'` |
| Malicious file upload | External attacker | Magic-byte verification; executables (ELF/PE/Mach-O/shebang) rejected |
| Host header attack | External attacker | `TrustedHostMiddleware` |
| Clickjacking | External attacker | `X-Frame-Options: DENY` |
| MIME sniffing | External attacker | `X-Content-Type-Options: nosniff` |
| Data persistence after expiry | Operator / attacker | Background purge worker + lazy purge on access |
| Hardcoded secrets in repo | Contributor | Pre-commit/pre-push secret scanning + CI `detect-secrets` |

## 2. Authentication & Authorization

v1 has **no user accounts**. The code is the sole credential:

- Anyone with the code can `GET /api/retrieve/{code}`
- Anyone with the code can `DELETE /api/item/{code}`
- Anyone with the code can `GET /api/file/{code}`

> ⚠️ Share codes only through trusted channels. Do not post codes publicly.

### Future (v2)

- Optional JWT auth so only the sender can delete
- API keys for programmatic access
- Password-protected clips

## 3. Code Entropy

Codes are **12 characters**, case-sensitive alphanumeric (`[A-Za-z0-9]`):

- Combination space: 62^12 ≈ 3.2 sextillion
- Generated via `secrets.choice()` (cryptographically secure)
- Format validated with `^[\w]{12}$` (alphanumeric only)

> The README previously referenced "6-digit codes"; the implementation uses 12-character codes for stronger entropy.

## 4. Rate Limiting

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

## 5. Brute-Force Lockout

Failed retrieval attempts (wrong password, invalid code) increment a counter:

| Setting | Default |
|---------|---------|
| Max failed attempts | 5 |
| Lockout duration | 300 seconds (5 minutes) |

After `MAX_FAILED_ATTEMPTS` failures, the item is locked for `LOCKOUT_SECONDS`. Successful retrieval resets the counter.

## 6. Input Validation

| Input | Validation |
|-------|------------|
| Code | Regex `^[A-Za-z0-9]{12}$` (12 alphanumeric chars) |
| `kind` | Must be `text`, `image`, or `file` |
| `ttl` | Integer between `CLIP_MIN_TTL` and `CLIP_MAX_TTL` |
| File size | ≤ `CLIP_MAX_UPLOAD_BYTES` (default 50 MB) |
| File type | Magic-byte verified; executables rejected |
| Filename | Basename only; path separators stripped |

## 7. File Upload Security

- Client `Content-Type` header is **never trusted**
- `python-magic` inspects the first bytes of the file
- Images must match: `image/png`, `image/jpeg`, `image/gif`, `image/webp`, `image/bmp`
- Executables rejected by magic signature:
  - ELF (`\x7fELF`)
  - PE / Windows (`MZ`)
  - Mach-O / macOS (`\xca\xfe\xba\xbe`, etc.)
  - Shell scripts (`#!`)

## 8. Security Headers

All responses include:

| Header | Value |
|--------|-------|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |
| `Content-Security-Policy` | `default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` |

## 9. Data Retention & Destruction

- Content is hard-deleted after its TTL (default 15 min, max 24h)
- One-shot content is deleted immediately after first download
- Background purge worker runs every 30s (configurable)
- Lazy purge: expired rows are deleted on access if the worker missed them
- Blobs and metadata are deleted together; no orphaned data

## 10. Deployment Security

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

## 11. Environment Variables (Security-Related)

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
| `CLIP_MAX_FAILED_ATTEMPTS` | `5` | Max failed attempts before lockout |
| `CLIP_LOCKOUT_SECONDS` | `300` | Lockout duration in seconds |
| `CLIP_ADMIN_PASSWORD` | `admin` | ⚠️ CHANGE IN PRODUCTION |
| `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` | `minioadmin` | Change in production |

> Never commit `.env` or secrets to version control. Use `.env.example` as a template.

## 12. Local Git Hooks

Install hooks to enforce security on every commit and push:

```bash
./scripts/install_hooks.sh
```

- **pre-commit**: scans staged files for secrets, blocks `.env` commits, runs quick security audit
- **pre-push**: runs full secret scan, blocks direct push to `main`, runs full security audit

## 13. Known Limitations (v1)

- No end-to-end encryption (content is stored plaintext at rest)
- No user accounts (code is the only credential)
- No audit log of who retrieved/deleted what
- SQLite is single-writer; not suitable for multi-instance horizontal scaling without MinIO + shared DB

## 14. Reporting Security Issues

Please report vulnerabilities privately. Do not file public issues for security bugs.

