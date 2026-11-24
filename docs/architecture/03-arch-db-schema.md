# 03-arch-db-schema.md

# Database Schema

## 1. Overview

SQLite stores metadata only. Blobs live in separate object storage (local disk or MinIO).

## 2. Table: `items`

```sql
CREATE TABLE IF NOT EXISTS items (
    code         TEXT PRIMARY KEY,
    kind         TEXT NOT NULL,
    filename     TEXT,
    content_type TEXT,
    size         INTEGER NOT NULL,
    object_key   TEXT NOT NULL,
    created_at   REAL NOT NULL,
    expires_at   REAL NOT NULL,
    one_shot     INTEGER NOT NULL DEFAULT 0,
    retrieved_at REAL,
    downloads    INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_items_expires ON items (expires_at);
```

## 3. Column Reference

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `code` | TEXT | NO | PK. 6-digit retrieval code |
| `kind` | TEXT | NO | `text` \| `image` \| `file` |
| `filename` | TEXT | YES | Sanitized original filename |
| `content_type` | TEXT | YES | MIME type (magic-verified) |
| `size` | INTEGER | NO | Blob size in bytes |
| `object_key` | TEXT | NO | UUID-based storage key |
| `created_at` | REAL | NO | Creation timestamp (epoch) |
| `expires_at` | REAL | NO | Expiration timestamp (epoch) |
| `one_shot` | INTEGER | NO | 0 = false, 1 = true |
| `retrieved_at` | REAL | YES | First download timestamp |
| `downloads` | INTEGER | NO | Download counter |

## 4. Indexes

| Index | Columns | Purpose |
|-------|---------|---------|
| Primary Key | `code` | Fast lookup by retrieval code |
| `idx_items_expires` | `expires_at` | Efficient purge sweep |

## 5. Sample Row

```json
{
  "code": "123456",
  "kind": "image",
  "filename": "screenshot.png",
  "content_type": "image/png",
  "size": 58,
  "object_key": "a1b2c3d4/e5f6g7h8",
  "created_at": 1795517030.729,
  "expires_at": 1795517930.729,
  "one_shot": 1,
  "retrieved_at": null,
  "downloads": 0
}
```

## 6. Purge Query

```sql
SELECT * FROM items
WHERE expires_at < ?
   OR (one_shot = 1 AND retrieved_at IS NOT NULL)
```

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
├── clipboard.db
└── blobs/
    ├── {uuid1}/{uuid2}
    └── {uuid3}/{uuid4}
```

### MinIO
```
Bucket: clipboard
Objects: {uuid1}/{uuid2}, {uuid3}/{uuid4}, ...
```

## 9. Future Extensions

| Addition | Reason |
|----------|--------|
| `audit_log` table | Track who retrieved/deleted what |
| `users` table | Optional authentication |
| `clip_password_hash` | Password-protected clips |
