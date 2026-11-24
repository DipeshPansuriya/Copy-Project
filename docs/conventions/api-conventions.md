# API Conventions

## 1. URL Structure

All API routes are prefixed with `/api/`:

```
/api/send          POST   - Create a clipboard entry
/api/retrieve/{code} GET    - Retrieve metadata + content
/api/item/{code}   GET    - Item status / countdown metadata
/api/file/{code}   GET    - Download the blob
/api/item/{code}   DELETE - Delete the entry
/api/stats         GET    - Active item count and bytes
/health            GET    - Health check
```

## 2. HTTP Methods

| Method | Use |
|--------|-----|
| `GET` | Safe retrieval (retrieve, item, file, stats, health) |
| `POST` | Create resource (send) |
| `DELETE` | Remove resource (item) |

## 3. Request Body Formats

| Endpoint | Content-Type | Description |
|----------|-------------|-------------|
| `POST /api/send` | `multipart/form-data` | File uploads and form fields |
| Others | N/A | No body required |

## 4. Response Formats

All responses are JSON unless otherwise noted.

**Success:**
```json
{
  "code": "123456",
  "kind": "text",
  ...
}
```

**Error:**
```json
{
  "detail": "Human-readable error message"
}
```

**File download (`/api/file/{code}`):** `application/octet-stream` or original MIME type with `Content-Disposition` header.

## 5. Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 204 | Deleted successfully (no content) |
| 400 | Bad request (invalid code format) |
| 404 | Not found (code does not exist) |
| 410 | Gone (expired or one-shot consumed) |
| 413 | Payload too large (file exceeds limit) |
| 422 | Unprocessable entity (validation error) |
| 429 | Too many requests (rate limited) |
| 500 | Internal server error |

## 6. Date/Time Format

All timestamps are ISO 8601 in UTC:

```
2026-11-24T10:15:00+00:00
```

Internally stored as Unix epoch seconds (float) in SQLite.

## 7. Code Format

- 6 numeric digits: `000000` to `999999`
- Generated via `secrets.randbelow(1_000_000)`
- Validated with regex `^\d{6}$`

## 8. Rate Limit Headers

Rate limits are enforced per client IP. On `429`, the client should wait before retrying.

## 9. Content Negotiation

Only `application/json` is produced and consumed (except file upload/download).

## 10. Idempotency

- `DELETE /api/item/{code}` is idempotent in effect (item is gone), but returns 404 if already deleted.
- `POST /api/send` is not idempotent; each call creates a new code.
