# Testing and QA

## 1. Testing Strategy

OpenClipboard ships an **automated pytest suite** plus a manual smoke checklist.
The automated suite covers the API surface, security controls, storage backends,
file-type detection, admin authentication, and rate limiting.

| Layer | Tool | Location |
|-------|------|----------|
| Unit / integration | `pytest` + `pytest-asyncio` | `backend/tests/` |
| HTTP client | `httpx` (`ASGITransport`) | `backend/tests/conftest.py` |
| Secret scanning | `scripts/check_secrets.py` | repo root |
| Security audit | `scripts/security_audit.sh` | repo root |
| CI | GitHub Actions | `.github/workflows/` |

## 2. Running the Suite

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest tests/ -v
```

Expected result: all tests pass. The suite runs in about 1–2 seconds and uses a
temporary data directory, so it never touches a real database or blob store.

## 3. Test Files

| File | Coverage |
|------|----------|
| `tests/conftest.py` | Environment isolation + lifespan-aware `client` fixture |
| `tests/test_api.py` | send, retrieve, item info, download, delete, stats, health, security headers |
| `tests/test_security.py` | executable rejection, SQL injection, path traversal, XSS, lockout, empty content |
| `tests/test_storage.py` | local storage put/get/stat/delete and streaming uploads |
| `tests/test_rate_limit.py` | slowapi 429 behaviour + configured limits |
| `tests/test_filetype.py` | magic-byte MIME detection and pure-Python fallback |
| `tests/test_admin.py` | admin login, token auth, logout, disabled mode, constant-time compare |

## 4. Manual Test Scenarios

### Send / Retrieve

| Test | Input | Expected Result |
|------|-------|-----------------|
| Send text | `kind=text, text="hello"` | 200 + 12-character code |
| Retrieve valid code | `GET /api/retrieve/{code}` | 200 + text body |
| Retrieve invalid code | `GET /api/retrieve/short` | 400 |
| Retrieve missing code | `GET /api/retrieve/AAAAAAAAAAAA` | 404 |
| Retrieve expired code | Expired TTL | 410 |

### File Upload

| Test | Input | Expected Result |
|------|-------|-----------------|
| Send image | PNG file | 200 + code |
| Download image | `GET /api/file/CODE` | 200 + PNG bytes |
| Send executable | ELF binary | 422 |
| Send oversized file | > `CLIP_MAX_UPLOAD_MB` | 413 |

### One-Shot

| Test | Input | Expected Result |
|------|-------|-----------------|
| Retrieve one-shot | `one_shot=1` | 200 + content |
| Re-retrieve one-shot | Same code | 410 |

### Rate Limiting

| Test | Input | Expected Result |
|------|-------|-----------------|
| Rapid sends | Over the configured limit | 429 |

## 5. Security Test Scenarios

| Test | Input | Expected Result |
|------|-------|-----------------|
| SQL injection | `123456' OR '1'='1` | 400 |
| Path traversal | `../../../etc/passwd` as filename | Stored as `passwd` |
| XSS in text | `<script>alert(1)</script>` | Stored literally, escaped in UI |
| Code guessing | Brute force | 429 / 423 lockout |
| Executable upload | ELF / PE / Mach-O / shebang | 422 |

## 6. Manual Smoke Test

```bash
BASE=http://localhost:8000

# Health
curl $BASE/health

# Send text
CODE=$(curl -s -X POST $BASE/api/send -F kind=text -F text="test" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['code'])")

# Retrieve
curl $BASE/api/retrieve/$CODE

# Download file
curl $BASE/api/file/$CODE -o /tmp/out

# Delete
curl -X DELETE $BASE/api/item/$CODE
```

## 7. QA Checklist Before Release

- [ ] `pytest tests/` passes with zero failures
- [ ] `./scripts/security_audit.sh --full` reports 0 failures
- [ ] `python3 scripts/check_secrets.py --push` reports no secrets
- [ ] All endpoints return correct status codes
- [ ] Security headers present on all responses
- [ ] Rate limiting triggers correctly
- [ ] Expired content is purged
- [ ] One-shot content deletes after download
- [ ] Executable uploads are rejected
- [ ] Docker build succeeds
- [ ] `docker compose up` works from clean state
- [ ] Mobile UI is responsive

## 8. Coverage Target

| Metric | Target |
|--------|--------|
| Lines | 80% |
| Branches | 70% |
| Security-critical paths | 100% |

## 9. Test Data

Never use real sensitive data in tests. Use:

- Text: `"test content"`
- Images: 1x1 PNG
- Files: `"test file content"`
