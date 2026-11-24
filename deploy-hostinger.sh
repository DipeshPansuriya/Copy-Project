#!/bin/bash
# OpenClipboard — Hostinger VPS Quick Deploy Script
# Run this on your VPS as root: bash deploy-hostinger.sh

set -e

echo "========================================="
echo "  OpenClipboard — Hostinger VPS Deploy"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}Please run as root (use sudo)${NC}"
    exit 1
fi

# Get domain name
read -p "Enter your domain (e.g., clip.yourdomain.com): " DOMAIN
if [ -z "$DOMAIN" ]; then
    echo -e "${RED}Domain is required!${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Domain: $DOMAIN${NC}"

# 1. Update system
echo -e "\n${YELLOW}[1/8] Updating system...${NC}"
apt update && apt upgrade -y

# 2. Install essential tools
echo -e "\n${YELLOW}[2/8] Installing essential tools...${NC}"
apt install -y curl wget git vim ufw fail2ban

# 3. Install Docker
echo -e "\n${YELLOW}[3/8] Installing Docker...${NC}"
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    usermod -aG docker $USER
    rm get-docker.sh
fi
systemctl enable docker
systemctl start docker

# 4. Install Nginx + Certbot
echo -e "\n${YELLOW}[4/8] Installing Nginx + Certbot...${NC}"
apt install -y nginx certbot python3-certbot-nginx

# 5. Copy project files (assumes project is already in ~/openclipboard)
echo -e "\n${YELLOW}[5/8] Setting up project...${NC}"
if [ ! -d ~/openclipboard ]; then
    echo -e "${RED}Project not found at ~/openclipboard${NC}"
    echo "Please upload your project files first:"
    echo "  scp -r /path/to/Copy\ Project root@your-vps:~/openclipboard"
    exit 1
fi
cd ~/openclipboard

# 6. Configure .env
echo -e "\n${YELLOW}[6/8] Configuring environment...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
fi
# Replace domain placeholders
sed -i "s/yourdomain.com/$DOMAIN/g" .env
sed -i "s/ChangeThisToAStrongPassword123!/$(openssl rand -base64 12)/g" .env
echo -e "${GREEN}✓ .env configured${NC}"

# 7. Configure Nginx
echo -e "\n${YELLOW}[7/8] Configuring Nginx with SSL...${NC}"
cat > /etc/nginx/sites-available/openclipboard << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;
    return 301 https://\$server_name\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header Referrer-Policy no-referrer;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/s;
    limit_req zone=api_limit burst=20 nodelay;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINXEOF

ln -sf /etc/nginx/sites-available/openclipboard /etc/nginx/sites-enabled/openclipboard
rm -f /etc/nginx/sites-enabled/default

# Test and start Nginx
nginx -t
systemctl enable nginx
systemctl start nginx

# Get SSL certificate
certbot --nginx -d $DOMAIN -d www.$DOMAIN --non-interactive --agree-tos -m admin@$DOMAIN

# 8. Start OpenClipboard
echo -e "\n${YELLOW}[8/8] Starting OpenClipboard...${NC}"
docker compose -f docker-compose.prod.yml up --build -d

# Configure firewall
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

echo -e "\n========================================="
echo -e "${GREEN}✓ Deployment Complete!${NC}"
echo "========================================="
echo ""
echo -e "OpenClipboard UI:  ${GREEN}https://$DOMAIN${NC}"
echo -e "Health Check:      ${GREEN}https://$DOMAIN/health${NC}"
echo -e "API Docs:          ${GREEN}https://$DOMAIN/api/docs${NC}"
echo -e "Admin Login:       ${GREEN}https://$DOMAIN/admin/login${NC}"
echo ""
echo -e "${YELLOW}Admin credentials:${NC}"
echo -e "  Username: admin"
echo -e "  Password: Check .env file (CLIP_ADMIN_PASSWORD)"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Point your domain DNS to this VPS IP"
echo "  2. Change admin password in .env"
echo "  3. Monitor logs: docker compose -f docker-compose.prod.yml logs -f app"
echo "========================================="
