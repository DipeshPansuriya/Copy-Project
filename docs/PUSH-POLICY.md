# Push Policy — OpenClipboard

This document defines the push permissions and restrictions enforced on the
OpenClipboard repository, modeled on
[DipeshPansuriya/MLX_Model_App](https://github.com/DipeshPansuriya/MLX_Model_App).

## 1. Direct Push Restrictions

| Branch | Who Can Push Directly | Notes |
|--------|----------------------|-------|
| `main` | No one (blocked) | All changes must go through a pull request |
| `develop` | Maintainers only | Still requires PR for production-ready changes |
| Feature branches | Author + maintainers | Force push allowed on own feature branches |

## 2. Pre-Push Checks

Before any push, the following checks are enforced via the pre-push Git hook
(`.githooks/pre-push`):

1. **Secret scanning** — `scripts/check_secrets.py --push` must pass
2. **Branch check** — Direct push to `main` is blocked
3. **Security audit** — `scripts/security_audit.sh --full` must pass

## 3. Pre-Commit Checks

Before any commit, the following checks are enforced via the pre-commit Git hook
(`.githooks/pre-commit`):

1. **Secret scan** on staged files
2. **.env exclusion** — `.env` files cannot be committed
3. **Security audit** — `scripts/security_audit.sh --quick`

## 4. Installing Hooks

```bash
./scripts/install_hooks.sh
```

This configures `core.hooksPath` to `.githooks` and makes all hooks executable.

## 5. Bypassing Protections

Bypasses are **not permitted**, including for repository administrators.
The `Do not allow bypassing the above settings` option is enabled on the
`main` branch protection rule.

## 6. Push Protection

GitHub push protection is enabled at the repository level. It scans pushes for
secrets (API keys, tokens, passwords) and blocks the push if any are found.
