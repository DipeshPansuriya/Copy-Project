# Authentication and Security

## 1. Authentication Model (v1)

OpenClipboard v1 uses **capability-based access**. There are no usernames, passwords, or sessions.

- The **12-character code** is the sole credential.
- Anyone who knows the code can retrieve, download, or delete the content.
- No cookies, no JWT, no OAuth.

## 2. Authorization

| Action | Required | Enforced By |
|--------|----------|-------------|
| Send content | None | Rate limit only |
| Retrieve content | Valid 12-character code | Code lookup + expiry check |
| Download file | Valid 12-character code | Code lookup + expiry check |
| Delete content | Valid 12-character code | Code lookup |
| View stats | None | Rate limit only |

## 3. Security Controls

| Control | Implementation |
|---------|---------------|
| Code entropy | `secrets.choice over [A-Za-z0-9]` — cryptographically random |
| Brute force protection | Rate limiting: 30/min on retrieve endpoints |
| SQL injection | Parameterized queries via `aiosqlite` |
| XSS | Frontend `escapeHtml()` + CSP `script-src 'self'` |
| File upload | Magic-byte verification; executables rejected |
| Path traversal | UUID-based object keys; filenames sanitized |
| Host header | `TrustedHostMiddleware` |
| Clickjacking | `X-Frame-Options: DENY` |

## 4. Future Enhancements (v2)

| Feature | Description |
|---------|-------------|
| JWT auth | Optional authentication so only sender can delete |
| Password-protected clips | AES-256 encryption with user-supplied password |
| API keys | For programmatic access without a code |
| Audit log | Who retrieved/deleted what and when |

## 5. Secrets Management

| Secret | Source | Rotation |
|--------|--------|----------|
| MinIO root user/password | `MINIO_ROOT_USER`, `MINIO_ROOT_PASSWORD` env vars | Manual |
| App secret key (future) | `CLIP_SECRET_KEY` env var | Manual |

> Never commit `.env` or secrets to version control. Use `.env.example` as a template.
