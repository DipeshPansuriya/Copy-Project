# Database Schema

## 1. Overview

OpenClipboard uses **SQLite** for metadata. The actual file blobs are stored separately in object storage (MinIO) or on local disk. SQLite tracks only small metadata rows needed for retrieval, accounting, and purging.

## 2. Schema

```sql
CREATE TABLE IF NOT EXISTS items (
    code         TEXT PRIMARY KEY,      -- 12-character retrieval code
    kind         TEXT NOT NULL,         -- 'text' | 'image' | 'file'
    filename     TEXT,                  -- Original filename (sanitized)
    content_type TEXT,                  -- MIME type (magic-verified)
    size         INTEGER NOT NULL,      -- Byte size
    object_key   TEXT NOT NULL,         -- UUID-based storage key
    created_at   REAL NOT NULL,         -- Unix timestamp (UTC)
    expires_at   REAL NOT NULL,         -- Unix timestamp (UTC)
    one_shot     INTEGER NOT NULL DEFAULT 0,  -- 0 = false, 1 = true
    retrieved_at REAL,                  -- NULL until first download
    downloads    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_items_expires ON items (expires_at);
```

## 3. Column Reference

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `code` | TEXT | NO | Primary key. 12-character alphanumeric code |
| `kind` | TEXT | NO | Entry type: `text`, `image`, `file` |
| `filename` | TEXT | YES | Original filename (basename only, URL-encoded) |
| `content_type` | TEXT | YES | MIME type verified by `python-magic` |
| `size` | INTEGER | NO | Blob size in bytes |
| `object_key` | TEXT | NO | Storage key: `{uuid}/{uuid}` |
| `created_at` | REAL | NO | Creation timestamp (epoch seconds) |
| `expires_at` | REAL | NO | Expiration timestamp (epoch seconds) |
| `one_shot` | INTEGER | NO | 0 = persistent until TTL, 1 = delete after first download |
| `retrieved_at` | REAL | YES | First download timestamp; NULL if never downloaded |
| `downloads` | INTEGER | NO | Download counter |

## 4. Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| `PRIMARY KEY` | `code` | Fast lookup by retrieval code |
| `idx_items_expires` | `expires_at` | Efficient purge sweep queries |

## 5. Data Lifecycle

```
CREATE (send)
    │
    ▼
ACTIVE (within TTL)
    │
    ├─▶ RETRIEVED (one_shot → retrieved_at set)
    │       │
    │       ▼
    │   DELETED (after download stream completes)
    │
    ├─▶ EXPIRED (expires_at < now)
    │       │
    │       ▼
    │   DELETED (by purge worker or lazy purge)
    │
    └─▶ MANUALLY DELETED (DELETE /api/item/{code})
```

## 6. Purge Logic

The background purge worker (and lazy purge on retrieve) deletes rows where:

```sql
SELECT * FROM items
WHERE expires_at < ?
   OR (one_shot = 1 AND retrieved_at IS NOT NULL)
```

For each expired row:
1. Delete blob from storage using `object_key`
2. Delete metadata row from SQLite

## 7. Stats Query

```sql
SELECT COUNT(*) AS active, COALESCE(SUM(size), 0) AS bytes
FROM items
WHERE expires_at >= ?
```

## 8. File Storage Layout

### Local Disk
```
data/
├── clipboard.db          # SQLite metadata
└── blobs/
    ├── {uuid1}/{uuid2}   # File blob 1
    ├── {uuid3}/{uuid4}   # File blob 2
    └── ...
```

### MinIO
```
Bucket: clipboard
Objects: {uuid1}/{uuid2}, {uuid3}/{uuid4}, ...
```

## 9. Migration Strategy

SQLite is file-based. For future migrations:

- Add new columns with `ALTER TABLE ADD COLUMN`
- Create new tables for audit logs, auth, etc.
- Use `PRAGMA user_version` for schema versioning

No migration tool (e.g., Alembic, Liquibase) is included in v1 due to single-file simplicity.
