#!/bin/bash

# =============================================================================
# Tulpin Shop - TMA Debug Script
# Использование: ./debug_tma.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}>>> $1${NC}"; }
success() { echo -e "${GREEN}✓ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }

cd /opt/tlpn_shop

echo ""
echo "================================================="
echo "    TULPIN SHOP - TMA Debug"
echo "================================================="
echo ""

# 1. Проверка Git
info "Проверка Git статуса..."
git status --short | head -5 || warning "Git не настроен"

# 2. Проверка .env
info "Проверка .env..."
if [ -f ".env" ]; then
    if grep -q "TELEGRAM_BOT_TOKEN" .env; then
        success "TELEGRAM_BOT_TOKEN найден"
    else
        error "TELEGRAM_BOT_TOKEN не найден в .env"
    fi
    
    if grep -q "TELEGRAM_ADMIN_ID" .env; then
        success "TELEGRAM_ADMIN_ID найден"
    else
        warning "TELEGRAM_ADMIN_ID не найден в .env"
    fi
else
    error ".env файл не найден"
fi

# 3. Проверка темплатегов
info "Проверка analytics_tags..."
if [ -f "analytics/templatetags/analytics_tags.py" ]; then
    success "analytics_tags.py существует"
    if grep -q "abs_val" analytics/templatetags/analytics_tags.py; then
        success "Функция abs_value найдена"
    else
        error "Функция abs_value не найдена"
    fi
else
    error "analytics_tags.py не найден"
fi

# 4. Проверка моделей
info "Проверка моделей..."
if grep -q "TelegramUser" store/models.py; then
    success "Модель TelegramUser найдена"
else
    error "Модель TelegramUser не найдена"
fi

if grep -q "telegram_user_id" orders/models.py; then
    success "Поле telegram_user_id найдено"
else
    error "Поле telegram_user_id не найдено"
fi

# 5. Проверка логов
info "Последние ошибки в логах..."
if [ -f "/var/log/tulpin/error.log" ]; then
    tail -20 /var/log/tulpin/error.log | grep -i "telegram\|tma\|error" || success "Ошибок не найдено"
else
    warning "Лог файл не найден"
fi

# 6. Проверка пользователей Telegram
info "Пользователи Telegram в БД..."
python manage.py shell -c "
from store.models import TelegramUser
count = TelegramUser.objects.count()
print(f'Всего пользователей: {count}')
if count > 0:
    for user in TelegramUser.objects.all()[:5]:
        print(f'  • {user.first_name} {user.last_name} (@{user.username}) - ID: {user.telegram_id}')
" 2>/dev/null || warning "Не удалось выполнить"

# 7. Проверка заказов
info "Заказы с Telegram User ID..."
python manage.py shell -c "
from orders.models import Order
total = Order.objects.count()
with_tg = Order.objects.exclude(telegram_user_id__isnull=True).count()
print(f'Всего заказов: {total}')
print(f'С Telegram User ID: {with_tg}')
print(f'Без Telegram User ID: {total - with_tg}')
" 2>/dev/null || warning "Не удалось выполнить"

# 8. Проверка миграций
info "Проверка миграций..."
python manage.py showmigrations orders 2>/dev/null | tail -3 || warning "Не удалось выполнить"

echo ""
echo "================================================="
echo "    Готово!"
echo "================================================="
echo ""
echo "Для отладки TMA:"
echo "1. Откройте https://tlpn.shop/bag/ из Telegram"
echo "2. Найдите чёрную панель отладки внизу страницы"
echo "3. Проверьте логи [TMA]"
echo ""
echo "Dashboard UI: https://tlpn.shop/analytics/dashboard-ui/"
echo ""
