# Tulpin Shop - Production Setup Guide

## 📋 Быстрый старт (локальная разработка)

```bash
# Запуск проекта (миграции + данные + сервер)
./start.sh

# Или на Windows
start.bat
```

**Доступ:**
- Сайт: http://0.0.0.0:8000
- Админка: http://0.0.0.0:8000/admin
- Логин: `trebla`
- Пароль: `KFCone1ove!12`

---

## 🚀 Production развёртывание (Nginx + SSL)

### Требования
- Сервер с Ubuntu/Debian
- Домен `tlpn.shop` с A-записью на IP сервера
- Root доступ

### Автоматическое развёртывание

```bash
# Полное развёртывание (Gunicorn + Nginx + SSL)
sudo ./deploy.sh
```

### Пошаговая настройка

#### 1. Настройка Nginx + SSL (без развёртывания)

```bash
# Полная настройка
sudo ./setup_ssl.sh

# Тестовый режим (staging сертификаты)
sudo ./setup_ssl.sh --dry-run

# Обновление SSL
sudo ./setup_ssl.sh --renew
```

#### 2. Ручная настройка

```bash
# 1. Скопировать конфиг Nginx
sudo cp nginx.conf /etc/nginx/sites-available/tlpn_shop
sudo ln -sf /etc/nginx/sites-available/tlpn_shop /etc/nginx/sites-enabled/tlpn_shop
sudo rm -f /etc/nginx/sites-enabled/default

# 2. Получить SSL сертификат
sudo certbot --nginx -d tlpn.shop -d www.tlpn.shop --email admin@tlpn.shop

# 3. Проверить и перезапустить Nginx
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📁 Структура файлов

```
tulpin/
├── start.sh              # Локальный запуск (dev)
├── start.bat             # Локальный запуск (Windows)
├── setup_ssl.sh          # Настройка SSL через Let's Encrypt
├── setup_fonts.sh        # Скачивание и установка шрифтов
├── deploy.sh             # Production развёртывание
├── nginx.conf            # Конфигурация Nginx
├── create_superuser.py   # Скрипт создания админа
├── create_test_data.py   # Тестовые данные
└── .env.production       # Production настройки (создаётся автоматически)
```

---

## 🔤 Шрифты

Проект использует шрифт **Inter** (Google Fonts).

### Локальная установка шрифтов (для production)

```bash
# Скачать и установить шрифты
./setup_fonts.sh
```

Это:
1. Скачает WOFF2 файлы шрифтов Inter (веса: 300, 400, 500, 600, 700)
2. Создаст CSS файл с `@font-face` правилами
3. Обновит шаблон `base.html` для использования локальных шрифтов
4. Соберёт статику через `collectstatic`

### Почему локальные шрифты?

| Преимущество | Описание |
|--------------|----------|
| Скорость | Шрифты загружаются с вашего сервера/CDN |
| Приватность | Нет запросов к Google Fonts (GDPR) |
| Надёжность | Работает без доступа к googleapis.com |
| Кэширование | Полный контроль над кэшем |

---

## 🔧 Команды управления

### Nginx
```bash
sudo nginx -t                    # Проверить конфиг
sudo systemctl status nginx      # Статус
sudo systemctl restart nginx     # Перезапуск
sudo tail -f /var/log/nginx/tlpn_shop_error.log  # Логи
```

### SSL сертификаты
```bash
sudo certbot certificates        # Список сертификатов
sudo certbot renew               # Обновить SSL
sudo certbot renew --dry-run     # Тест обновления
```

### Gunicorn (production)
```bash
sudo systemctl status tulpin_shop    # Статус
sudo systemctl restart tulpin_shop   # Перезапуск
sudo journalctl -u tulpin_shop -f    # Логи
```

---

## 🔐 Безопасность

После развёртывания:

1. Измените `SECRET_KEY` в `.env.production`
2. Установите реальный `TELEGRAM_BOT_TOKEN`
3. Настройте firewall:
   ```bash
   sudo ufw allow 22/tcp    # SSH
   sudo ufw allow 80/tcp    # HTTP
   sudo ufw allow 443/tcp   # HTTPS
   sudo ufw enable
   ```

---

## 📊 Мониторинг

Проверка доступности:
```bash
curl -I https://tlpn.shop
curl -I https://tlpn.shop/health/
```

Проверка SSL:
```bash
curl -vI https://tlpn.shop 2>&1 | grep SSL
```

---

## 🆘 Troubleshooting

### Ошибка 502 Bad Gateway
```bash
# Проверьте Gunicorn
sudo systemctl status tulpin_shop
sudo journalctl -u tulpin_shop -n 50
```

### SSL не работает
```bash
# Проверьте сертификаты
sudo certbot certificates

# Пересоздайте
sudo certbot delete --cert-name tlpn.shop
sudo certbot --nginx -d tlpn.shop -d www.tlpn.shop
```

### Nginx не запускается
```bash
sudo nginx -t
sudo systemctl status nginx
sudo journalctl -u nginx -n 50
```
