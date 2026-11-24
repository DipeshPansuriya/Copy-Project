# Testing and QA

## 1. Testing Strategy (v1)

OpenClipboard v1 relies on **manual testing** with `curl` and browser verification. Automated test suites (pytest, Playwright, etc.) are planned for v2.

## 2. Manual Test Scenarios

### Send / Retrieve

| Test | Input | Expected Result |
|------|-------|-----------------|
| Send text | `kind=text, text="hello"` | 200 + 6-digit code |
| Retrieve valid code | `GET /api/retrieve/123456` | 200 + text body |
| Retrieve invalid code | `GET /api/retrieve/abcdef` | 400 |
| Retrieve missing code | `GET /api/retrieve/000000` | 404 |
| Retrieve expired code | Expired TTL | 410 |

### File Upload

| Test | Input | Expected Result |
|------|-------|-----------------|
| Send image | PNG file | 200 + code |
| Download image | `GET /api/file/CODE` | 200 + PNG bytes |
| Send executable | ELF binary | 422 |
| Send oversized file | > 50 MB | 413 |

### One-Shot

| Test | Input | Expected Result |
|------|-------|-----------------|
| Download one-shot | `one_shot=1` | 200 + content |
| Re-retrieve one-shot | Same code | 404 |

### Rate Limiting

| Test | Input | Expected Result |
|------|-------|-----------------|
| Rapid sends | 20+ requests/min | 429 after limit |

## 3. Security Test Scenarios

| Test | Input | Expected Result |
|------|-------|-----------------|
| SQL injection | `123456' OR '1'='1` | 400 |
| Path traversal | `../../../etc/passwd` | 404 |
| XSS in text | `<script>alert(1)</script>` | Stored literally, escaped in UI |
| Code guessing | Brute force | 429 after 30 attempts |

## 4. How to Run Manual Tests

```bash
BASE=http://localhost:8000

# Health
curl $BASE/health

# Send text
CODE=$(curl -s -X POST $BASE/api/send -F kind=text -F text="test" | python3 -c "import sys,json;print(json.load(sys.stdin)['code'])")

# Retrieve
curl $BASE/api/retrieve/$CODE

# Download file
curl $BASE/api/file/$CODE -o /tmp/out

# Delete
curl -X DELETE $BASE/api/item/$CODE
```

## 5. QA Checklist Before Release

- [ ] All endpoints return correct status codes
- [ ] Security headers present on all responses
- [ ] Rate limiting triggers correctly
- [ ] Expired content is purged
- [ ] One-shot content deletes after download
- [ ] Executable uploads are rejected
- [ ] Docker build succeeds
- [ ] `docker compose up` works from clean state
- [ ] Mobile UI is responsive

## 6. Future Automated Testing

| Tool | Purpose |
|------|---------|
| `pytest` | Python unit/integration tests |
| `httpx` | Async HTTP test client |
| `Playwright` | Frontend E2E tests |
| `bandit` | Python security scanning |
| `safety` / `pip audit` | Dependency vulnerability scanning |
| `trivy` | Docker image scanning |

## 7. Test Data

Never use real sensitive data in tests. Use:

- Text: "test content"
- Images: 1x1 PNG
- Files: "test file content"
