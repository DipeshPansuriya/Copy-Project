# 02-deploy-cicd.md

# CI/CD

## 1. Current State (v1)

OpenClipboard v1 does not have an automated CI/CD pipeline. Deployment is manual:

```bash
# Build and deploy
docker compose up --build -d
```

## 2. Recommended CI/CD Pipeline (v2)

### GitHub Actions Workflow Example

```yaml
name: CI/CD

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install pytest pytest-asyncio httpx bandit safety
      - name: Run security scans
        run: |
          cd backend
          bandit -r app -f txt -o security-bandit.txt
          safety check --file requirements.txt
      - name: Run tests
        run: |
          cd backend
          pytest tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - name: Build Docker image
        run: docker compose build
      - name: Run Trivy scan
        run: trivy image copyproject-app:latest
      - name: Push to registry
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login -u "${{ secrets.REGISTRY_USER }}" --password-stdin
          docker tag copyproject-app:latest registry.example.com/openclipboard:latest
          docker push registry.example.com/openclipboard:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    steps:
      - name: Deploy to server
        run: |
          ssh user@server "cd /opt/openclipboard && docker compose pull && docker compose up -d"
```

## 3. Security Scanning in CI

| Tool | Purpose | When |
|------|---------|------|
| `bandit` | Python security issues | Every PR |
| `safety` / `pip audit` | Vulnerable dependencies | Every PR |
| `trivy` | Docker image vulnerabilities | Every build |
| `semgrep` | Custom security rules | Every PR |

## 4. Deployment Strategies

| Strategy | Description | Risk |
|----------|-------------|------|
| Rolling update | Replace one container at a time | Low |
| Blue-green | Switch traffic between two environments | Low |
| Recreate | Stop old, start new | Medium (downtime) |

Recommended: Rolling update with health check.

## 5. Rollback

```bash
# Rollback to previous image
docker compose pull openclipboard-app:previous-tag
docker compose up -d

# Or rollback compose file
git checkout previous-tag docker-compose.yml
docker compose up -d
```

## 6. Secrets in CI/CD

Never hardcode secrets. Use:

- GitHub Actions secrets (`MINIO_ROOT_PASSWORD`, etc.)
- Docker secrets
- HashiCorp Vault
- AWS Secrets Manager / GCP Secret Manager

## 7. Release Tags

```bash
git tag v1.0.1
git push origin v1.0.1
```

Tag triggers automated build and deploy (when CI/CD is implemented).
