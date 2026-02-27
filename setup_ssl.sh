#!/bin/bash

# =============================================================================
# Tulpin Shop - Настройка Nginx + SSL (Let's Encrypt)
# =============================================================================
# Использование:
#   ./setup_ssl.sh              - полная настройка
#   ./setup_ssl.sh --renew      - обновить SSL сертификаты
#   ./setup_ssl.sh --dry-run    - тестовый запуск (staging)
# =============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Переменные
DOMAIN="tlpn.shop"
EMAIL="admin@tlpn.shop"
PROJECT_ROOT="/root/tlpn_shop"
NGINX_CONF="/etc/nginx/sites-available/tlpn_shop"
NGINX_LINK="/etc/nginx/sites-enabled/tlpn_shop"

info() { echo -e "${BLUE}>>> $1${NC}"; }
success() { echo -e "${GREEN}✓ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }

# Проверка root прав
check_root() {
    if [ "$EUID" -ne 0 ]; then
        error "Требуется запуск от root! Используйте: sudo ./setup_ssl.sh"
        exit 1
    fi
}

# Проверка домена (DNS должен указывать на сервер)
check_domain() {
    info "Проверка домена $DOMAIN..."
    if ! dig +short $DOMAIN | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
        warning "Домен $DOMAIN не разрешается или DNS не настроен"
        warning "Убедитесь, что A-запись указывает на IP этого сервера"
        read -p "Продолжить? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        success "Домен настроен корректно"
    fi
}

# Установка Certbot
install_certbot() {
    if command -v certbot &> /dev/null; then
        success "Certbot уже установлен"
    else
        info "Установка Certbot..."
        apt-get update -qq
        apt-get install -y -qq certbot python3-certbot-nginx
        success "Certbot установлен"
    fi
}

# Установка Nginx
install_nginx() {
    if command -v nginx &> /dev/null; then
        success "Nginx уже установлен"
    else
        info "Установка Nginx..."
        apt-get update -qq
        apt-get install -y -qq nginx
        success "Nginx установлен"
        systemctl enable nginx
        systemctl start nginx
    fi
}

# Копирование конфигурации Nginx
setup_nginx_config() {
    info "Настройка конфигурации Nginx..."
    
    # Создаём директорию sites-available если нет
    mkdir -p /etc/nginx/sites-available
    mkdir -p /etc/nginx/sites-enabled
    
    # Копируем конфиг
    cp "$PROJECT_ROOT/nginx.conf" "$NGINX_CONF"
    
    # Обновляем путь к статике в конфиге
    sed -i "s|alias /root/tlpn_shop/staticfiles/|alias $PROJECT_ROOT/staticfiles/|g" "$NGINX_CONF"
    sed -i "s|alias /root/tlpn_shop/media/|alias $PROJECT_ROOT/media/|g" "$NGINX_CONF"
    
    # Создаём симлинк если нет
    if [ ! -L "$NGINX_LINK" ]; then
        ln -sf "$NGINX_CONF" "$NGINX_LINK"
        success "Конфигурация Nginx создана"
    else
        success "Конфигурация Nginx уже существует"
    fi
    
    # Удаляем дефолтный конфиг если есть
    if [ -L "/etc/nginx/sites-enabled/default" ]; then
        rm -f /etc/nginx/sites-enabled/default
        info "Дефолтный конфиг Nginx удалён"
    fi
    
    # Проверка конфигурации
    if nginx -t; then
        success "Конфигурация Nginx валидна"
        systemctl reload nginx
        success "Nginx перезапущен"
    else
        error "Ошибка в конфигурации Nginx!"
        exit 1
    fi
}

# Получение SSL сертификата
get_ssl_cert() {
    local staging=""
    if [[ "$1" == "--dry-run" ]]; then
        staging="--staging"
        warning "Используется staging сервер Let's Encrypt (тестовый режим)"
    fi
    
    info "Получение SSL сертификата для $DOMAIN..."
    
    # Проверяем, есть ли уже сертификат
    if [ -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
        warning "Сертификат уже существует"
        read -p "Пересоздать? (y/n): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            return 0
        fi
    fi
    
    # Получаем сертификат через Nginx plugin
    certbot $staging --nginx \
        -d $DOMAIN \
        -d www.$DOMAIN \
        --email $EMAIL \
        --agree-tos \
        --non-interactive \
        --redirect \
        --hsts \
        --cert-name $DOMAIN
    
    if [ $? -eq 0 ]; then
        success "SSL сертификат получен и установлен"
    else
        error "Не удалось получить SSL сертификат"
        exit 1
    fi
}

# Настройка автообновления SSL
setup_auto_renew() {
    info "Настройка автообновления SSL..."
    
    # Проверяем, есть ли уже cron задача
    if grep -q "certbot renew" /etc/cron.d/certbot 2>/dev/null || \
       [ -f /etc/cron.daily/certbot ]; then
        success "Автообновление уже настроено"
    else
        # Certbot обычно сам создаёт cron задачу или systemd timer
        systemctl enable certbot.timer 2>/dev/null || true
        systemctl start certbot.timer 2>/dev/null || true
        success "Автообновление настроено (systemd timer)"
    fi
    
    # Тестовое обновление
    info "Тестирование автообновления..."
    certbot renew --dry-run
    success "Автообновление работает корректно"
}

# Обновление Django settings для production
update_django_settings() {
    info "Обновление настроек Django для production..."
    
    # Создаём файл с production настройками
    cat > "$PROJECT_ROOT/.env.production" <<EOF
# Production settings for tlpn.shop
DEBUG=False
SECRET_KEY=CHANGE_THIS_IN_PRODUCTION
ALLOWED_HOSTS=tlpn.shop,www.tlpn.shop,localhost,127.0.0.1

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_ADMIN_ID=your_admin_id_here

# WebApp URL (production)
TELEGRAM_WEBAPP_URL=https://tlpn.shop

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
    
    warning "Не забудьте изменить SECRET_KEY и TELEGRAM_BOT_TOKEN в .env.production"
    success "Production настройки созданы: .env.production"
}

# Показать инструкцию
show_summary() {
    echo ""
    echo "================================================="
    echo "         TULPIN SHOP - SSL настройка завершена"
    echo "================================================="
    echo ""
    echo "Домен: https://$DOMAIN"
    echo ""
    echo "Следующие шаги:"
    echo "  1. Отредактируйте .env.production (SECRET_KEY, TELEGRAM_BOT_TOKEN)"
    echo "  2. Запустите проект: ./start.sh"
    echo "  3. Проверьте HTTPS: https://$DOMAIN"
    echo ""
    echo "Команды для управления:"
    echo "  sudo nginx -t              - проверить конфиг Nginx"
    echo "  sudo systemctl status nginx - статус Nginx"
    echo "  sudo certbot certificates  - список сертификатов"
    echo "  sudo certbot renew         - обновить SSL"
    echo ""
}

# =============================================================================
# Основная логика
# =============================================================================

main() {
    echo ""
    echo "================================================="
    echo "    TULPIN SHOP - Nginx + SSL Setup"
    echo "================================================="
    echo ""
    
    check_root
    
    case "${1:-}" in
        --renew)
            info "Обновление SSL сертификатов..."
            certbot renew
            systemctl reload nginx
            success "SSL сертификаты обновлены"
            exit 0
            ;;
        --dry-run)
            check_domain
            install_nginx
            install_certbot
            setup_nginx_config
            get_ssl_cert "--dry-run"
            setup_auto_renew
            update_django_settings
            show_summary
            ;;
        --help|-h)
            echo "Использование:"
            echo "  ./setup_ssl.sh           - полная настройка"
            echo "  ./setup_ssl.sh --renew   - обновить SSL"
            echo "  ./setup_ssl.sh --dry-run - тестовый режим"
            echo "  ./setup_ssl.sh --help    - эта справка"
            exit 0
            ;;
        "")
            check_domain
            install_nginx
            install_certbot
            setup_nginx_config
            get_ssl_cert
            setup_auto_renew
            update_django_settings
            show_summary
            ;;
        *)
            error "Неизвестная опция: $1"
            exit 1
            ;;
    esac
}

main "$@"
