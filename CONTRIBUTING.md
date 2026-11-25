# Contributing to OpenClipboard

Thank you for considering a contribution to OpenClipboard! This document outlines
the process for contributing code, documentation, and security fixes.

## 1. Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## 2. How to Contribute

### Reporting Issues

- Search existing issues before creating a new one.
- Use the appropriate issue template (bug report, feature request, security issue).
- For security vulnerabilities, please email privately — do not open a public issue.

### Submitting Pull Requests

1. **Fork** the repository and create your branch from `main`.
2. **Name your branch** following the convention:
   - `feature/<description>` — new features
   - `fix/<description>` — bug fixes
   - `security/<description>` — security fixes
   - `docs/<description>` — documentation changes
3. **Implement your changes** and add/update tests.
4. **Run the pre-commit checks** locally:
   ```bash
   ./scripts/install_hooks.sh
   git commit -m "feat: your change"
   ```
5. **Ensure Docker builds**:
   ```bash
   docker build -t openclipboard:test ./backend
   docker compose up --build
   ```
6. **Open a pull request** against `main`. Describe what changed and how you tested it.
7. **Address review comments** until the PR is approved.

## 3. Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/):

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

## 4. Branch Protection

The `main` branch is protected:

- Pull requests required before merging
- At least 1 approving review required
- Status checks must pass
- Direct pushes to `main` are blocked

See [BRANCH-POLICY.md](docs/BRANCH-POLICY.md) for details.

## 5. Security

- Never commit `.env`, secrets, or credentials.
- Use `.env.example` as a template for environment variables.
- Report security issues privately — see [SECURITY.md](SECURITY.md).
- All secrets are scanned by pre-commit hooks and CI.

## 6. License

By contributing, you agree that your contributions will be licensed under the MIT
License.
