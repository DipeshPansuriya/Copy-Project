# Git Workflow

## 1. Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<description>` | `feature/rate-limiting` |
| Fix | `fix/<description>` | `fix/sql-injection` |
| Docs | `docs/<description>` | `docs/api-endpoints` |
| Release | `release/v<version>` | `release/v1.0.0` |
| Hotfix | `hotfix/<description>` | `hotfix/critical-bug` |

## 2. Commit Message Convention

```
<type>: <short description>

[optional body]

[optional footer]
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `security`

Examples:
```
feat: add rate limiting to send endpoint

fix: reject executable uploads via magic bytes

security: add TrustedHostMiddleware and CSP headers
```

## 3. Pull Request Process

1. Create feature branch from `main`
2. Implement changes
3. Run tests (`python -m pytest` if available, or manual curl tests)
4. Verify Docker build (`docker compose build`)
5. Open PR with description and testing notes
6. Review and merge

## 5. Versioning

Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`

- `MAJOR` — breaking API changes
- `MINOR` — new features, backward compatible
- `PATCH` — bug fixes, security patches

Current version: `1.0.0`

## 6. Tagging

```bash
git tag v1.0.0
git push origin v1.0.0
```
