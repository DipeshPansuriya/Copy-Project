# 04-wf-audit-trail.md

# Workflow: Audit Trail

## 1. Current State (v1)

OpenClipboard v1 does **not** maintain an audit trail. The following actions are not logged with user identity:

| Action | Logged? | Details |
|--------|---------|---------|
| Send content | Partially | IP address in access logs, no user ID |
| Retrieve content | Partially | IP address in access logs, no user ID |
| Download file | Partially | Download count incremented, no user ID |
| Delete content | Partially | IP address in access logs, no user ID |
| Expire content | Partially | Purge worker logs code and kind |

## 2. What IS Logged

### Server Access Logs
```
INFO: 192.168.65.1:PORT - "POST /api/send HTTP/1.1" 200 OK
INFO: 192.168.65.1:PORT - "GET /api/retrieve/123456 HTTP/1.1" 200 OK
INFO: 192.168.65.1:PORT - "DELETE /api/item/123456 HTTP/1.1" 204 No Content
```

### Purge Logs
```
INFO openclip.purge: purged item 123456 (image, 58 bytes)
```

### Rate Limit Logs
```
WARNING slowapi: ratelimit 20 per 1 minute (192.168.65.1) exceeded at endpoint: /api/send
```

## 3. What is NOT Logged (v1)

- User identity (no accounts)
- Who retrieved a specific code
- Who deleted a specific code
- Timestamp of retrieval (only `downloads` count and `retrieved_at` for one-shot)
- Geographic location
- User agent

## 4. Future Audit Trail (v2)

If an audit trail is required:

### New Table: `audit_log`

```sql
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,          -- send, retrieve, download, delete, expire
    code TEXT NOT NULL,
    actor_ip TEXT,                 -- IP address
    actor_id TEXT,                 -- User ID (if auth added)
    timestamp REAL NOT NULL,
    details TEXT                   -- JSON metadata
);

CREATE INDEX IF NOT EXISTS idx_audit_code ON audit_log (code);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log (timestamp);
```

### Audit Events

| Event | Trigger | Fields |
|-------|---------|--------|
| `clip.send` | POST /api/send | code, kind, size, ttl, actor_ip |
| `clip.retrieve` | GET /api/retrieve/{code} | code, actor_ip |
| `clip.download` | GET /api/file/{code} | code, actor_ip |
| `clip.delete` | DELETE /api/item/{code} | code, actor_ip |
| `clip.expire` | Purge worker | code, reason (ttl/one-shot) |

### Retention

- Audit logs retained for 90 days (configurable)
- Older logs purged by background job

## 4. Privacy Considerations

- IP addresses are personal data in some jurisdictions
- Consider hashing IPs before storage
- Provide data deletion on request (GDPR right to erasure)
- Audit logs should not contain clipboard content (only metadata)

## 5. Compliance

| Regulation | Requirement | Current Status |
|------------|-------------|----------------|
| GDPR | Right to erasure | Manual delete via API |
| GDPR | Data minimization | Ephemeral by design (TTL) |
| SOC2 | Audit logging | Not implemented (v1) |
| HIPAA | Access controls | Not suitable (v1) |
