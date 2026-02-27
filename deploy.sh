#!/bin/bash
# =============================================================================
# Tulpin Shop - Production Deployment Script
# =============================================================================
# Использование:
#   ./deploy.sh              - полное развёртывание
#   ./deploy.sh --ssl-only   - только SSL настройка
#   ./deploy.sh --status     - показать статус
#   ./deploy.sh --help       - эта справка
# =============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Переменные
PROJECT_ROOT="/root/tlpn_shop"
DOMAIN="tlpn.shop"
STATIC_ROOT="/var/www/tlpn_shop/static"
MEDIA_ROOT="/var/www/tlpn_shop/media"
EMAIL="admin@$DOMAIN"

info() { echo -e "${BLUE}>>> $1${NC}"; }
success() { echo -e "${GREEN}✓ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }

# Проверка root прав
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Требуется запуск от root! Используйте: sudo ./deploy.sh"
        exit 1
    fi
}

# Обновление системы и установка зависимостей
setup_system() {
    info "Обновление системы..."
    apt-get update -qq
    apt-get upgrade -y -qq

    info "Установка системных зависимостей..."
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

    success "Системные зависимости установлены"
}

# Создание директорий для статики и медиа
setup_static_dirs() {
    info "Создание директорий для статики и медиа..."
    
    mkdir -p "$STATIC_ROOT"
    mkdir -p "$MEDIA_ROOT"
    
    # Даем права www-data для nginx
    chown -R www-data:www-data /var/www/tlpn_shop
    chmod -R 755 /var/www/tlpn_shop
    
    success "Директории созданы"
}

# Развёртывание проекта
deploy_project() {
    info "Развёртывание проекта..."

    cd "$PROJECT_ROOT"

    # Создание venv если нет
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        success "Виртуальное окружение создано"
    fi

    # Активация и установка зависимостей
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install gunicorn
    success "Python зависимости установлены"

    # Сбор статики в правильную директорию (через переменные окружения)
    info "Сбор статических файлов..."
    export STATIC_ROOT="$STATIC_ROOT"
    export MEDIA_ROOT="$MEDIA_ROOT"
    python manage.py collectstatic --noinput
    success "Статические файлы собраны"

    # Копирование медиа файлов (если есть)
    if [ -d "$PROJECT_ROOT/media" ] && [ "$(ls -A $PROJECT_ROOT/media 2>/dev/null)" ]; then
        info "Копирование медиа файлов..."
        cp -r "$PROJECT_ROOT/media/"* "$MEDIA_ROOT/"
        chown -R www-data:www-data "$MEDIA_ROOT"
        success "Медиа файлы скопированы"
    fi

    # Миграции
    python manage.py migrate
    success "Миграции применены"

    # Создание суперпользователя
    python manage.py shell < create_superuser.py

    # Тестовые данные (опционально)
    if [ -f create_test_data.py ]; then
        python manage.py shell < create_test_data.py
        success "Тестовые данные созданы"
    fi
}

# Настройка Gunicorn systemd сервиса
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
    --bind unix:$PROJECT_ROOT/tulpin_shop.sock \\
    config.wsgi:application

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable tulpin_shop
    systemctl start tulpin_shop
    
    success "Gunicorn сервис настроен и запущен"
}

# Настройка Nginx
setup_nginx() {
    info "Настройка Nginx..."

    # Создаём конфиг с правильными путями
    cat > /etc/nginx/sites-available/tlpn_shop <<EOF
upstream django_app {
    server unix:$PROJECT_ROOT/tulpin_shop.sock fail_timeout=0;
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

    # Создаём симлинк
    ln -sf /etc/nginx/sites-available/tlpn_shop /etc/nginx/sites-enabled/tlpn_shop
    rm -f /etc/nginx/sites-enabled/default

    # Проверка и перезапуск
    if nginx -t; then
        systemctl reload nginx
        success "Nginx настроен"
    else
        error "Ошибка конфигурации Nginx!"
        exit 1
    fi
}

# Проверка и получение SSL сертификата
get_ssl() {
    info "Проверка SSL сертификата..."

    # Создаём директорию для challenge
    mkdir -p /var/www/certbot

    # Проверяем, существует ли сертификат
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        # Проверяем, не истекает ли сертификат (менее 30 дней)
        if certbot certificates 2>/dev/null | grep -q "$DOMAIN"; then
            EXPIRY=$(certbot certificates 2>/dev/null | grep "$DOMAIN" | awk '{print $NF}')
            info "SSL сертификат уже существует (действует до: $EXPIRY)"
            success "SSL сертификат найден"
            return 0
        fi
    fi

    info "Получение SSL сертификата..."
    
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
        systemctl reload nginx
    else
        error "Не удалось получить SSL сертификат"
        exit 1
    fi
}

# Настройка автообновления SSL
setup_ssl_renew() {
    info "Настройка автообновления SSL..."
    systemctl enable certbot.timer
    systemctl start certbot.timer
    success "Автообновление SSL настроено"
}

# Показать статус
show_status() {
    echo ""
    echo "================================================="
    echo "         TULPIN SHOP - Deployment Status"
    echo "================================================="
    echo ""
    echo "Домен: https://$DOMAIN"
    echo ""
    systemctl status tulpin_shop --no-pager -l || true
    echo ""
    systemctl status nginx --no-pager -l || true
    echo ""
    echo "Логи:"
    echo "  - Gunicorn: journalctl -u tulpin_shop -f"
    echo "  - Nginx: tail -f /var/log/nginx/tlpn_shop_error.log"
    echo ""
}

# Помощь
show_help() {
    echo "Tulpin Shop - Production Deployment"
    echo ""
    echo "Использование:"
    echo "  ./deploy.sh              - полное развёртывание"
    echo "  ./deploy.sh --ssl-only   - только SSL настройка"
    echo "  ./deploy.sh --status     - показать статус"
    echo "  ./deploy.sh --help       - эта справка"
    echo ""
}

# =============================================================================
# Основная логика
# =============================================================================

main() {
    echo ""
    echo "================================================="
    echo "    TULPIN SHOP - Production Deployment"
    echo "================================================="
    echo ""

    check_root

    case "${1:-}" in
        --ssl-only)
            setup_nginx
            get_ssl
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
            setup_nginx
            get_ssl
            setup_ssl_renew
            show_status
            ;;
        *)
            error "Неизвестная опция: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
