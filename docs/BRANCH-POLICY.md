# Branch Policy — OpenClipboard

This document defines the branch protection rules and branching model enforced on
the OpenClipboard repository, modeled on
[DipeshPansuriya/MLX_Model_App](https://github.com/DipeshPansuriya/MLX_Model_App).

## 1. Protected Branches

| Branch | Protected | Required Reviews | Status Checks Required |
|--------|-----------|------------------|------------------------|
| `main` | ✅ Yes | 1 | security scan, quality checks, Docker build |
| `develop` (if created) | ✅ Yes | 1 | quality checks |

## 2. Protection Rules for `main`

The `main` branch is protected with the following settings:

1. **Require a pull request before merging** — Enabled
2. **Required approving reviews** — 1 (from a CODEOWNER)
3. **Dismiss stale pull request approvals when new commits are pushed** — Enabled
4. **Require review from Code Owners** — Enabled
5. **Require status checks to pass before merging** — Enabled
   - `security-scan / Secret Scanning`
   - `quality-checks / Lint & Format`
   - `quality-checks / Run Tests`
   - `quality-checks / Docker Build`
   - `dependency-review / Dependency Review`
6. **Require branches to be up to date before merging** — Enabled
7. **Require conversation resolution before merging** — Enabled
8. **Require signed commits** — Enabled
9. **Require linear history** — Enabled
10. **Allow force pushes** — Disallowed
11. **Allow deletions** — Disallowed
12. **Do not allow bypassing the above settings** — Enabled (includes administrators)

## 3. Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<description>` | `feature/password-protection` |
| Fix | `fix/<description>` | `fix/xss-escaping` |
| Security | `security/<description>` | `security/rate-limiting` |
| Docs | `docs/<description>` | `docs/api-reference` |
| Release | `release/v<version>` | `release/v1.0.0` |
| Hotfix | `hotfix/<description>` | `hotfix/critical-bug-fix` |

## 4. Merging Strategy

- Pull requests must be merged via **squash and merge** or **create a merge commit**
- Direct push to `main` is blocked for all users including administrators
- Merge queue is not required for this repository size

## 5. Stale PR Handling

- Pull requests with no activity for 30 days are marked as stale
- Stale PRs are closed after 7 additional days of inactivity unless a maintainer
  comments requesting it to stay open
