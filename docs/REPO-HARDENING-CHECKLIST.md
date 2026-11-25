# Repository Hardening Checklist — OpenClipboard

This checklist is used to harden the OpenClipboard GitHub repository, modeled on
the security configuration of
[DipeshPansuriya/MLX_Model_App](https://github.com/DipeshPansuriya/MLX_Model_App).

## Repository Settings

- [ ] Repository is public with proper governance docs
- [ ] `SECURITY.md` is present at repository root
- [ ] `CODEOWNERS` is present in `.github/`
- [ ] `CONTRIBUTING.md` is present at repository root
- [ ] `CODE_OF_CONDUCT.md` is present at repository root
- [ ] Issue templates are configured (bug, feature, security, deployment)
- [ ] Pull request template is present
- [ ] `dependabot.yml` is present in `.github/`

## Branch Protection (`main`)

- [ ] Require a pull request before merging — Enabled
- [ ] Required approving reviews — 1
- [ ] Dismiss stale approvals on new commits — Enabled
- [ ] Require review from Code Owners — Enabled
- [ ] Require status checks before merging — Enabled
- [ ] Require branches up to date — Enabled
- [ ] Require conversation resolution — Enabled
- [ ] Require signed commits — Enabled
- [ ] Require linear history — Enabled
- [ ] Allow force pushes — Disabled
- [ ] Allow deletions — Disabled
- [ ] Do not allow bypassing (includes admins) — Enabled

## Security and Analysis

- [ ] Dependency graph — Enabled
- [ ] Dependabot alerts — Enabled
- [ ] Dependabot security updates — Enabled
- [ ] Secret scanning — Enabled
- [ ] Push protection — Enabled
- [ ] Code scanning (CodeQL) — Enabled

## CI/CD Workflows

- [ ] `.github/workflows/security.yml` — Secret scanning, bandit, safety, dependency review
- [ ] `.github/workflows/codeql.yml` — CodeQL static analysis
- [ ] `.github/workflows/quality.yml` — Lint, test, Docker build
- [ ] `.github/workflows/pr-review.yml` — PR title convention, security audit

## Git Hooks (Local)

- [ ] `.githooks/pre-commit` — Secret scan, .env exclusion, quick audit
- [ ] `.githooks/pre-push` — Secret scan, branch check, full audit
- [ ] `scripts/install_hooks.sh` — Installs hooks and sets `core.hooksPath`
- [ ] `scripts/check_secrets.py` — 19-rule secret scanner
- [ ] `scripts/security_audit.sh` — 21-point security audit

## Secrets Management

- [ ] `.env` is listed in `.gitignore`
- [ ] `.env.example` is committed (template only, no real secrets)
- [ ] No hardcoded passwords/API keys in source code
- [ ] Admin credentials come from environment variables only

## File Upload Security

- [ ] Executable magic byte detection (`EXECUTABLE_MAGIC`) in `storage.py`
- [ ] `python-magic` for MIME type verification
- [ ] Filename sanitization (basename only)
- [ ] Size limits enforced

## API Security

- [ ] `TrustedHostMiddleware` configured
- [ ] `X-Content-Type-Options: nosniff` header
- [ ] `X-Frame-Options: DENY` header
- [ ] `Referrer-Policy: no-referrer` header
- [ ] `Content-Security-Policy` header
- [ ] `Strict-Transport-Security` header
- [ ] Rate limiting via `slowapi`
- [ ] Input validation on all endpoints

## Documentation

- [ ] `docs/GITHUB-POLICY.md` — Repository governance
- [ ] `docs/BRANCH-POLICY.md` — Branch protection rules
- [ ] `docs/PUSH-POLICY.md` — Push restrictions
- [ ] `docs/SECURITY-AUDIT.md` — Audit procedure
- [ ] `SECURITY.md` — Security policy and vulnerability reporting
- [ ] `README.md` — Updated with security and governance info
