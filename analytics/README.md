# 📊 Система аналитики для Django E-commerce

Полная система веб-аналитики для интернет-магазина Tulipa без зависимости от Celery/Redis.

## 🏗 Архитектура

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Browser)                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │              analytics/static/analytics/tracker.js        │  │
│  │  - Page View, Scroll Depth, Clicks                        │  │
│  │  - Cart & Checkout Events                                 │  │
│  │  - Web Vitals (LCP, INP, CLS)                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│                    POST /api/analytics/track/                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                       DJANGO APPLICATION                        │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │ AnalyticsMiddleware│  │  Tracking API   │  │  Admin UI    │  │
│  │ - UTM capture    │  │  - Event ingest  │  │  - Dashboard │  │
│  │ - Session track  │  │  - Validation    │  │  - Reports   │  │
│  │ - Funnel steps   │  │                  │  │              │  │
│  └──────────────────┘  └──────────────────┘  └──────────────┘  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
┌──────────────────────────────▼───────────────────────────────────┐
│                      POSTGRESQL / SQLite                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ tracking_    │  │ aggregated_  │  │ rfm_segment          │  │
│  │ session      │  │ stat         │  │ customer_cohort      │  │
│  │ tracking_    │  │ channel_     │  │ product_margin_stat  │  │
│  │ event        │  │ performance  │  │ funnel_step          │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Компоненты

### 1. Модели данных (`analytics/models.py`)

| Модель | Описание |
|--------|----------|
| `TrackingSession` | Сессия пользователя с UTM-метками |
| `TrackingEvent` | Сырые события (page_view, click, scroll, etc.) |
| `AggregatedStat` | Агрегированные метрики для быстрого доступа |
| `RFMSegment` | RFM-сегментация клиентов |
| `CustomerCohort` | Когортный анализ retention |
| `ProductMarginStat` | Маржинальность товаров |
| `ChannelPerformance` | Эффективность каналов трафика |
| `FunnelStep` | Шаги воронки конверсии |

### 2. Middleware (`analytics/middleware.py`)

Автоматически трекает:
- UTM-метки из URL
- Referer и User Agent
- Шаги воронки по URL
- Page View события

**Подключение:**
```python
MIDDLEWARE = [
    ...
    'analytics.middleware.AnalyticsMiddleware',
]
```

### 3. JavaScript Tracker (`analytics/static/analytics/tracker.js`)

Собирает события:
- `page_view` — просмотр страницы
- `scroll_depth` — глубина скролла (25/50/75/100%)
- `click` — клики по важным элементам
- `add_to_cart` — добавление в корзину
- `purchase` — покупка

**Авто-подключение в `base.html`:**
```html
<script src="{% static 'analytics/tracker.js' %}" defer></script>
```

**Ручной трекинг:**
```javascript
// Добавление в корзину
AnalyticsTracker.trackAddToCart(productId, productName, price, quantity);

// Покупка
AnalyticsTracker.trackPurchase(orderId, revenue, items);

// Opt-out
AnalyticsTracker.optOut();
```

### 4. API Endpoints

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/api/analytics/track/` | POST | Приём событий от трекера |
| `/api/analytics/dashboard/` | GET | Основные метрики дашборда |
| `/api/analytics/revenue-per-channel/` | GET | Revenue per Visitor по каналам |
| `/api/analytics/funnel/` | GET | Воронка конверсии |
| `/api/analytics/top-products-margin/` | GET | Топ товаров по марже |
| `/api/analytics/rfm-segments/` | GET | RFM-сегментация |
| `/api/analytics/cohort-retention/` | GET | Когортный анализ |
| `/api/analytics/channel-romi/` | GET | ROMI/ROAS по каналам |

## 🚀 Быстрый старт

### 1. Миграции
```bash
python manage.py migrate analytics
```

### 2. Сбор статистики (ежедневно)
```bash
python manage.py aggregate_analytics
```

**Для Windows Task Scheduler:**
```xml
<Trigger>
    <CalendarTrigger>
        <StartBoundary>2024-01-01T02:00:00</StartBoundary>
        <ScheduleByDay>1</ScheduleByDay>
    </CalendarTrigger>
</Trigger>
<Action>
    <Exec>
        <Command>python</Command>
        <Arguments>C:\Users\trebl\Desktop\tulpin\manage.py aggregate_analytics</Arguments>
    </Exec>
</Action>
```

### 3. Просмотр данных

**Django Admin:**
- `/admin/analytics/trackingsession/` — сессии
- `/admin/analytics/trackingevent/` — события
- `/admin/analytics/aggregatedstat/` — агрегированные метрики
- `/admin/analytics/rfmsegment/` — RFM-сегменты
- `/admin/analytics/channelperformance/` — каналы

**API (требуется is_staff):**
```bash
curl -H "Authorization: Bearer <token>" \
     http://localhost:8000/api/analytics/dashboard/?days=30
```

## 📊 Метрики

### Поведенческая аналитика
- **Sessions** — количество сессий
- **Visitors** — уникальные посетители (по hash IP)
- **Pages/Session** — глубина просмотра
- **Time on Site** — время на сайте
- **Scroll Depth** — % доскролливших до конца

### Конверсии
- **Conversion Rate** = Orders / Sessions × 100%
- **AOV** = Revenue / Orders
- **Revenue per Visitor** = Revenue / Visitors
- **Cart Abandonment Rate** = (Carts - Orders) / Carts × 100%

### Customer Analytics
- **LTV** — средняя выручка с клиента за всё время
- **Retention Rate** — % вернувшихся клиентов (когортный анализ)
- **Churn Rate** — % потерянных клиентов
- **RFM Segmentation:**
  - Champions (лучшие клиенты)
  - Loyal Customers
  - At Risk (под угрозой ухода)
  - Lost (потерянные)

### Маркетинг
- **ROMI** = (Revenue - Cost) / Cost × 100%
- **ROAS** = Revenue / Cost
- **CPA** = Cost / Orders

### Продукты
- **Margin** = Revenue - COGS
- **ABC Analysis** — по вкладу в выручку
- **XYZ Analysis** — по стабильности спроса

## 🔒 Безопасность и GDPR/152-ФЗ

### Хеширование IP
```python
# analytics/models.py
def hash_ip(ip_address: str, salt: str = None) -> str:
    salt = salt or settings.ANALYTICS_IP_SALT
    return hashlib.sha256(f"{ip_address}:{salt}".encode()).hexdigest()
```

### Opt-out отслеживания
```javascript
// Установить cookie
AnalyticsTracker.optOut();

// Проверка в middleware
if request.COOKIES.get('analytics_optout'):
    return self.get_response(request)
```

### Настройки
```python
# settings.py
ANALYTICS_IP_SALT = SECRET_KEY  # Уникальный salt
ANALYTICS_SESSION_TIMEOUT = 30 * 60  # 30 минут
```

## 🧪 Тестирование

### Проверка Cart Abandonment Rate
```python
from analytics.models import FunnelStep

# Корзины созданные
carts = FunnelStep.objects.filter(step=4).values('session').distinct().count()

# Завершённые заказы
orders = FunnelStep.objects.filter(step=8).values('session').distinct().count()

# Cart Abandonment Rate
abandonment = (carts - orders) / carts * 100
print(f"Cart Abandonment Rate: {abandonment:.2f}%")
```

### Проверка трекинга событий
```python
from analytics.models import TrackingEvent

# Page View за сегодня
page_views = TrackingEvent.objects.filter(
    event_type='page_view',
    created_at__date=today
).count()

# Добавления в корзину
add_to_carts = TrackingEvent.objects.filter(
    event_type='add_to_cart'
).count()

print(f"Page Views: {page_views}, Add to Carts: {add_to_carts}")
```

### Проверка Web Vitals
```python
from analytics.models import TrackingEvent

lcp_events = TrackingEvent.objects.filter(
    event_type='web_vital',
    event_name='LCP'
)

avg_lcp = lcp_events.aggregate(
    avg=Avg(Cast('meta__value', FloatField()))
)['avg']

print(f"Average LCP: {avg_lcp:.2f}ms")
```

## 📈 Мониторинг производительности

### 1. Логгирование медленных запросов
```python
# settings.py
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'analytics.log',
        },
    },
    'loggers': {
        'django.db.backends': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
    },
}
```

### 2. Метрики для мониторинга
- Время обработки `/api/analytics/track/` (< 100ms)
- Количество событий в минуту
- % ошибок при записи событий

### 3. Оптимизация
- Индексы на `created_at`, `session_id`, `event_type`
- Batch insert событий (в JS-трекере)
- Агрегация данных nightly (не в реальном времени)

## 📋 Checklist для продакшена

- [ ] Сменить `ANALYTICS_IP_SALT` на уникальный
- [ ] Настроить ежедневный запуск `aggregate_analytics`
- [ ] Включить HTTPS для API
- [ ] Настроить backup БД
- [ ] Добавить мониторинг ошибок (Sentry)
- [ ] Настроить алерты при аномалиях в трафике
- [ ] Провести нагрузочное тестирование

## 📚 Дополнительные ресурсы

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Web Vitals GitHub](https://github.com/GoogleChrome/web-vitals)
- [RFM Analysis Guide](https://www.clevertap.com/blog/rfm-analysis/)
