# 03-wf-error-handling.md

# Workflow: Error Handling

## 1. Error Classification

| Category | HTTP Status | Examples | Response |
|----------|-------------|----------|----------|
| Client error | 400 | Invalid code format | `{"detail": "Codes are 6 digits"}` |
| Client error | 404 | Code not found | `{"detail": "No such code..."}` |
| Client error | 410 | Expired or one-shot consumed | `{"detail": "This code has expired..."}` |
| Client error | 413 | File too large | `{"detail": "File exceeds...MB limit"}` |
| Client error | 422 | Validation error | `{"detail": "Executable file types..."}` |
| Client error | 429 | Rate limited | `{"detail": "Rate limit exceeded"}` |
| Server error | 500 | Storage failure | `{"detail": "Failed to store content"}` |

## 2. Error Handling Flow

```
Request received
        │
        ▼
   ┌──────────────┐
   │ Validate input│
   └──────┬───────┘
          │
    ┌─────┴─────┐
    │           │
  Invalid     Valid
    │           │
    ▼           ▼
  4xx       Process request
   │            │
   │        ┌───┴───┐
   │        │       │
   │      Error   Success
   │        │       │
   ▼        ▼       ▼
  4xx/5xx   200   200/204
```

## 3. Specific Error Scenarios

### Invalid Code Format
```
Request: GET /api/retrieve/abcdef
Response: 400 Bad Request
Body: {"detail": "Codes are 6 digits"}
```

### Expired Code
```
Request: GET /api/retrieve/123456 (TTL elapsed)
Response: 410 Gone
Body: {"detail": "This code has expired and was deleted"}
Side effect: Blob and metadata row deleted (lazy purge)
```

### One-Shot Already Consumed
```
Request: GET /api/retrieve/123456 (already downloaded)
Response: 410 Gone
Body: {"detail": "This code has expired and was deleted"}
```

### File Too Large
```
Request: POST /api/send with 60 MB file (limit 50 MB)
Response: 413 Payload Too Large
Body: {"detail": "File exceeds the 50 MB limit"}
```

### Executable Upload
```
Request: POST /api/send with ELF binary
Response: 422 Unprocessable Entity
Body: {"detail": "Executable file types are not allowed"}
```

### Rate Limit Exceeded
```
Request: 31st POST /api/send in one minute
Response: 429 Too Many Requests
```

### Storage Failure
```
Request: POST /api/send (disk full or MinIO unavailable)
Response: 500 Internal Server Error
Body: {"detail": "Failed to store content"}
Side effect: Blob rolled back if metadata write failed
```

## 4. Frontend Error Handling

The frontend (`app.js`) handles errors as follows:

| Status | UI Behavior |
|--------|-------------|
| 400 | Show "Please enter a 6-digit code" |
| 404 | Show "No such code" |
| 410 | Show "This code has expired and its content was deleted" |
| 413 | Show file size error |
| 422 | Show validation error |
| 429 | Show rate limit message (implicit via failed request) |
| 500 | Show "Something went wrong" |
| Network error | Show "Something went wrong" |

## 5. Logging

All errors are logged server-side:

```
ERROR: Exception in ASGI application
INFO: 192.168.65.1:PORT - "POST /api/send HTTP/1.1" 500 Internal Server Error
WARNING slowapi: ratelimit 20 per 1 minute exceeded
```

## 6. Error Response Format (Consistent)

```json
{
  "detail": "Human-readable error message"
}
```

All errors return this shape regardless of status code.

## 7. Best Practices

- Never expose stack traces to clients
- Log full errors server-side for debugging
- Return actionable messages to clients
- Use lazy purge for expired items (self-healing)
- Roll back storage writes on metadata failure
