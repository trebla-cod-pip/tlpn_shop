# 🌷 Tulipa - Документация проекта

Интернет-магазин тюльпанов с интеграцией Telegram Mini App (TMA) и внутренней системой аналитики.

---

## 📋 Содержание

1. [Быстрый старт](#быстрый-старт)
2. [Архитектура проекта](#архитектура-проекта)
3. [Telegram Mini App](#telegram-mini-app)
4. [Оформление заказа](#оформление-заказа)
5. [API Reference](#api-reference)
6. [Модели данных](#модели-данных)
7. [Аналитика](#аналитика)
8. [Развёртывание](#развёртывание)
9. [Устранение неполадок](#устранение-неполадок)

---

## 🚀 Быстрый старт

### Требования

- Python 3.10+
- SQLite3 (dev) / PostgreSQL (prod)
- Telegram Bot Token (для TMA)

### Установка

```bash
# Клонирование репозитория
git clone <repository-url>
cd tulpin

# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных окружения
cp .env.example .env
# Отредактируйте .env (см. ниже)

# Применение миграций
python manage.py migrate

# Загрузка тестовых данных (опционально)
python manage.py load_test_data

# Запуск сервера разработки
python manage.py runserver

# Запуск Telegram бота (в отдельном терминале)
python manage.py starttelegram
```

### Настройка .env

```env
# Django settings
SECRET_KEY=your-secret-key-here
DEBUG=True
DJANGO_DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_PATH=C:/Users/username/Desktop/tulpin/db.sqlite3

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP
TELEGRAM_ADMIN_ID=123456789

# WebApp URL
TELEGRAM_WEBAPP_URL=http://127.0.0.1:8000
```

---

## 🏗 Архитектура проекта

```
tulpin/
├── config/              # Настройки Django
│   ├── settings.py      # Основные настройки
│   ├── urls.py          # Корневой URLconf
│   └── wsgi.py          # WSGI конфигурация
├── store/               # Приложение магазина
│   ├── models.py        # Product, Category
│   ├── views.py         # API и web views
│   ├── serializers.py   # DRF сериализаторы
│   └── admin.py         # Админ-панель
├── orders/              # Приложение заказов
│   ├── models.py        # Order, OrderItem
│   ├── views.py         # API для заказов
│   ├── serializers.py   # Сериализаторы заказов
│   └── admin.py         # Админ-панель заказов
├── telegram_app/        # Telegram интеграция
│   ├── bot.py           # Aiogram бот
│   ├── utils.py         # Уведомления в Telegram
│   └── management/      # Management команды
├── analytics/           # Система аналитики
│   ├── models.py        # TrackingSession, TrackingEvent
│   ├── middleware.py    # Трекинг событий
│   ├── dashboard_views.py # Дашборд
│   └── management/      # Агрегация данных
├── templates/           # HTML шаблоны
│   ├── base.html        # Базовый шаблон
│   └── store/           # Шаблоны магазина
│       ├── home.html    # Главная страница
│       ├── item.html    # Страница товара
│       ├── bag.html     # Корзина
│       └── ...
└── static/              # Статические файлы
    ├── css/             # Стили
    ├── js/              # JavaScript
    └── fonts/           # Шрифты Inter
```

---

## 📱 Telegram Mini App

### Что такое TMA

Telegram Mini App - это веб-приложение, которое открывается внутри Telegram. Пользователи могут просматривать каталог, добавлять товары в корзину и оформлять заказы без выхода из мессенджера.

### Инициализация TMA

```javascript
// templates/store/bag.html
function initTelegramUser() {
    // Ждём загрузки Telegram WebApp
    if (!window.Telegram || !window.Telegram.WebApp) {
        setTimeout(initTelegramUser, 100);
        return;
    }

    const tg = window.Telegram.WebApp;
    tg.ready();
    tg.expand(); // Разворачиваем на весь экран

    // Получаем данные пользователя
    if (tg.initDataUnsafe?.user) {
        user = {
            id: tgUser.id,
            username: tgUser.username,
            first_name: tgUser.first_name,
            last_name: tgUser.last_name,
            phone: tgUser.phone,
        };
    }
}
```

### Данные пользователя из Telegram

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | number | Уникальный ID пользователя Telegram |
| `username` | string | Username (может отсутствовать) |
| `first_name` | string | Имя |
| `last_name` | string | Фамилия (может отсутствовать) |
| `phone` | string | Телефон (если пользователь разрешил доступ) |

### MainButton

Telegram MainButton - это большая кнопка внизу экрана TMA:

```javascript
// Показать MainButton
tg.MainButton.setText(`ОФОРМИТЬ ЗАКАЗ — ${total}₽`);
tg.MainButton.show();
tg.MainButton.onClick(submitOrderFromMainButton);

// Скрыть MainButton
tg.MainButton.hide();
tg.MainButton.offClick(submitOrderFromMainButton);
```

### Haptic Feedback

Тактильная отдача для улучшения UX:

```javascript
// Лёгкая вибрация
tg.HapticFeedback.impactOccurred('light');

// Средняя вибрация
tg.HapticFeedback.impactOccurred('medium');

// Успех
tg.HapticFeedback.notificationOccurred('success');

// Ошибка
tg.HapticFeedback.notificationOccurred('error');
```

---

## 🛒 Оформление заказа

### Поток оформления заказа

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Пользователь нажимает "Оформить заказ" в корзине         │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Показывается pop-up с выбором способа связи:             │
│    • Через Telegram                                         │
│    • По телефону                                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Форма доставки с предзаполненными полями:                │
│    • Телефон (автозаполнение из Telegram)                   │
│    • Адрес доставки *                                       │
│    • Дата доставки * (завтра по умолчанию)                  │
│    • Время (по умолчанию "В течение дня")                   │
│    • Комментарий                                            │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Отправка заказа в API /api/orders/                       │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Уведомления отправляются:                                │
│    • Админу в Telegram                                      │
│    • Пользователю в Telegram (если есть telegram_user_id)   │
└─────────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. TMA закрывается / Веб показывает уведомление об успехе   │
└─────────────────────────────────────────────────────────────┘
```

### Выбор способа связи

**Через Telegram:**
- Показывается @username или имя
- Телефон скрывается если есть в Telegram
- Связь через мессенджер

**По телефону:**
- Показывается номер телефона
- Если телефона нет в Telegram - поле для ввода
- Связь через звонок/SMS

### Структура заказа (API)

```json
{
  "items": [
    {"product_id": 1, "quantity": 2}
  ],
  "phone": "+7 (999) 000-00-00",
  "delivery_address": "ул. Пушкина, д. 10, кв. 5",
  "delivery_date": "2026-02-28",
  "delivery_time": "В течение дня",
  "comment": "Позвонить за 30 минут",
  "telegram_user_id": 123456789,
  "telegram_username": "username",
  "telegram_first_name": "Имя",
  "telegram_last_name": "Фамилия",
  "preferred_contact_method": "telegram"
}
```

---

## 📡 API Reference

### Товары

#### Получить список товаров

```
GET /api/products/
```

**Параметры:**
- `category` (string, optional) - фильтр по категории (slug)
- `featured` (string, optional) - `true` для рекомендуемых
- `tag` (string, optional) - фильтр по тегу

**Ответ:**
```json
[
  {
    "id": 1,
    "name": "Белый тюльпан",
    "slug": "belyy-tyulpan",
    "price": "2500.00",
    "image": "/media/products/tulip.webp",
    "category": {"slug": "white", "name": "Белые"}
  }
]
```

#### Получить товар по slug

```
GET /api/products/<slug>/
```

### Категории

#### Получить список категорий

```
GET /api/categories/
```

### Заказы

#### Создать заказ

```
POST /api/orders/
```

**Тело запроса:**
```json
{
  "items": [{"product_id": 1, "quantity": 2}],
  "phone": "+7 (999) 000-00-00",
  "delivery_address": "ул. Пушкина, д. 10",
  "delivery_date": "2026-02-28",
  "telegram_user_id": 123456789
}
```

**Ответ:**
```json
{
  "id": 42,
  "status": "pending",
  "status_display": "Ожидает подтверждения",
  "total_amount": "5000.00",
  "delivery_address": "ул. Пушкина, д. 10",
  "delivery_date": "2026-02-28",
  "items": [
    {
      "product_id": 1,
      "product_name": "Белый тюльпан",
      "quantity": 2,
      "price": "2500.00",
      "total": "5000.00"
    }
  ],
  "created_at": "2026-02-27T12:00:00Z"
}
```

#### Получить список заказов пользователя

```
GET /api/orders/?telegram_user_id=123456789
```

#### Получить детали заказа

```
GET /api/orders/<id>/
```

---

## 🗄 Модели данных

### Order (Заказ)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Уникальный ID |
| `telegram_user_id` | BigIntegerField | ID пользователя Telegram (nullable) |
| `telegram_username` | CharField | Username Telegram |
| `telegram_first_name` | CharField | Имя Telegram |
| `telegram_last_name` | CharField | Фамилия Telegram |
| `phone` | CharField | Телефон |
| `email` | EmailField | Email (опционально) |
| `preferred_contact_method` | CharField | `telegram` или `phone` |
| `delivery_address` | TextField | Адрес доставки |
| `delivery_date` | DateField | Дата доставки |
| `delivery_time` | CharField | Время доставки |
| `comment` | TextField | Комментарий |
| `status` | CharField | `pending`, `confirmed`, `assembling`, `delivering`, `delivered`, `cancelled` |
| `total_amount` | DecimalField | Общая сумма |
| `created_at` | DateTimeField | Дата создания |
| `updated_at` | DateTimeField | Дата обновления |

### OrderItem (Товар в заказе)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Уникальный ID |
| `order` | ForeignKey | Ссылка на заказ |
| `product` | ForeignKey | Ссылка на товар |
| `quantity` | PositiveIntegerField | Количество |
| `price` | DecimalField | Цена на момент заказа |
| `total` | DecimalField | Сумма (price × quantity) |

### Product (Товар)

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | AutoField | Уникальный ID |
| `name` | CharField | Название |
| `slug` | SlugField | URL-идентификатор |
| `description` | TextField | Описание |
| `price` | DecimalField | Цена |
| `image` | ImageField | Основное изображение |
| `cart_image` | ImageField | Изображение для корзины |
| `category` | ForeignKey | Категория |
| `is_featured` | BooleanField | Рекомендуемый |
| `is_active` | BooleanField | Активен |
| `stock` | PositiveIntegerField | Остаток на складе |
| `tags` | JSONField | Теги |

---

## 📊 Аналитика

### Трекинг событий

Автоматический трекинг событий пользователя:

| Событие | Описание |
|---------|----------|
| `page_view` | Просмотр страницы |
| `click` | Клик по элементу |
| `scroll` | Прокрутка страницы |
| `cart_add` | Добавление в корзину |
| `cart_remove` | Удаление из корзины |
| `purchase` | Покупка |

### TrackingSession

```python
{
    "session_id": "uuid",
    "user_id": "telegram_id",
    "utm_source": "telegram",
    "utm_medium": "mini_app",
    "utm_campaign": "spring_sale",
    "ip_hash": "sha256_hash",
    "user_agent": "Mozilla/5.0...",
    "started_at": "2026-02-27T12:00:00Z"
}
```

### Агрегированные метрики

- **Поведенческая**: Сессии, Посетители, Время на сайте, Scroll Depth
- **Конверсии**: CR, AOV, Revenue per Visitor, Cart Abandonment Rate
- **Customer**: LTV, Retention, Churn, RFM-сегменты
- **Маркетинг**: ROMI, ROAS, CPA по каналам
- **Продукты**: Топ по марже, ABC/XYZ анализ

### Дашборд

Доступен по адресу: `/analytics/dashboard-ui/`

6 графиков:
1. Трафик по дням (area chart)
2. Выручка по дням (bar chart)
3. Каналы трафика (donut chart)
4. Воронка конверсии (horizontal bar)
5. RFM-сегменты (pie chart)
6. Топ товаров по марже (horizontal bar)

---

## 🚀 Развёртывание

### Production настройки

#### 1. .env для production

```env
DEBUG=False
DJANGO_DEBUG=False
ALLOWED_HOSTS=tlpn.shop,www.tlpn.shop

SECRET_KEY=<secure-random-key>

DB_PATH=/opt/db/db.sqlite3

STATIC_ROOT=/var/www/tlpn_shop/static/
MEDIA_ROOT=/var/www/tlpn_shop/media/

TELEGRAM_BOT_TOKEN=<bot-token>
TELEGRAM_WEBAPP_URL=https://tlpn.shop
TELEGRAM_ADMIN_ID=<admin-id>
```

#### 2. Сборка статики

```bash
python manage.py collectstatic --noinput
```

#### 3. Gunicorn systemd сервис

```ini
# /etc/systemd/system/tulpin_shop.service
[Unit]
Description=Tulipa Shop Gunicorn daemon
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/root/tlpn_shop
ExecStart=/root/tlpn_shop/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/run/tulpin_shop.sock \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

#### 4. Nginx конфигурация

```nginx
# /etc/nginx/sites-available/tlpn_shop
server {
    listen 80;
    server_name tlpn.shop www.tlpn.shop;

    location = /favicon.ico { access_log off; log_not_found off; }

    location /static/ {
        alias /var/www/tlpn_shop/static/;
    }

    location /media/ {
        alias /var/www/tlpn_shop/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/tulpin_shop.sock;
    }
}
```

#### 5. SSL сертификат (Let's Encrypt)

```bash
sudo certbot certonly --webroot -w /var/www/certbot \
    -d tlpn.shop -d www.tlpn.shop
```

---

## 🔧 Устранение неполадок

### TMA не показывает pop-up с выбором способа связи

**Проблема:** Pop-up не открывается при нажатии "Оформить заказ"

**Решение:**
1. Откройте консоль браузера (F12 в Telegram Desktop)
2. Проверьте логи:
   - `[TMA] WebApp ещё не загружен` - нормально, скрипт ждёт загрузки
   - `[TMA] Пользователь: {...}` - данные получены
   - `[TMA] Modal element not found!` - ошибка в HTML
3. Проверьте что `window.Telegram.WebApp` существует

### Заказ не создаётся, висит "Отправка..."

**Проблема:** Кнопка показывает "Отправка..." и ничего не происходит

**Решение:**
1. Проверьте консоль на ошибки:
   ```javascript
   console.log('[TMA] Response status:', response.status);
   ```
2. Проверьте что `telegram_user_id` передаётся (может быть `null` для веб-версии)
3. Проверьте логи Django сервера

### Ошибка "unable to open database file"

**Проблема:** SQLite не может открыть базу данных

**Решение:**
1. Проверьте путь в `.env`:
   ```env
   DB_PATH=C:/Users/username/Desktop/tulpin/db.sqlite3
   ```
2. Используйте прямые слеши `/` вместо обратных `\`
3. Проверьте права доступа к файлу БД

### Уведомления не отправляются в Telegram

**Проблема:** Заказ создан, но уведомления нет

**Решение:**
1. Проверьте `TELEGRAM_BOT_TOKEN` в `.env`
2. Проверьте `TELEGRAM_ADMIN_ID` в `.env`
3. Проверьте логи:
   ```
   [ERROR] telegram_app.utils: Ошибка отправки пользователю #123456789
   ```
4. Убедитесь что бот добавлен в админы (если нужно отправлять в группу)

### Статика не загружается в production

**Проблема:** CSS/JS файлы возвращают 404

**Решение:**
1. Выполните:
   ```bash
   python manage.py collectstatic --noinput
   ```
2. Проверьте `STATIC_ROOT` в настройках
3. Проверьте права доступа:
   ```bash
   chown -R www-data:www-data /var/www/tlpn_shop/static/
   ```

---

## 📞 Поддержка

По вопросам и проблемам обращайтесь:
- GitHub Issues: <repository-url>/issues
- Telegram: @<support-username>

---

## 📝 Changelog

### v1.2.0 (2026-02-27)
- ✅ Выбор способа связи при оформлении заказа
- ✅ Уведомления в Telegram с указанием способа связи
- ✅ Оптимизация иконок (SVG спрайт вместо Iconify)
- ✅ PageSpeed оптимизации
- ✅ Исправление работы TMA

### v1.1.0
- ✅ Telegram Mini App интеграция
- ✅ Корзина с оформлением заказа
- ✅ Уведомления админу и пользователю

### v1.0.0
- ✅ Базовый функционал магазина
- ✅ Каталог товаров
- ✅ Система аналитики
