# Testing Conventions

## 1. Naming

| Type | Pattern | Example |
|------|---------|---------|
| Test file | `test_<module>.py` | `test_items.py` |
| Test function | `test_<scenario>` | `test_send_text_success` |
| Test class | `Test<Component>` | `TestSendEndpoint` |

## 2. Test Structure (Future pytest Suite)

```python
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_send_text_success():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/send", data={
            "kind": "text",
            "text": "hello world",
            "ttl": "300"
        })
    assert response.status_code == 200
    data = response.json()
    assert len(data["code"]) == 6
    assert data["kind"] == "text"
```

## 3. Test Data Conventions

- Use non-sensitive placeholder data
- Use unique codes per test to avoid collisions
- Clean up created items after tests (or rely on TTL)

## 4. Security Test Conventions

Every security fix must have a corresponding test:

| Fix | Test |
|-----|------|
| SQL injection | Malicious code returns 400 |
| Executable rejection | ELF binary returns 422 |
| XSS escaping | `<script>` stored literally |
| Rate limiting | 31st request returns 429 |

## 5. Where to Place Tests

```
backend/
  tests/
    __init__.py
    test_api.py
    test_storage.py
    test_security.py
    test_purge.py
```

## 6. Running Tests (Future)

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/
```

## 7. Coverage Target (Future)

- Lines: 80%
- Branches: 70%
- Security-critical paths: 100%
