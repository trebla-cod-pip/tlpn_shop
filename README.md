# Tulipa - Магазин тюльпанов с Telegram Mini App

Django приложение для продажи тюльпанов через Telegram Mini App и мобильную веб-версию.

## 🚀 Быстрый старт

### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

### 2. Настройка переменных окружения

Отредактируйте файл `.env`:

```env
SECRET_KEY=ваш-secret-key
DEBUG=True

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN=1234567890:AABBccDDeeFFggHHiiJJkkLLmmNNooP  # Получить у @BotFather
TELEGRAM_ADMIN_ID=123456789  # Ваш Telegram ID

# WebApp URL
TELEGRAM_WEBAPP_URL=http://localhost:8000
```

### 3. Применение миграций

```bash
python manage.py migrate
```

### 4. Создание суперпользователя

```bash
python manage.py createsuperuser
```

### 5. Запуск сервера разработки

```bash
python manage.py runserver
```

### 6. Запуск Telegram бота (в отдельном терминале)

```bash
python manage.py starttelegram
```

## 📱 Настройка Telegram бота

1. Откройте @BotFather в Telegram
2. Создайте нового бота: `/newbot`
3. Получите токен
4. Настройте WebApp:
   - `/mybots` → Выберите бота → Bot Settings → Menu Button
   - Укажите URL: `http://your-domain.com` (или ngrok для разработки)

### Для локальной разработки с ngrok:

```bash
# Установите ngrok
ngrok http 8000
```

Используйте полученный URL в `TELEGRAM_WEBAPP_URL`.

## 📁 Структура проекта

```
tulpin/
├── config/              # Настройки Django проекта
├── store/               # Приложение магазина (товары, категории)
│   ├── models.py        # Модели Product, Category
│   ├── serializers.py   # DRF сериалайзеры
│   ├── views.py         # API и web views
│   └── admin.py         # Админка
├── orders/              # Приложение заказов
│   ├── models.py        # Модели Order, OrderItem
│   ├── serializers.py   # Сериалайзеры заказов
│   ├── views.py         # API для заказов
│   └── admin.py         # Админка заказов
├── telegram_app/        # Telegram интеграция
│   ├── bot.py           # Aiogram бот
│   ├── utils.py         # Утилиты для отправки сообщений
│   └── management/      # Management команды
├── templates/           # HTML шаблоны
│   ├── base.html        # Базовый шаблон
│   └── store/           # Шаблоны магазина
└── media/               # Загруженные изображения
```

## 🔌 API Endpoints

### Товары
- `GET /api/products/` - Список товаров
- `GET /api/products/<slug>/` - Детали товара
- `GET /api/products/?category=<slug>` - Фильтр по категории
- `GET /api/products/?featured=true` - Рекомендуемые товары

### Категории
- `GET /api/categories/` - Список категорий

### Заказы
- `POST /api/orders/` - Создать заказ
- `GET /api/orders/` - Список заказов пользователя
- `GET /api/orders/<id>/` - Детали заказа

## 🛒 Поток заказа

1. Пользователь открывает WebApp в Telegram
2. Выбирает товары, добавляет в корзину
3. Заполняет данные доставки
4. Заказ создаётся через API
5. Пользователь получает сообщение в Telegram с деталями заказа
6. Админ получает уведомление о новом заказе

## 🎨 Шаблоны

- `home.html` - Главная страница с каталогом
- `item.html` - Страница товара
- `bag.html` - Корзина с формой оформления

## 📝 Админка

Доступна по адресу: `/admin/`

- Управление товарами и категориями
- Просмотр и обработка заказов
- Смена статусов заказов

## 🔧 Production развёртывание

### Автоматическое развёртывание (рекомендуется)

Скрипт `deploy.sh` автоматически настроит всё:

```bash
# На сервере (Ubuntu/Debian)
sudo ./deploy.sh
```

**Что делает скрипт:**
1. Устанавливает системные зависимости (Python, Nginx, Certbot)
2. Создаёт виртуальное окружение и устанавливает Python-зависимости
3. Собирает статику в `/var/www/tlpn_shop/static/`
4. Применяет миграции и создаёт суперпользователя
5. Настраивает Gunicorn systemd сервис
6. Настраивает Nginx с правильными путями
7. Получает SSL сертификат Let's Encrypt (если нет)
8. Настраивает автообновление SSL

**Опции скрипта:**
```bash
./deploy.sh              # Полное развёртывание
./deploy.sh --ssl-only   # Только SSL настройка
./deploy.sh --status     # Показать статус сервисов
./deploy.sh --help       # Справка
```

### Ручное развёртывание

1. **Скопируйте проект на сервер:**
```bash
git clone <repository> /root/tlpn_shop
cd /root/tlpn_shop
```

2. **Установите зависимости:**
```bash
sudo apt update && sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt gunicorn
```

3. **Настройте переменные окружения:**
```bash
# Создайте .env файл
cat > .env << EOF
DEBUG=False
DJANGO_DEBUG=False
ALLOWED_HOSTS=tlpn.shop,www.tlpn.shop
SECRET_KEY=ваш-secret-key
TELEGRAM_BOT_TOKEN=ваш-токен
TELEGRAM_WEBAPP_URL=https://tlpn.shop
EOF
```

4. **Соберите статику:**
```bash
mkdir -p /var/www/tlpn_shop/static
mkdir -p /var/www/tlpn_shop/media
chown -R www-data:www-data /var/www/tlpn_shop

export STATIC_ROOT=/var/www/tlpn_shop/static
python manage.py collectstatic --noinput
python manage.py migrate
```

5. **Настройте Gunicorn:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable tulpin_shop
sudo systemctl start tulpin_shop
```

6. **Настройте Nginx:**
```bash
sudo ln -sf /etc/nginx/sites-available/tlpn_shop /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

7. **Получите SSL сертификат:**
```bash
sudo certbot certonly --webroot -w /var/www/certbot -d tlpn.shop -d www.tlpn.shop
```

## 📦 Зависимости

- Django 5.2+
- Django REST Framework
- aiogram 3.x (Telegram бот)
- Pillow (работа с изображениями)
- aiohttp (HTTP клиент)
