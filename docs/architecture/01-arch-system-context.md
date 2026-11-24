# 01-arch-system-context.md

# System Context

## 1. Overview

OpenClipboard is a self-hosted, temporary clipboard-sharing service. Users send content from one device and retrieve it on another using a 6-digit code.

## 2. Actors

| Actor | Description |
|-------|-------------|
| **Sender** | User who uploads text, image, or file and receives a 6-digit code |
| **Receiver** | User who enters the 6-digit code on any device to view/download |
| **Operator** | Person who self-hosts the OpenClipboard instance |

## 3. External Systems

| System | Relationship |
|--------|--------------|
| **Web Browser** | Primary client for both sender and receiver |
| **Reverse Proxy** (optional) | TLS termination, rate limiting, WAF in production |
| **MinIO** (optional) | S3-compatible object storage for blobs |
| **Docker** | Container runtime for deployment |

## 4. Context Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNAL ENVIRONMENT                            │
│                                                                         │
│  ┌─────────────┐                    ┌─────────────┐                    │
│  │   Sender    │                    │   Receiver  │                    │
│  │  (Device A) │                    │  (Device B) │                    │
│  │  Web Browser│                    │  Web Browser│                    │
│  └──────┬──────┘                    └──────┬──────┘                    │
│         │  Enter text/file                  │  Enter 6-digit code       │
│         │  Get 6-digit code                 │  Get content              │
│         └───────────────────────────────────┘                           │
│                    Internet / Local Network                             │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    OPENCLIPBOARD (Self-Hosted)                          │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      FastAPI Application                         │   │
│  │  • Send / Retrieve / Download / Delete                           │   │
│  │  • Rate limiting                                                  │   │
│  │  • Security headers                                               │   │
│  │  • Purge worker (expiry)                                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                              │                                          │
│              ┌───────────────┼───────────────┐                          │
│              ▼               ▼               ▼                          │
│       ┌─────────┐      ┌───────────┐   ┌──────────────┐               │
│       │ SQLite  │      │ Local Disk│   │    MinIO     │               │
│       │ (metadata│      │   (blobs) │   │  (blobs,     │               │
│       │  only)   │      │  default  │   │   optional)  │               │
│       └─────────┘      └───────────┘   └──────────────┘               │
└─────────────────────────────────────────────────────────────────────────┘
```

## 5. Key Interactions

1. **Sender** → OpenClipboard: POST content → Get 6-digit code
2. **Receiver** → OpenClipboard: POST code → Get content
3. **OpenClipboard** → SQLite: Store/lookup metadata
4. **OpenClipboard** → Storage: Store/retrieve blobs
5. **OpenClipboard** → Purge Worker: Delete expired content

## 6. Boundaries

- **In scope:** Web UI, API, storage, purge, rate limiting
- **Out of scope:** User accounts, authentication, encryption, notifications, mobile apps
