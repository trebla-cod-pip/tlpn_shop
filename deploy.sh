#!/bin/bash
# =============================================================================
# Tulpin Shop - Production Deployment Script
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOMAIN="tlpn.shop"
EMAIL="admin@$DOMAIN"
STATIC_ROOT="/var/www/tlpn_shop/static"
MEDIA_ROOT="/var/www/tlpn_shop/media"
CERTBOT_ROOT="/var/www/certbot"
SOCKET_DIR="/run/tulpin_shop"
SOCKET_PATH="$SOCKET_DIR/tulpin_shop.sock"
NGINX_CONF="/etc/nginx/sites-available/tlpn_shop"
NGINX_LINK="/etc/nginx/sites-enabled/tlpn_shop"
APP_USER="www-data"
APP_GROUP="www-data"

info() { echo -e "${BLUE}>>> $1${NC}"; }
success() { echo -e "${GREEN}OK: $1${NC}"; }
warning() { echo -e "${YELLOW}WARN: $1${NC}"; }
error() { echo -e "${RED}ERROR: $1${NC}"; }

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Run as root: sudo ./deploy.sh"
        exit 1
    fi
}

check_project_root() {
    if [ ! -f "$PROJECT_ROOT/manage.py" ]; then
        error "manage.py not found in $PROJECT_ROOT"
        error "Run deploy.sh from the project directory"
        exit 1
    fi

    # /root is usually not traversable by www-data, so fallback to root gunicorn.
    if [[ "$PROJECT_ROOT" == /root/* ]]; then
        warning "PROJECT_ROOT is under /root, Gunicorn will run as root"
        warning "Recommended project path: /opt/tlpn_shop"
        APP_USER="root"
        APP_GROUP="www-data"
    fi
}

setup_system() {
    info "Installing system dependencies..."
    apt-get update -qq
    apt-get upgrade -y -qq
    apt-get install -y -qq \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        build-essential \
        libpq-dev \
        curl \
        git \
        nginx \
        certbot \
        python3-certbot-nginx
    success "System dependencies installed"
}

setup_static_dirs() {
    info "Preparing static/media directories..."
    mkdir -p "$STATIC_ROOT" "$MEDIA_ROOT"
    chown -R www-data:www-data /var/www/tlpn_shop
    chmod -R 755 /var/www/tlpn_shop
    success "Static/media directories are ready"
}

deploy_project() {
    info "Deploying project..."
    cd "$PROJECT_ROOT"

    if [ ! -d "venv" ]; then
        python3 -m venv venv
        success "Virtualenv created"
    fi

    # shellcheck disable=SC1091
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn

    export STATIC_ROOT="$STATIC_ROOT"
    export MEDIA_ROOT="$MEDIA_ROOT"

    python manage.py collectstatic --noinput
    python manage.py migrate

    if [ -f create_superuser.py ]; then
        python manage.py shell < create_superuser.py
    fi

    if [ -f create_test_data.py ]; then
        python manage.py shell < create_test_data.py
    fi

    if [ -d "$PROJECT_ROOT/media" ] && [ "$(ls -A "$PROJECT_ROOT/media" 2>/dev/null)" ]; then
        cp -r "$PROJECT_ROOT/media/"* "$MEDIA_ROOT/"
        chown -R www-data:www-data "$MEDIA_ROOT"
    fi

    success "Project deployed"
}

setup_gunicorn() {
    info "Configuring Gunicorn service..."

    mkdir -p "$SOCKET_DIR"
    chown "$APP_USER:$APP_GROUP" "$SOCKET_DIR"
    chmod 755 "$SOCKET_DIR"
    rm -f "$SOCKET_PATH"

    cat > /etc/systemd/system/tulpin_shop.service <<EOF
[Unit]
Description=Tulpin Shop Gunicorn Daemon
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_GROUP
WorkingDirectory=$PROJECT_ROOT
RuntimeDirectory=tulpin_shop
RuntimeDirectoryMode=0755
UMask=0007
Environment=PYTHONUNBUFFERED=1
ExecStart=$PROJECT_ROOT/venv/bin/gunicorn \\
    --access-logfile - \\
    --workers 3 \\
    --bind unix:$SOCKET_PATH \\
    config.wsgi:application
ExecReload=/bin/kill -s HUP \$MAINPID
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable tulpin_shop
    systemctl restart tulpin_shop
    success "Gunicorn service configured"
}

setup_nginx_http() {
    info "Configuring Nginx HTTP (ACME challenge)..."

    mkdir -p /etc/nginx/sites-available /etc/nginx/sites-enabled "$CERTBOT_ROOT"

    cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root $CERTBOT_ROOT;
    }

    location / {
        return 200 "Tulpin Shop - setting up SSL";
        add_header Content-Type text/plain;
    }
}
EOF

    ln -sf "$NGINX_CONF" "$NGINX_LINK"
    rm -f /etc/nginx/sites-enabled/default

    nginx -t
    systemctl reload nginx
    success "Nginx HTTP config applied"
}

setup_nginx() {
    info "Configuring Nginx reverse proxy..."

    cat > "$NGINX_CONF" <<EOF
upstream django_app {
    server unix:$SOCKET_PATH fail_timeout=0;
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root $CERTBOT_ROOT;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN www.$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    add_header Strict-Transport-Security "max-age=63072000" always;

    access_log /var/log/nginx/tlpn_shop_access.log;
    error_log /var/log/nginx/tlpn_shop_error.log;

    client_max_body_size 100M;

    location /static/ {
        alias $STATIC_ROOT/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $MEDIA_ROOT/;
        expires 7d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://django_app;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$server_name;
        proxy_redirect off;

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        proxy_buffering off;
    }

    location /health/ {
        proxy_pass http://django_app;
        access_log off;
    }
}
EOF

    ln -sf "$NGINX_CONF" "$NGINX_LINK"
    rm -f /etc/nginx/sites-enabled/default

    nginx -t
    systemctl reload nginx
    success "Nginx reverse proxy configured"
}

get_ssl() {
    info "Ensuring SSL certificate..."
    mkdir -p "$CERTBOT_ROOT"

    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ] && certbot certificates 2>/dev/null | grep -q "$DOMAIN"; then
        success "SSL certificate already exists"
        return 0
    fi

    certbot certonly \
        --webroot \
        -w "$CERTBOT_ROOT" \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive \
        --force-renewal

    success "SSL certificate issued"
}

setup_ssl_renew() {
    info "Enabling SSL auto-renew..."
    systemctl enable certbot.timer
    systemctl start certbot.timer
    success "SSL auto-renew enabled"
}

show_status() {
    echo ""
    echo "================================================="
    echo "         TULPIN SHOP - Deployment Status"
    echo "================================================="
    echo ""
    echo "Domain: https://$DOMAIN"
    echo "Project root: $PROJECT_ROOT"
    echo "Gunicorn socket: $SOCKET_PATH"
    echo ""
    systemctl status tulpin_shop --no-pager -l || true
    echo ""
    systemctl status nginx --no-pager -l || true
    echo ""
    echo "Logs:"
    echo "  - Gunicorn: journalctl -u tulpin_shop -f"
    echo "  - Nginx: tail -f /var/log/nginx/tlpn_shop_error.log"
    echo ""
}

show_help() {
    echo "Tulpin Shop - Production Deployment"
    echo ""
    echo "Usage:"
    echo "  ./deploy.sh              - full deployment"
    echo "  ./deploy.sh --proxy-only - reconfigure gunicorn/nginx only"
    echo "  ./deploy.sh --ssl-only   - SSL and Nginx only"
    echo "  ./deploy.sh --status     - show service status"
    echo "  ./deploy.sh --help       - help"
    echo ""
}

main() {
    echo ""
    echo "================================================="
    echo "    TULPIN SHOP - Production Deployment"
    echo "================================================="
    echo ""

    check_root
    check_project_root

    case "${1:-}" in
        --proxy-only)
            setup_gunicorn
            setup_nginx_http
            get_ssl
            setup_nginx
            setup_ssl_renew
            show_status
            ;;
        --ssl-only)
            setup_nginx_http
            get_ssl
            setup_nginx
            setup_ssl_renew
            show_status
            ;;
        --status)
            show_status
            ;;
        --help|-h)
            show_help
            ;;
        "")
            setup_system
            setup_static_dirs
            deploy_project
            setup_gunicorn
            setup_nginx_http
            get_ssl
            setup_nginx
            setup_ssl_renew
            show_status
            ;;
        *)
            error "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
