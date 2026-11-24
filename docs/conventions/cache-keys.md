# Cache Keys

OpenClipboard v1 does not use a distributed cache (no Redis/Memcached). Caching is handled as follows:

## 1. Browser Cache

All API responses include:

```
Cache-Control: no-store
```

This prevents browsers and intermediate proxies from caching sensitive clipboard content.

## 2. In-Memory Rate Limiter

`slowapi` maintains an in-memory counter per client IP. There are no persistent cache keys.

## 3. Frontend Cache Keys (Future)

If a frontend cache layer is added (e.g., for retrieve polling), suggested key format:

```
clipboard:item:{code}
clipboard:stats
clipboard:rate:{ip}:{endpoint}
```

## 4. CDN / Edge Cache

Not applicable in v1. All content is ephemeral and should not be cached at the edge.

## 5. SQLite WAL Mode

SQLite uses WAL (Write-Ahead Logging) for concurrent reads:

```
PRAGMA journal_mode=WAL;
```

This is an internal database setting, not an application cache key.
