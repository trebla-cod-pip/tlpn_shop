# 🚀 Деплой и отладка TMA

## 1. Применение изменений на сервере

```bash
cd /opt/tlpn_shop
git pull
```

## 2. Проверка ошибки 500 на /analytics/dashboard-ui/

### Возможные причины:
1. Не установлен `analytics_tags` templatetag
2. Ошибка в `dashboard_views.py`
3. Нет данных в моделях аналитики

### Диагностика:

```bash
# Проверка логов Django
tail -f /var/log/tulpin/error.log

# Или через journalctl
journalctl -u tulpin -f

# Проверка через Django
python manage.py shell
>>> from analytics.models import TrackingSession
>>> TrackingSession.objects.count()
```

### Быстрое исправление:

Если ошибка в templatetags, проверьте:
```bash
ls -la /opt/tlpn_shop/analytics/templatetags/
```

Файлы должны быть:
- `__init__.py`
- `analytics_tags.py`

## 3. Отладка TMA (Telegram Mini App)

### Debug панель

После деплоя откройте https://tlpn.shop/bag/ из Telegram.

Внизу страницы появится **чёрная панель отладки** с логами:
- 🟢 `[TMA]` - обычные логи
- 🟡 `[TMA]` - предупреждения  
- 🔴 `[TMA]` - ошибки

### Что должно быть в логах:

```
[12:34:56] Debug panel initialized
[12:34:57] [TMA bag.html] Начало инициализации Telegram пользователя...
[12:34:57] [TMA bag.html] Telegram WebApp: {platform: 'ios', version: '7.0', ...}
[12:34:57] [TMA bag.html] Данные пользователя из Telegram: {id: 123456789, ...}
[12:34:57] [TMA bag.html] Сохранение профиля на сервере: {id: 123456789, ...}
[12:34:58] [TMA bag.html] Сервер ответил: {success: true, user_id: 123456789, ...}
[12:34:58] [TMA bag.html] Профиль сохранён на сервере
```

### Если видите "Нет данных пользователя":

1. **Проверьте, что заходите из Telegram:**
   - Откройте бота
   - Нажмите кнопку "Открыть магазин"
   - Не открывайте в браузере!

2. **Проверьте TELEGRAM_BOT_TOKEN:**
   ```bash
   grep TELEGRAM_BOT_TOKEN /opt/tlpn_shop/.env
   ```

3. **Проверьте логи сервера:**
   ```bash
   tail -f /var/log/tulpin/error.log | grep TMA
   ```

## 4. Проверка сохранения пользователей

```bash
python manage.py shell
>>> from store.models import TelegramUser
>>> TelegramUser.objects.all()
>>> TelegramUser.objects.filter(telegram_id=123456789)  # Ваш ID
```

Если пусто — проблема с сохранением.

## 5. Проверка заказов

```bash
>>> from orders.models import Order
>>> Order.objects.values_list('telegram_user_id', flat=True).distinct()
>>> Order.objects.filter(telegram_user_id=123456789)
```

## 6. Тестовый заказ

1. Откройте https://tlpn.shop/bag/ из Telegram
2. Добавьте товар в корзину
3. Оформите заказ
4. Проверьте в админке: https://tlpn.shop/admin/orders/order/

**Должно быть заполнено:**
- ✅ Telegram User ID: 123456789
- ✅ Telegram username: @username
- ✅ Имя Telegram: Ivan
- ✅ Фамилия Telegram: Ivanov

## 7. Исправление частых проблем

### Проблема: "TemplateDoesNotExist analytics_tags"
```bash
# Проверьте INSTALLED_APPS
grep -A 20 "INSTALLED_APPS" /opt/tlpn_shop/config/settings.py
```

### Проблема: "ModuleNotFoundError: No module named 'analytics.templatetags'"
Убедитесь, что в папке `analytics/templatetags/` есть `__init__.py`

### Проблема: Пользователь не сохраняется
Проверьте логи TMA debug панели и сервера:
```bash
tail -100 /var/log/tulpin/error.log | grep -i telegram
```

## 8. Ссылки для проверки

| Страница | URL |
|----------|-----|
| **Dashboard** | https://tlpn.shop/analytics/dashboard-ui/ |
| **Корзина** | https://tlpn.shop/bag/ |
| **Админка** | https://tlpn.shop/admin/ |
| **Заказы** | https://tlpn.shop/admin/orders/order/ |
| **Telegram пользователи** | https://tlpn.shop/admin/store/telegramuser/ |
