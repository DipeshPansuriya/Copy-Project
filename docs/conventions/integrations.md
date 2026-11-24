# Integrations

## 1. MinIO (Object Storage)

OpenClipboard supports MinIO as an S3-compatible object storage backend.

### Configuration

```yaml
environment:
  CLIP_STORAGE: minio
  MINIO_ENDPOINT: minio:9000
  MINIO_ACCESS_KEY: minioadmin
  MINIO_SECRET_KEY: minioadmin
  MINIO_BUCKET: clipboard
  MINIO_SECURE: "false"
```

### MinIO Console

- URL: `http://localhost:9001`
- Login: `minioadmin` / `minioadmin`

### Bucket

The `clipboard` bucket is created automatically on startup (if it doesn't exist).

## 2. Reverse Proxy (Production)

Recommended: Caddy, Nginx, or Traefik.

### Caddy Example

```caddyfile
clipboard.yourdomain.com {
    reverse_proxy localhost:8000
    
    header /api/* {
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
    }
}
```

### Responsibilities

| Concern | Reverse Proxy | App |
|---------|--------------|-----|
| TLS / HTTPS | ✅ | ❌ |
| Rate limiting (edge) | ✅ | ✅ (slowapi) |
| WAF | ✅ | ❌ |
| Body size limits | ✅ | ✅ (FastAPI) |
| Security headers | ✅ | ✅ (defense in depth) |

## 3. Monitoring (Future)

No built-in metrics in v1. Suggested additions:

- Prometheus metrics endpoint (`/metrics`)
- Health check (`/health`) for load balancer probes
- Structured JSON logging for log aggregation

## 4. CI/CD (Future)

No CI/CD pipeline in v1. Suggested:

- GitHub Actions: build Docker image, run `bandit` + `safety` scans
- Container registry: push tagged images
- Deployment: docker compose on target host

## 5. Client Libraries (Future)

No official SDK in v1. The API is simple enough for direct HTTP calls:

```bash
# Send
curl -X POST http://localhost:8000/api/send -F text="hello"

# Retrieve
curl http://localhost:8000/api/retrieve/123456

# Download
curl http://localhost:8000/api/file/123456 -o output.txt
```

## 6. Third-Party Services

OpenClipboard does not integrate with any third-party SaaS in v1:
- No analytics
- No error tracking (Sentry, etc.)
- No email/SMS providers
- No authentication providers (Auth0, Clerk, etc.)
