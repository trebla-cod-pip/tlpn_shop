# Настройка sitemap.xml

## Что было сделано

1. Добавлен `django.contrib.sitemaps` и `django.contrib.sites` в `INSTALLED_APPS`
2. Создан файл `config/sitemap.py` с классами:
   - `StaticViewSitemap` - главная, корзина, профиль
   - `ProductSitemap` - страницы товаров
   - `CategorySitemap` - категории
3. Обновлен `config/urls.py` - добавлен маршрут `/sitemap.xml`
4. Добавлены настройки в `config/settings.py`:
   - `SITE_ID = 1`
   - `SITEMAP_DOMAIN = 'tlpn.shop'`
   - `SITEMAP_PROTOCOL = 'https'`

## Настройка на сервере

### 1. Применить миграции
```bash
cd /path/to/tulpin
python manage.py migrate
```

### 2. Настроить домен в Django Sites
```bash
python manage.py shell
```

```python
from django.contrib.sites.models import Site
site = Site.objects.get(id=1)
site.domain = 'tlpn.shop'
site.name = 'Tulipa - Минималистичные букеты'
site.save()
```

### 3. Проверить sitemap.xml
Откройте в браузере: `https://tlpn.shop/sitemap.xml`

## Структура sitemap.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <!-- Статические страницы (home, bag, profile) -->
  <!-- Товары (item/<slug>/) -->
  <!-- Категории (/?category=<slug>) -->
</urlset>
```

## Добавление в robots.txt

Создайте или обновите файл `robots.txt` в корне сайта:

```
User-agent: *
Sitemap: https://tlpn.shop/sitemap.xml

Disallow: /admin/
Disallow: /api/
Disallow: /telegram/
Disallow: /analytics/
```

## Примечания

- Sitemap автоматически обновляется при добавлении/изменении товаров
- Для товаров указывается `lastmod` по дате обновления
- Приоритеты: товары (0.9) > статические (0.8) > категории (0.7)
- Частота обновления: daily для статических, weekly для товаров и категорий
