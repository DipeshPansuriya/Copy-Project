# Product Requirements Document (PRD)

## 1. Overview

**Product Name:** OpenClipboard  
**Version:** 1.0.0  
**Status:** Draft  
**Owner:** Product Engineering

## 2. Problem Statement

Users need to copy-paste text, images, and files between devices without signing up for accounts or using proprietary cloud services. Existing solutions like Online Clipboard offer temporary clipboard sharing but lack:

- File upload support beyond images
- Configurable expiry times
- Burn-after-read (one-shot) semantics
- Self-hosting with open-source blob storage
- Explicit data deletion guarantees

## 3. Goals

| Goal | Success Metric |
|------|----------------|
| Cross-device clipboard sharing via 12-character code | User can send on device A, retrieve on device B |
| Support text, images, and files | All three kinds upload and download successfully |
| Configurable expiry (30s–24h) | Content auto-deletes after TTL |
| One-shot / burn-after-read | Content deletes after first download |
| 100% open-source stack | No proprietary SaaS dependencies |
| Self-hostable via Docker | `docker compose up` works out of the box |

## 4. Non-Goals

- User accounts / authentication (v1)
- End-to-end encryption (v1; code is the capability)
- File editing or versioning
- Public gallery or search
- Mobile native apps (v1; responsive web only)

## 5. User Stories

### As a sender, I want to…
1. Paste text and get a 12-character code
2. Drop an image or file and get a 12-character code
3. Choose how long the content lives (30s to 24h)
4. Enable burn-after-read so content deletes after first download
5. Copy a shareable link containing the code

### As a receiver, I want to…
1. Enter a 12-character code on any device
2. View text inline, preview images, download files
3. See a countdown to expiry
4. Delete content immediately if I am the sender

### As a self-hoster, I want to…
1. Run with `docker compose up`
2. Choose local disk or MinIO blob storage
3. Configure TTL, upload size, and rate limits via env vars
4. See active item count and storage usage

## 6. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | POST `/api/send` accepts text, image, or file | P0 |
| FR-02 | Returns a unique 12-character alphanumeric code | P0 |
| FR-03 | GET `/api/retrieve/{code}` returns metadata and content | P0 |
| FR-04 | GET `/api/file/{code}` streams the blob | P0 |
| FR-05 | DELETE `/api/item/{code}` removes content immediately | P0 |
| FR-06 | Content expires after configurable TTL | P0 |
| FR-07 | One-shot items delete after first download | P0 |
| FR-08 | Background purge worker sweeps expired items | P0 |
| FR-09 | File uploads verified by magic bytes, not client headers | P1 |
| FR-10 | Executable file types rejected | P1 |

## 7. Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Max upload size | 50 MB (configurable) |
| NFR-02 | TTL range | 30s – 24h |
| NFR-03 | Purge interval | 30s (configurable) |
| NFR-04 | Rate limit: send | 20/min per IP |
| NFR-05 | Rate limit: retrieve/file | 30/min per IP |
| NFR-06 | Rate limit: delete | 10/min per IP |
| NFR-07 | Response time (send/retrieve) | < 200ms p95 |
| NFR-08 | Concurrent users | 100+ (single instance) |

## 8. Out of Scope

- User registration/login
- Password-protected clips
- Email/SMS delivery of codes
- End-to-end encryption
- CLI client
- Mobile apps

## 9. Future Considerations

- Optional JWT auth for sender-owned delete
- AES-256 encryption at rest with customer-managed keys
- Webhook notifications on expiry
- CLI client (`ocp send`, `ocp get`)

---

*Last updated: 2026-11-24*
