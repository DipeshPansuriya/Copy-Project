# API Documentation

## Base URL

- Development: `http://localhost:8000`
- Docker: `http://localhost:8000`
- Production: `https://clipboard.yourdomain.com`

## Authentication

v1 uses **capability-based access**: the 6-digit code is the sole credential. Anyone who knows the code can retrieve or delete the content. No sessions, cookies, or API keys are required.

> ⚠️ Treat the code like a password. Share it only through trusted channels.

## Endpoints

### Send Content

**`POST /api/send`**

Creates a new clipboard entry and returns a 6-digit retrieval code.

**Request** (`multipart/form-data`)

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `kind` | string | No | `text`, `image`, or `file` (default: `text`) |
| `text` | string | Yes (if kind=text) | Text content |
| `file` | file | Yes (if kind=image/file) | Uploaded file |
| `ttl` | integer | No | Expiry in seconds (30–86400, default: 900) |
| `one_shot` | integer | No | `1` to delete after first download (default: 0) |

**Response** (`200 OK`)

```json
{
  "code": "123456",
  "kind": "text",
  "filename": null,
  "size": 25,
  "ttl": 900,
  "created_at": "2026-11-24T10:00:00+00:00",
  "expires_at": "2026-11-24T10:15:00+00:00",
  "one_shot": false,
  "url": "/?code=123456"
}
```

**Rate limit:** 20 requests/minute per IP

---

### Retrieve Metadata

**`GET /api/retrieve/{code}`**

Returns item metadata. For text entries, the body is included inline.

**Response** (`200 OK`)

```json
{
  "item": {
    "code": "123456",
    "kind": "text",
    "filename": null,
    "content_type": "text/plain; charset=utf-8",
    "size": 25,
    "created_at": "2026-11-24T10:00:00+00:00",
    "expires_at": "2026-11-24T10:15:00+00:00",
    "one_shot": false,
    "retrieved_at": null,
    "downloads": 0,
    "expired": false
  },
  "file_url": "/api/file/123456",
  "text": "Hello world"
}
```

**Errors**

| Status | Meaning |
|--------|---------|
| 400 | Code is not 6 digits |
| 404 | Code does not exist |
| 410 | Code expired or already consumed (one-shot) |

**Rate limit:** 30 requests/minute per IP

---

### Download File

**`GET /api/file/{code}`**

Streams the stored blob. One-shot entries are deleted after the download completes.

**Headers**

| Header | Value |
|--------|-------|
| `Content-Type` | Original MIME type |
| `Content-Disposition` | `inline` for text/image, `attachment` for files |
| `Cache-Control` | `no-store` |
| `X-Content-Type-Options` | `nosniff` |

**Rate limit:** 30 requests/minute per IP

---

### Item Status

**`GET /api/item/{code}`**

Lightweight metadata check for countdown UIs. Same shape as the `item` field in retrieve.

**Rate limit:** 30 requests/minute per IP

---

### Delete Item

**`DELETE /api/item/{code}`**

Permanently removes content and its blob immediately.

**Response:** `204 No Content`

**Rate limit:** 10 requests/minute per IP

---

### Stats

**`GET /api/stats`**

```json
{
  "active": 42,
  "bytes": 1048576
}
```

---

### Health

**`GET /health`**

```json
{
  "status": "ok",
  "app": "OpenClipboard",
  "storage": "local"
}
```

---

## Error Response Format

```json
{
  "detail": "Human-readable error message"
}
```

## Security Headers

All responses include:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Content-Security-Policy: default-src 'self'; ...`
- `Strict-Transport-Security: max-age=31536000; includeSubDomains`

---

## Interactive Docs

Swagger UI: `http://localhost:8000/api/docs`  
ReDoc: `http://localhost:8000/api/redoc`
