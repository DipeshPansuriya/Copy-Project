# Debugging

## 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","app":"OpenClipboard","storage":"local"}`

## 2. Logs

### Docker
```bash
# All services
docker compose logs

# App only
docker compose logs app

# Follow logs in real-time
docker compose logs -f app
```

### Local (uvicorn)
Logs go to stdout/stderr. If run with `nohup`, check `/tmp/openclip.log` or your redirect target.

Log format:
```
2026-11-24 11:19:37,XXX INFO openclip: OpenClipboard ready (storage=local, ...)
INFO: 127.0.0.1:PORT - "POST /api/send HTTP/1.1" 200 OK
ERROR: Exception in ASGI application ...
```

## 3. Common Issues

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| `Connection refused` on `:8000` | App not running or wrong port | `docker compose ps`; check port mapping |
| Images not showing | MinIO not configured or port conflict | Check `CLIP_STORAGE`; verify Docker ports |
| `429 Too Many Requests` | Rate limit exceeded | Wait for window reset; adjust `CLIP_RATE_LIMIT_*` |
| `410 Gone` on retrieve | Code expired or one-shot consumed | Re-send content with new code |
| `400` on retrieve | Code not 12 characters | Enter exactly 6 numeric digits |
| Database locked | Multiple writers to SQLite | Single instance only; use MinIO for storage if scaling |

## 4. Database Inspection

```bash
# Local development
sqlite3 backend/data/clipboard.db "SELECT * FROM items;"

# Docker
docker compose exec app sqlite3 /data/clipboard.db "SELECT * FROM items;"
```

> SQLite CLI may not be installed in the container. Use `docker compose exec app python3 -c "import sqlite3; ..."` instead.

## 5. Storage Inspection

### Local Disk
```bash
ls -la backend/data/blobs/
```

### MinIO
- Console: `http://localhost:9001` (if enabled)
- Login: `minioadmin` / `minioadmin`

## 6. Purge Worker Debugging

Check that expired items are being removed:

```bash
# Check active count
curl http://localhost:8000/api/stats

# Look at logs for purge messages
docker compose logs app | grep purge
```

## 7. Python Debugging

Run locally with reload for development:

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

Set log level to DEBUG by modifying `logging.basicConfig` in `main.py`.

## 8. Frontend Debugging

- Open browser DevTools (F12)
- Check Network tab for failed API requests
- Check Console tab for JavaScript errors
- Verify CSP is not blocking inline scripts
