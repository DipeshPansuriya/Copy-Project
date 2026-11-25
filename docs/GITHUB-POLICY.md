# GitHub Policy — OpenClipboard

This document describes the repository governance, branch protection, push
controls, and security settings applied to the OpenClipboard GitHub repository.
It is modeled on the security configuration of
[DipeshPansuriya/MLX_Model_App](https://github.com/DipeshPansuriya/MLX_Model_App).

## 1. Repository Visibility

- **Status:** Public (planned migration to Private → Public with proper governance)
- **Owner:** Dipesh Pansuriya (@DipeshPansuriya)
- **URL:** https://github.com/DipeshPansuriya/Copy-Project

## 2. Branch Protection Rules

The following protection rules are enforced on the `main` branch:

| Setting | Value |
|---------|-------|
| Require a pull request before merging | ✅ Enabled |
| Required approving reviews | 1 |
| Dismiss stale pull request approvals when new commits are pushed | ✅ Enabled |
| Require review from Code Owners | ✅ Enabled |
| Require status checks to pass before merging | ✅ Enabled |
| Require branches to be up to date before merging | ✅ Enabled |
| Require conversation resolution before merging | ✅ Enabled |
| Require signed commits | ✅ Enabled |
| Require linear history | ✅ Enabled |
| Lock branch | ❌ Disabled |
| Allow force pushes | ❌ Not allowed (administrators included) |
| Allow deletions | ❌ Not allowed |
| Do not allow bypassing the above settings | ✅ Enabled (includes admins) |
| Restrict who can push to matching branches | Admins only |

### Branch Naming Convention

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<description>` | `feature/rate-limiting` |
| Fix | `fix/<description>` | `fix/sql-injection` |
| Security | `security/<description>` | `security/secret-scanning` |
| Docs | `docs/<description>` | `docs/api-endpoints` |
| Release | `release/v<version>` | `release/v1.0.0` |
| Hotfix | `hotfix/<description>` | `hotfix/critical-bug` |

## 3. Pull Request Process

1. Create a feature branch from `main`
2. Implement changes and add/update tests
3. Run pre-commit checks locally (`./scripts/install_hooks.sh`)
4. Open a pull request against `main`
5. Ensure all CI checks pass (security, quality, PR review workflows)
6. Address review comments
7. Merge after approval

## 4. Security and Analysis Settings

The following GitHub security features are enabled:

| Feature | Status |
|---------|--------|
| Dependency graph | ✅ Enabled |
| Dependabot alerts | ✅ Enabled |
| Dependabot security updates | ✅ Enabled |
| Secret scanning | ✅ Enabled |
| Push protection | ✅ Enabled |
| Code scanning (CodeQL) | ✅ Enabled |

See `.github/dependabot.yml` and `.github/workflows/security.yml` for details.

## 5. Secret Protection

- `.env` and `.env.*` files are excluded via `.gitignore`
- `.env.example` is provided as a template (no real secrets)
- Pre-commit hook scans staged files for hardcoded secrets
- CI runs `detect-secrets` and a custom 19-rule scanner
- Push protection blocks secrets from being pushed

## 6. Code Ownership

See `.github/CODEOWNERS` for file ownership and required reviewers.

## 7. Release and Tagging

- Semantic Versioning (SemVer): `MAJOR.MINOR.PATCH`
- Tags are created for each release: `git tag v1.0.0`
- Release notes are published on GitHub Releases
