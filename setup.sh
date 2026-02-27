#!/bin/bash

# =============================================================================
# Tulpin Shop - Production Setup Script
# =============================================================================
# Использование:
#   ./setup.sh              - полная настройка
#   ./setup.sh --dev        - только локальный запуск (dev)
#   ./setup.sh --ssl-only   - только SSL
#   ./setup.sh --fonts      - только шрифты
# =============================================================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Переменные
DOMAIN="tlpn.shop"
EMAIL="admin@tlpn.shop"
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NGINX_CONF="/etc/nginx/sites-available/tlpn_shop"
NGINX_LINK="/etc/nginx/sites-enabled/tlpn_shop"

info() { echo -e "${BLUE}>>> $1${NC}"; }
success() { echo -e "${GREEN}✓ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }

# =============================================================================
# Проверки
# =============================================================================

check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Требуется запуск от root! Используйте: sudo ./setup.sh"
        exit 1
    fi
}

check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD=python3
    else
        error "Python3 не найден!"
        exit 1
    fi
    info "Python: $($PYTHON_CMD --version)"
}

check_domain() {
    info "Проверка домена $DOMAIN..."
    if ! dig +short $DOMAIN | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
        warning "Домен не разрешается или DNS не настроен"
        warning "Убедитесь, что A-запись $DOMAIN указывает на IP сервера"
        read -p "Продолжить? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "Домен настроен: $(dig +short $DOMAIN)"
    fi
}

# =============================================================================
# Системные зависимости
# =============================================================================

setup_system() {
    info "Обновление системы..."
    apt-get update -qq
    apt-get upgrade -y -qq
    
    info "Установка зависимостей..."
    apt-get install -y -qq \
        python3 python3-pip python3-venv python3-dev \
        build-essential curl git \
        nginx certbot python3-certbot-nginx
    
    success "Системные зависимости установлены"
}

# =============================================================================
# Проект
# =============================================================================

setup_project() {
    info "Настройка проекта..."
    cd "$PROJECT_ROOT"
    
    # Venv
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        success "Виртуальное окружение создано"
    fi
    
    source venv/bin/activate
    
    # Зависимости
    pip install --upgrade pip -q
    pip install -r requirements.txt -q
    pip install gunicorn -q
    success "Python зависимости установлены"
    
    # Миграции
    python manage.py migrate
    success "Миграции применены"
    
    # Суперпользователь
    python manage.py shell < create_superuser.py
    
    # Тестовые данные
    if [ -f create_test_data.py ]; then
        python manage.py shell < create_test_data.py
        success "Тестовые данные созданы"
    fi
    
    # Статика
    python manage.py collectstatic --noinput
    success "Статические файлы собраны"
}

# =============================================================================
# Шрифты
# =============================================================================

setup_fonts() {
    info "Configuring local fonts..."
    cd "$PROJECT_ROOT"

    mkdir -p static/fonts static/css

    # Google Fonts URLs
    curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hjp-Ek-_EeA.woff2" -o static/fonts/Inter-400.woff2
    curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuGKYMZ9hjp-Ek-_EeA.woff2" -o static/fonts/Inter-500.woff2
    curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuI6fMZ9hjp-Ek-_EeA.woff2" -o static/fonts/Inter-600.woff2
    curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuFuYMZ9hjp-Ek-_EeA.woff2" -o static/fonts/Inter-700.woff2
    curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuOKfMZ9hjp-Ek-_EeA.woff2" -o static/fonts/Inter-300.woff2

    cat > static/css/fonts.css <<'EOF'
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 300;
    font-display: swap;
    src: url('../fonts/Inter-300.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('../fonts/Inter-400.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 500;
    font-display: swap;
    src: url('../fonts/Inter-500.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url('../fonts/Inter-600.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 700;
    font-display: swap;
    src: url('../fonts/Inter-700.woff2') format('woff2');
}
EOF

    if ! grep -q "static 'css/fonts.css'" templates/base.html; then
        sed -i '/<head>/a\    <!-- Local Fonts -->\n    <link rel="stylesheet" href="{% static '\''css/fonts.css'\'' %}">' templates/base.html
        success "Template updated with local fonts"
    fi

    python manage.py collectstatic --noinput
    success "Local fonts configured"
}
# =============================================================================
# Gunicorn
# =============================================================================

setup_gunicorn() {
    info "Настройка Gunicorn сервиса..."
    
    cat > /etc/systemd/system/tulpin_shop.service <<EOF
[Unit]
Description=Tulpin Shop Gunicorn Daemon
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/venv/bin/gunicorn \\
    --access-logfile - \\
    --workers 3 \\
    --bind 0.0.0.0:8000 \\
    config.wsgi:application

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable tulpin_shop
    systemctl start tulpin_shop
    
    success "Gunicorn сервис настроен и запущен"
}

# =============================================================================
# SSL сертификат
# =============================================================================

setup_nginx_http() {
    info "Настройка Nginx (HTTP режим для SSL challenge)..."
    
    mkdir -p /etc/nginx/sites-available
    mkdir -p /etc/nginx/sites-enabled
    mkdir -p /var/www/certbot
    
    # Временный конфиг ТОЛЬКО для HTTP challenge
    cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    # ACME challenge для Let's Encrypt
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    # Всё остальное - заглушка
    location / {
        return 200 "Tulpin Shop - Setting up SSL...";
        add_header Content-Type text/plain;
    }
}
EOF
    
    ln -sf "$NGINX_CONF" "$NGINX_LINK"
    rm -f /etc/nginx/sites-enabled/default
    
    if nginx -t; then
        systemctl reload nginx
        success "Nginx настроен для SSL challenge"
    else
        error "Ошибка конфигурации Nginx!"
        exit 1
    fi
}

get_ssl() {
    info "Получение SSL сертификата..."
    info "  Домены: $DOMAIN, www.$DOMAIN"
    
    # Даём время на распространение DNS
    sleep 2
    
    certbot certonly \
        --webroot \
        -w /var/www/certbot \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --email $EMAIL \
        --agree-tos \
        --non-interactive \
        --force-renewal
    
    if [ $? -eq 0 ]; then
        success "SSL сертификат получен"
    else
        error "Не удалось получить SSL сертификат"
        error "Проверьте:"
        error "  1. DNS A-запись $DOMAIN → $(dig +short $DOMAIN | head -1)"
        error "  2. Порт 80 открыт: sudo ufw status | grep 80"
        error "  3. Nginx работает: sudo systemctl status nginx"
        exit 1
    fi
}

setup_ssl_renew() {
    info "Настройка автообновления SSL..."
    systemctl enable certbot.timer 2>/dev/null || true
    systemctl start certbot.timer 2>/dev/null || true
    success "Автообновление SSL настроено"
}

# =============================================================================
# Nginx
# =============================================================================

setup_nginx() {
    info "Настройка Nginx..."
    
    mkdir -p /etc/nginx/sites-available
    mkdir -p /etc/nginx/sites-enabled
    
    # Полный конфиг с SSL
    cat > "$NGINX_CONF" <<EOF
upstream django_app {
    server 0.0.0.0:8000;
}

server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
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
        alias $PROJECT_ROOT/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /media/ {
        alias $PROJECT_ROOT/media/;
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
    
    if nginx -t; then
        systemctl reload nginx
        success "Nginx настроен"
    else
        error "Ошибка конфигурации Nginx!"
        exit 1
    fi
}

# =============================================================================
# Production .env
# =============================================================================

create_env_production() {
    info "Создание .env.production..."
    
    cat > "$PROJECT_ROOT/.env.production" <<EOF
# Production settings for tlpn.shop
DEBUG=False
SECRET_KEY=$(openssl rand -base64 32)
ALLOWED_HOSTS=$DOMAIN,www.$DOMAIN,localhost,127.0.0.1

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_ID=your_admin_id_here

# WebApp URL (production)
TELEGRAM_WEBAPP_URL=https://$DOMAIN

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Security
SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=True
SECURE_HSTS_PRELOAD=True
EOF
    
    warning "Измените SECRET_KEY и TELEGRAM_BOT_TOKEN в .env.production"
    success ".env.production создан"
}

# =============================================================================
# Итоги
# =============================================================================

show_summary() {
    echo ""
    echo "================================================="
    echo "    TULPIN SHOP - Setup Complete!"
    echo "================================================="
    echo ""
    echo "Домен: https://$DOMAIN"
    echo ""
    echo "Сервисы:"
    systemctl status tulpin_shop --no-pager -l 2>/dev/null || true
    echo ""
    systemctl status nginx --no-pager -l 2>/dev/null || true
    echo ""
    echo "Доступ:"
    echo "  - Сайт: https://$DOMAIN"
    echo "  - Админка: https://$DOMAIN/admin"
    echo "  - Логин: trebla"
    echo "  - Пароль: KFCone1ove!12"
    echo ""
    echo "Команды:"
    echo "  sudo systemctl status tulpin_shop  - статус Gunicorn"
    echo "  sudo journalctl -u tulpin_shop -f  - логи Gunicorn"
    echo "  sudo nginx -t                       - проверить Nginx"
    echo "  sudo certbot certificates           - список SSL"
    echo ""
}

show_help() {
    echo "Tulpin Shop - Production Setup"
    echo ""
    echo "Использование:"
    echo "  sudo ./setup.sh           - полная настройка"
    echo "  sudo ./setup.sh --dev     - только локальный запуск"
    echo "  sudo ./setup.sh --ssl-only - только SSL"
    echo "  sudo ./setup.sh --fonts   - только шрифты"
    echo "  sudo ./setup.sh --help    - эта справка"
    echo ""
}

# =============================================================================
# Основная логика
# =============================================================================

main() {
    echo ""
    echo "================================================="
    echo "    TULPIN SHOP - Production Setup"
    echo "================================================="
    echo ""
    
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --dev)
            check_python
            setup_project
            info "Запуск dev сервера..."
            source venv/bin/activate
            python manage.py runserver 0.0.0.0:8000
            ;;
        --ssl-only)
            check_root
            check_domain
            setup_nginx_http    # Сначала HTTP конфиг для challenge
            get_ssl             # Получаем SSL
            setup_ssl_renew
            setup_nginx         # Потом полный конфиг с SSL
            show_summary
            ;;
        --fonts)
            check_python
            setup_fonts
            success "Шрифты настроены"
            exit 0
            ;;
        "")
            check_root
            check_python
            check_domain
            setup_system
            setup_project
            setup_fonts
            setup_gunicorn
            setup_nginx_http    # Сначала HTTP конфиг для challenge
            get_ssl             # Получаем SSL
            setup_ssl_renew
            setup_nginx         # Потом полный конфиг с SSL
            create_env_production
            show_summary
            ;;
        *)
            error "Неизвестная опция: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"

