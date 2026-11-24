# Feature Development

## 1. Adding a New API Endpoint

1. Define the endpoint in `API.md`
2. Add the route to `backend/app/api/items.py`
3. Add rate limiting via `@deps.limiter.limit(...)`
4. Add input validation (regex, size, type)
5. Add error handling with appropriate HTTP status codes
6. Test with `curl` and browser
7. Update frontend `backend/static/app.js` if needed

### Example

```python
@router.post("/api/new-endpoint")
@deps.limiter.limit(settings.rate_limit_send)
async def new_endpoint(request: Request, ...):
    # Validate input
    # Process
    # Return response
    pass
```

## 2. Adding a New Frontend Feature

1. Add HTML to `backend/static/index.html`
2. Add CSS to `backend/static/style.css`
3. Add JS logic to `backend/static/app.js`
4. Test responsive behavior on mobile
5. Verify XSS escaping with `escapeHtml()`

## 3. Adding a New Storage Backend

1. Implement the `Storage` interface in `backend/app/storage.py`
2. Add backend selection logic in `create_storage()`
3. Add environment variable in `backend/app/config.py`
4. Update `Dockerfile` if new system dependencies are needed
5. Update `docker-compose.yml` if new services are needed

## 4. Testing Checklist

- [ ] Happy path works
- [ ] Invalid input returns 422/400
- [ ] Missing resource returns 404
- [ ] Expired resource returns 410
- [ ] Rate limiting triggers 429
- [ ] Security headers present
- [ ] Frontend handles error gracefully
- [ ] Mobile responsive

## 5. Documentation

Update these files when adding features:
- `API.md` — endpoint reference
- `ARCHITECTURE.md` — if components change
- `DATABASE.md` — if schema changes
- `SECURITY.md` — if security model changes
- `DESIGN.md` — if UI/UX changes
- `PRD.md` — if requirements change
