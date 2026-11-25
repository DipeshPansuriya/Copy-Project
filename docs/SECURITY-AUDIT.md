# Security Audit Procedure — OpenClipboard

This document describes the security audit process for OpenClipboard, modeled on
the audit script in
[DipeshPansuriya/MLX_Model_App](https://github.com/DipeshPansuriya/MLX_Model_App).

## 1. Automated Audit Script

Run the full security audit before any push or release:

```bash
./scripts/security_audit.sh --full
```

For a quick check (e.g. pre-commit):

```bash
./scripts/security_audit.sh --quick
```

## 2. The 21 Audit Checks

| # | Check | Description |
|---|-------|-------------|
| 1 | `.env` not tracked | `.env` must not be in git |
| 2 | `.env.example` exists | Template file present |
| 3 | `SECURITY.md` exists | Security policy present |
| 4 | `.gitignore` excludes `.env` | .env in gitignore |
| 5 | Branch policy docs | `docs/BRANCH-POLICY.md` exists |
| 6 | Push policy docs | `docs/PUSH-POLICY.md` exists |
| 7 | `CODEOWNERS` | Code owners file present |
| 8 | `dependabot.yml` | Dependabot config present |
| 9 | Secret scanner | `scripts/check_secrets.py` exists |
| 10 | Secret scanner passes | No hardcoded secrets found |
| 11 | No hardcoded admin creds | No plaintext passwords in source |
| 12 | `X-Content-Type-Options` | Security header present |
| 13 | `X-Frame-Options` | Clickjacking protection header |
| 14 | `Strict-Transport-Security` | HSTS header present |
| 15 | `TrustedHostMiddleware` | Host header attack protection |
| 16 | Rate limiting | `slowapi` configured in config.py |
| 17 | Non-root Docker user | Dockerfile runs as non-root |
| 18 | Pre-commit hook | `.githooks/pre-commit` exists |
| 19 | Pre-push hook | `.githooks/pre-push` exists |
| 20 | Security workflow | `.github/workflows/security.yml` exists |
| 21 | Executable detection | `EXECUTABLE_MAGIC` in storage.py |

## 3. Secret Scanner Rules

The custom secret scanner (`scripts/check_secrets.py`) implements 19 rules:

| # | Pattern | What it detects |
|---|---------|-----------------|
| 1 | `AKIA[0-9A-Z]{16}` | AWS Access Key ID |
| 2 | `aws_secret_access_key` | AWS Secret Key |
| 3 | `github_token` / `ghp_` | GitHub PAT |
| 4 | `gitlab_token` / `glpt-` | GitLab token |
| 5 | `slack_token` / `xoxb-` | Slack token |
| 6 | `stripe_live/test_key` / `sk_` | Stripe secret key |
| 7 | `stripe_publishable_key` / `pk_` | Stripe publishable key |
| 8 | `sendgrid_api_key` / `SG.` | SendGrid key |
| 9 | `mailgun_api_key` / `key-` | Mailgun key |
| 10 | `twilio_account_sid` / `AC` | Twilio SID |
| 11 | `twilio_auth_token` | Twilio auth token |
| 12 | `mongodb+srv://` | MongoDB connection string |
| 13 | `postgres://user:pass@` | Database credentials |
| 14 | `redis://` | Redis connection string |
| 15 | `BEGIN ... PRIVATE KEY` | Private key |
| 16 | `ssh-rsa` | SSH public key |
| 17 | `CLIP_ADMIN_PASSWORD`, `MINIO_SECRET_KEY`, `PG_PASSWORD` | App secrets |
| 18 | `Bearer ` | Bearer token |
| 19 | Generic password patterns | Hardcoded passwords |

## 4. CI Security Workflows

| Workflow | Triggers | What it runs |
|----------|----------|--------------|
| `security.yml` | push to main, PR, daily, manual | detect-secrets, bandit, safety, custom scanner, dependency review |
| `codeql.yml` | push to main, PR, weekly, manual | CodeQL static analysis (security-and-quality queries) |
| `quality.yml` | push to main, PR | black, flake8, isort, mypy, pytest, Docker build |
| `pr-review.yml` | PR to main | semantic PR title, security audit, secret scan, Docker build |

## 5. Manual Review Checklist

Before each release, a maintainer should:

- [ ] Review all open Dependabot PRs
- [ ] Run `bandit -r backend/app/` and review findings
- [ ] Run `safety check` in `backend/` and update vulnerable dependencies
- [ ] Verify no secrets in committed files
- [ ] Confirm branch protection rules are active on GitHub
- [ ] Review `CODEOWNERS` for accuracy
- [ ] Check that `.env.example` has no real secrets

## 6. Reporting Security Issues

See [SECURITY.md](SECURITY.md) for the vulnerability reporting process.
