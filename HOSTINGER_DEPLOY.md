# Hostinger Deployment Guide — OpenClipboard

## ⚠️ Important: Choose the Right Plan

| Hostinger Plan | Suitable? | Reason |
|---------------|-----------|--------|
| **Shared Hosting** | ❌ No | No Docker, no Python app support, no port 8000 access |
| **VPS Hosting** | ✅ Yes | Full root access, install Docker, Python, Nginx |
| **Cloud Hosting** | ✅ Yes | Same as VPS, better scalability |
| **KVM Hosting** | ✅ Yes | Full virtualization, works well |

**Recommended:** Hostinger VPS (KVM 2 or higher) — at least 2GB RAM, 1 vCPU, 40GB SSD.

---

## Step 1: Connect to Your Hostinger VPS

```bash
# SSH into your VPS (replace with your IP and username)
ssh root@your-vps-ip-address

# Update system
apt update && apt upgrade -y

# Install essential tools
apt install -y curl wget git vim ufw fail2ban
```

---

## Step 2: Install Docker & Docker Compose

```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Add your user to docker group
usermod -aG docker $USER
newgrp docker

# Install Docker Compose plugin (included in modern Docker)
docker --version
docker compose version

# Enable Docker on boot
systemctl enable docker
systemctl start docker
```

---

## Step 3: Upload Project to VPS

```bash
# On your LOCAL machine, copy project to VPS
scp -r "/Users/dipesh/Desktop/Dipesh/Project/Copy Project" root@your-vps-ip:~/openclipboard

# OR on VPS, clone from Git
git clone <your-repo-url> openclipboard
cd openclipboard
```

---

## Step 4: Configure Environment for Production

Create `.env` file on the VPS:

```bash
cd ~/openclipboard
nano .env
```

```env
# Core
APP_NAME=OpenClipboard
CLIP_STORAGE=local          # or minio
CLIP_DATA_DIR=/app/data
CLIP_DB_BACKEND=sqlite      # or postgres

# Limits
CLIP_MAX_UPLOAD_MB=100      # Increase for larger files
CLIP_MIN_TTL=30
CLIP_DEFAULT_TTL=900
CLIP_MAX_TTL=86400
CLIP_PURGE_INTERVAL=30

# Security — CHANGE THESE!
CLIP_ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CLIP_CORS_ORIGINS=https://yourdomain.com
CLIP_RATE_LIMIT_SEND=20/minute
CLIP_RATE_LIMIT_RETRIEVE=30/minute
CLIP_RATE_LIMIT_FILE=30/minute
CLIP_RATE_LIMIT_DELETE=10/minute
CLIP_MAX_FAILED_ATTEMPTS=5
CLIP_LOCKOUT_SECONDS=300
CLIP_PASSWORD_PROTECTION=true

# Admin — CHANGE THESE!
CLIP_ADMIN_ENABLED=true
CLIP_ADMIN_USERNAME=admin
CLIP_ADMIN_PASSWORD=ChangeThisToAStrongPassword123!

# Redis (optional, for caching in multi-instance)
# REDIS_URL=redis://localhost:6379/0
```

---

## Step 5: Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
services:
  app:
    build: ./backend
    container_name: openclipboard-app
    restart: unless-stopped
    ports:
      - "127.0.0.1:8000:8000"  # Only localhost, Nginx will proxy
    volumes:
      - clip-data:/data
    env_file:
      - .env
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Redis for shared caching (multi-instance)
  # redis:
  #   image: redis:7-alpine
  #   container_name: openclipboard-redis
  #   restart: unless-stopped
  #   command: redis-server --appendonly yes
  #   volumes:
  #     - clip-redis:/data

volumes:
  clip-data:
  # clip-redis:
```

---

## Step 6: Set Up Nginx Reverse Proxy with SSL

```bash
# Install Nginx and Certbot
apt install -y nginx certbot python3-certbot-nginx

# Create Nginx config
nano /etc/nginx/sites-available/openclipboard
```

```nginx
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    # SSL certificates (Certbot will fill these)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header Referrer-Policy no-referrer;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    # Upload size limit
    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable the site
ln -s /etc/nginx/sites-available/openclipboard /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Test Nginx config
nginx -t

# Start Nginx
systemctl enable nginx
systemctl start nginx

# Get SSL certificate
certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

---

## Step 7: Start OpenClipboard

```bash
cd ~/openclipboard

# Build and start
docker compose -f docker-compose.prod.yml up --build -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f app
```

---

## Step 8: Configure Firewall

```bash
# Enable UFW
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp      # SSH
ufw allow 80/tcp      # HTTP
ufw allow 443/tcp     # HTTPS
ufw enable

# Check status
ufw status
```

---

## Step 9: Set Up DNS

In your domain registrar (or Hostinger DNS zone):

| Record | Type | Value | TTL |
|--------|------|-------|-----|
| `@` | A | Your-VPS-IP | 3600 |
| `www` | A | Your-VPS-IP | 3600 |

---

## Step 10: Auto-Restart on Reboot

```bash
# Docker Compose already has restart: unless-stopped
# Enable Docker and Nginx on boot
systemctl enable docker
systemctl enable nginx

# Create a simple systemd service for Docker Compose (optional)
nano /etc/systemd/system/openclipboard.service
```

```ini
[Unit]
Description=OpenClipboard Docker Compose
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/root/openclipboard
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down

[Install]
WantedBy=multi-user.target
```

```bash
systemctl enable openclipboard.service
```

---

## Step 11: Access Your App

| Service | URL |
|---------|-----|
| OpenClipboard UI | `https://yourdomain.com` |
| Health Check | `https://yourdomain.com/health` |
| API Docs | `https://yourdomain.com/api/docs` |
| Admin Login | `https://yourdomain.com/admin/login` |

---

## 📊 Performance Tuning for Large Files

If you expect large file uploads, adjust these:

| Setting | Value | Where |
|---------|-------|-------|
| `CLIP_MAX_UPLOAD_MB` | 500 (or higher) | `.env` |
| Nginx `client_max_body_size` | 500M | Nginx config |
| Nginx `proxy_read_timeout` | 300s | Nginx config |
| Docker memory limit | 2GB+ | Docker Compose / VPS plan |

---

## 🔒 Security Checklist

- [ ] Change default admin password (`CLIP_ADMIN_PASSWORD`)
- [ ] Change `CLIP_ALLOWED_HOSTS` to your domain only
- [ ] Change `CLIP_CORS_ORIGINS` to your HTTPS domain
- [ ] Enable SSL/TLS (Certbot)
- [ ] Configure firewall (UFW)
- [ ] Set up fail2ban for SSH protection
- [ ] Regular backups of `clip-data` volume
- [ ] Monitor logs: `docker compose logs app`

---

## 🧹 Maintenance Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml logs -f app --tail=100

# Restart app
docker compose -f docker-compose.prod.yml restart app

# Update app
git pull
docker compose -f docker-compose.prod.yml up --build -d

# Backup data
docker run --rm --volumes-from openclipboard-app -v $(pwd):/backup alpine tar czf /backup/clipboard-backup.tar.gz /data

# Check disk space
df -h

# Check Docker container resources
docker stats
```

---

## 🆘 Troubleshooting

| Issue | Solution |
|-------|----------|
| Site not loading | Check `docker compose ps`, `ufw status`, Nginx config |
| 502 Bad Gateway | App container not running, check `docker compose logs app` |
| SSL errors | Run `certbot renew --dry-run` to test |
| Large upload fails | Increase `client_max_body_size` and `CLIP_MAX_UPLOAD_MB` |
| Rate limiting too strict | Adjust `CLIP_RATE_LIMIT_*` in `.env` |

---

## 💰 Estimated Hostinger VPS Cost

| Plan | RAM | CPU | SSD | Monthly | Suitable For |
|------|-----|-----|-----|---------|--------------|
| KVM 1 | 1 GB | 1 vCPU | 20 GB | ~$4-7/mo | Testing, light use |
| **KVM 2** | **2 GB** | **1 vCPU** | **40 GB** | **~$7-12/mo** | **Production (recommended)** |
| KVM 3 | 4 GB | 2 vCPU | 80 GB | ~$15-25/mo | High traffic, large files |

---

## ✅ You're Ready!

Your OpenClipboard app is now hosted on Hostinger VPS with:
- ✅ Docker containerization
- ✅ Nginx reverse proxy with SSL
- ✅ IP-wise rate limiting
- ✅ Streaming file uploads
- ✅ Caching (Redis-ready)
- ✅ Admin dashboard
- ✅ Auto-restart on reboot
- ✅ Firewall protection
