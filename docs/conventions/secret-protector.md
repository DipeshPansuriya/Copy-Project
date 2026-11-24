# Secret Protector

## 1. Purpose

OpenClipboard does not store user secrets (passwords, API keys, etc.) in v1. The only "secret" is the **6-digit retrieval code**, which acts as a capability token.

## 2. Code Handling

| Aspect | Implementation |
|--------|---------------|
| Generation | `secrets.randbelow(1_000_000)` — cryptographically random |
| Storage | Plaintext in SQLite (code is the lookup key) |
| Transmission | Plaintext over HTTP (use HTTPS in production via reverse proxy) |
| Display | Shown in UI after send; included in share link |
| Expiration | Hard-deleted after TTL or one-shot consumption |

## 3. Future Secret Protection (v2)

| Feature | Description |
|---------|-------------|
| At-rest encryption | AES-256 encryption of blob content with customer-managed keys |
| Code hashing | Store `SHA-256(code)` instead of plaintext code |
| Password-protected clips | User-supplied password encrypts content before storage |
| Key management | Integration with HashiCorp Vault, AWS KMS, or similar |

## 4. Environment Secrets

| Secret | Source | Protection |
|--------|--------|------------|
| MinIO credentials | `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY` | Env vars; rotate regularly |
| App secret key (future) | `CLIP_SECRET_KEY` | Env vars; never commit to git |

## 5. Do's and Don'ts

| Do | Don't |
|----|-------|
| Use HTTPS in production | Commit `.env` to git |
| Rotate MinIO credentials | Share codes publicly |
| Treat codes as passwords | Store sensitive PII in clips |
| Set short TTLs for sensitive content | Rely on v1 for regulated data |

## 6. Incident Response

If a code is compromised:

1. The recipient can retrieve/delete the content immediately
2. Delete the code via `DELETE /api/item/{code}` if you know it
3. Content auto-deletes after TTL regardless

## 7. Threats to Secrets

| Threat | Mitigation |
|--------|-----------|
| Code interception in transit | HTTPS via reverse proxy |
| Code brute force | Rate limiting (30/min on retrieve) |
| Code leakage in logs | Server logs contain URLs with codes; ensure log access is restricted |
| Database exposure | Codes are plaintext in SQLite; restrict file permissions |
