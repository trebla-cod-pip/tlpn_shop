# Tulipa - Интернет-магазин тюльпанов

## Описание проекта

Интернет-магазин тюльпанов с интеграцией Telegram Mini App и внутренней системой аналитики.

---

## Технический стек

| Компонент | Технология |
|-----------|------------|
| Backend | Django 5.2.10 + Django REST Framework |
| Database | SQLite3 (dev) |
| Frontend | HTML/CSS/JS + Telegram WebApp SDK |
| Telegram | aiogram (бот) + Mini Apps |
| Analytics | Собственная система без Celery/Redis |

---

## Структура проекта

```
tulpin/
├── config/              # Настройки Django
├── store/               # Магазин (товары, категории, API)
├── orders/              # Заказы и уведомления
├── telegram_app/        # Telegram бот и WebApp
├── analytics/           # Система аналитики + дашборд
└── templates/           # HTML шаблоны (mobile-first)
```

---

## Ключевой функционал

### Магазин

- Каталог товаров с категориями (Белые, Пастель, Сезонные, Премиум)
- 8 товаров с изображениями (цены: 2300-3500 руб.)
- Карточка товара с выбором количества
- Корзина с оформлением заказа
- Фильтрация по категориям

### Telegram интеграция

- WebApp для просмотра каталога внутри Telegram
- Отправка заказа в Telegram пользователю
- Уведомления админу о новых заказах
- Упрощённая авторизация через Telegram

### Аналитика

- Трекинг сессий и событий (page_view, click, scroll, cart)
- UTM-метки и источники трафика
- Воронка конверсии (9 шагов)
- RFM-сегментация клиентов
- Когортный анализ retention
- Топ товаров по марже
- Дашборд с графиками (ApexCharts)
- GDPR/152-ФЗ (хеширование IP, opt-out)

---

## Метрики аналитики

| Блок | Метрики |
|------|---------|
| Поведенческая | Сессии, Посетители, Время на сайте, Scroll Depth |
| Конверсии | CR, AOV, Revenue per Visitor, Cart Abandonment Rate |
| Customer | LTV, Retention, Churn, RFM-сегменты |
| Маркетинг | ROMI, ROAS, CPA по каналам |
| Продукты | Топ по марже, ABC/XYZ анализ |
| Web Vitals | LCP, INP, CLS |

---

## URL проекта

| Страница | URL |
|----------|-----|
| Главная | http://127.0.0.1:8000/ |
| Товар | http://127.0.0.1:8000/item/<slug>/ |
| Корзина | http://127.0.0.1:8000/bag/ |
| API товаров | http://127.0.0.1:8000/api/products/ |
| API заказов | http://127.0.0.1:8000/api/orders/ |
| Дашборд | http://127.0.0.1:8000/analytics/dashboard-ui/ |
| Админка | http://127.0.0.1:8000/admin/ |

---

## Модели данных

### store

- `Category` — категории товаров
- `Product` — товары (с авто-slug, cart_image)

### orders

- `Order` — заказ (Telegram user, статусы)
- `OrderItem` — товары в заказе

### analytics

- `TrackingSession` — сессии с UTM
- `TrackingEvent` — события (page_view, click, purchase)
- `AggregatedStat` — агрегированные метрики
- `RFMSegment` — RFM-сегментация
- `CustomerCohort` — когорты и retention
- `ChannelPerformance` — эффективность каналов
- `ProductMarginStat` — маржинальность товаров
- `FunnelStep` — воронка конверсии

---

## Команды управления

```bash
# Загрузка тестовых данных
python manage.py load_test_data

# Агрегация аналитики (по cron)
python manage.py aggregate_analytics

# Запуск Telegram бота
python manage.py starttelegram
```

---

## Безопасность

- Хеширование IP (SHA256 + salt)
- Opt-out отслеживания (cookie)
- Персональные данные не хранятся в сырых логах

---

## Дашборд аналитики

6 графиков:

1. Трафик по дням (area chart)
2. Выручка по дням (bar chart)
3. Каналы трафика (donut chart)
4. Воронка конверсии (horizontal bar)
5. RFM-сегменты (pie chart)
6. Топ товаров по марже (horizontal bar)

Фильтры: 7/30/90 дней, год

---

## Что в зачаточном состоянии

- Избранное (заглушка)
- Профиль пользователя (заглушка)
- Поиск товаров
- Оплата на сайте (только уведомление в Telegram)
- ABC/XYZ анализ (модель есть, расчёт не реализован)

---

## Итог

Полнофункциональный MVP магазина с полной системой аналитики, готовый к демонстрации и тестированию на реальных пользователях.
