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

## 🔧 Production настройки

1. Установите `DEBUG = False`
2. Настройте `ALLOWED_HOSTS`
3. Используйте PostgreSQL вместо SQLite
4. Настройте HTTPS для WebApp
5. Используйте webhook для бота вместо polling

## 📦 Зависимости

- Django 5.2+
- Django REST Framework
- aiogram 3.x (Telegram бот)
- Pillow (работа с изображениями)
- aiohttp (HTTP клиент)
