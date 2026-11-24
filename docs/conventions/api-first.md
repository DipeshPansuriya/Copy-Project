# API-First Development

## 1. Principle

OpenClipboard is designed **API-first**. The frontend is a thin client that consumes the same HTTP API available to any other client (CLI, mobile app, script).

## 2. API Contract

The contract is defined in `API.md`. All endpoint changes must be reflected there before implementation.

## 3. Development Workflow

1. Define/Update endpoint in `API.md`
2. Implement route in `backend/app/api/items.py`
3. Add tests for the endpoint
4. Update frontend `backend/static/app.js` to consume the endpoint
5. Verify with `curl` or browser

## 4. Backward Compatibility

- Breaking changes require a new version prefix (e.g., `/api/v2/`)
- Deprecated endpoints return `410 Gone` with a migration notice
- Query parameters are additive-only

## 5. Client Generation

The API is small enough to document manually. If it grows, consider OpenAPI/Swagger codegen.

Swagger UI is available at `http://localhost:8000/api/docs`.
