# Git Workflow

## 1. Branch Naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<description>` | `feature/rate-limiting` |
| Fix | `fix/<description>` | `fix/sql-injection` |
| Security | `security/<description>` | `security/secret-scanning` |
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

## 3. Branch Protection (`main`)

The `main` branch is protected — see [BRANCH-POLICY.md](../BRANCH-POLICY.md):

- Pull request required before merging
- 1 approving review (from a CODEOWNER)
- Status checks must pass (security, quality, Docker build, PR review)
- Signed commits required
- Linear history required
- Force pushes and deletions blocked
- Administrators are **not** exempt

Direct pushes to `main` are rejected locally by `.githooks/pre-push` and remotely
by the branch protection rule.

## 4. Pull Request Process

1. Create a feature branch from `main`
2. Implement changes and add/update tests (`pytest tests/`)
3. Run the security tooling (`./scripts/security_audit.sh --full`)
4. Commit (the pre-commit hook scans for secrets and blocks `.env`)
5. Push the branch (the pre-push hook runs the full audit)
6. Open a PR with description and testing notes
7. Ensure all CI checks pass
8. Merge after approval (squash merge; linear history)

## 5. Local Hook Setup

```bash
./scripts/install_hooks.sh
```

This sets `core.hooksPath` to `.githooks` and makes the hooks executable.

## 6. Applying Repository Settings

Branch protection and security features are applied through the GitHub API:

```bash
export GITHUB_TOKEN=ghp_xxx
./scripts/apply_repo_settings.sh            # apply
./scripts/apply_repo_settings.sh --verify   # read back current state
./scripts/apply_repo_settings.sh --dry-run  # print requests only
```

## 7. Versioning

Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`

- `MAJOR` — breaking API changes
- `MINOR` — new features, backward compatible
- `PATCH` — bug fixes, security patches

Current version: `1.0.0`

## 8. Tagging

```bash
git tag v1.0.0
git push origin v1.0.0
```

