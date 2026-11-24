# 03-deploy-network-security.md

# Network Security

## 1. Network Zones

```
┌─────────────────┐      TLS (443)      ┌──────────────────┐
│   Internet      │ ───────────────────►│  Reverse Proxy   │
│   (Untrusted)   │                     │  (DMZ)           │
└─────────────────┘                     └────────┬─────────┘
                                                 │ HTTP (8000)
                                                 │ Internal only
                                                 ▼
                                      ┌──────────────────┐
                                      │ OpenClipboard    │
                                      │ App (127.0.0.1)  │
                                      │ (Trusted Zone)   │
                                      └────────┬─────────┘
                                               │ Internal
                                               ▼
                                      ┌──────────────────┐
                                      │   MinIO (optional)│
                                      │   (9000/9001)    │
                                      └──────────────────┘
```

## 2. Firewall Rules

| From | To | Port | Protocol | Reason |
|------|----|------|----------|--------|
| Internet | Reverse Proxy | 443 | HTTPS | Public access |
| Internet | Reverse Proxy | 80 | HTTP | Redirect to HTTPS |
| Reverse Proxy | App | 8000 | HTTP | Internal traffic |
| App | MinIO | 9000 | HTTP | Object storage |
| Admin | MinIO Console | 9001 | HTTP | Management (restricted) |
| All others | All | All | All | Deny |

## 3. TLS Configuration

- Use TLS 1.2 or 1.3 only
- Strong cipher suites
- Valid certificate from Let's Encrypt or internal CA
- HSTS enabled (`Strict-Transport-Security` header)
- HTTP → HTTPS redirect

## 4. Host Header Protection

The app uses `TrustedHostMiddleware` to reject requests with unexpected `Host` headers:

```env
CLIP_ALLOWED_HOSTS=clipboard.yourdomain.com,localhost,127.0.0.1
```

## 5. CORS Policy

```env
CLIP_CORS_ORIGINS=https://clipboard.yourdomain.com
```

Never use `*` in production.

## 6. Rate Limiting at Edge

The reverse proxy should enforce rate limits before traffic reaches the app:

- Caddy/Nginx: `limit_req` or `ratelimit` middleware
- Cloudflare: Rate limiting rules
- AWS WAF: Rate-based rules

## 7. Content Security Policy

```http
Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; script-src 'self'; base-uri 'self'; form-action 'self'
```

Prevents XSS and unauthorized resource loading.

## 8. Headers Summary

| Header | Value | Purpose |
|--------|-------|---------|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Force HTTPS |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `Referrer-Policy` | `no-referrer` | Don't leak referrer |
| `Content-Security-Policy` | (see above) | Prevent XSS |
| `Cache-Control` | `no-store` | Don't cache sensitive content |

## 9. MinIO Network Security

- Bind MinIO to `127.0.0.1` or internal network only
- Never expose MinIO Console (9001) to the internet
- Change default `minioadmin` credentials
- Use `MINIO_SECURE=true` with TLS in production

## 10. Database Security

- SQLite file permissions: `600` (owner read/write only)
- Directory permissions: `700`
- No network access to SQLite (local file only)
- Regular backups with encrypted storage

## 11. Checklist

- [ ] Reverse proxy terminates TLS
- [ ] App binds to `127.0.0.1` only
- [ ] MinIO not exposed to internet
- [ ] `CLIP_ALLOWED_HOSTS` set to production domain
- [ ] `CLIP_CORS_ORIGINS` set to production domain (not `*`)
- [ ] Default MinIO credentials changed
- [ ] Rate limiting configured at edge
- [ ] Security headers verified
- [ ] Firewall rules applied
- [ ] SQLite file permissions restricted
