# Tulpin Shop - Production Setup Guide

## 📋 Быстрый старт

### Локальная разработка (Windows/Linux/Mac)

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

## 🚀 Production развёртывание (сервер)

### Требования
- Сервер с Ubuntu/Debian
- Домен `tlpn.shop` с A-записью на IP сервера
- Root доступ

### Автоматическая настройка (всё в одном)

```bash
# Полная настройка: система + проект + шрифты + SSL + Nginx
sudo ./setup.sh
```

### Отдельные режимы

```bash
# Только локальный запуск (dev)
sudo ./setup.sh --dev

# Только SSL сертификаты
sudo ./setup.sh --ssl-only

# Только шрифты
sudo ./setup.sh --fonts

# Справка
sudo ./setup.sh --help
```

---

## 📁 Структура файлов

```
tulpin/
├── setup.sh              # Production настройка (всё в одном)
├── start.sh              # Локальный запуск (dev)
├── start.bat             # Локальный запуск (Windows)
├── nginx.conf            # Конфигурация Nginx
├── setup_fonts.sh        # Отдельная настройка шрифтов
├── setup_ssl.sh          # Отдельная настройка SSL
├── deploy.sh             # Старый deploy скрипт
├── create_superuser.py   # Скрипт создания админа
├── create_test_data.py   # Тестовые данные
└── .env.production       # Production настройки
```

---

## 🔤 Шрифты

Проект использует шрифт **Inter** (Google Fonts).

### Локальная установка (для production)

```bash
# Скачать и установить шрифты
sudo ./setup.sh --fonts
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
sudo tail -f /var/log/nginx/tlpn_shop_error.log  # Логи ошибок
```

### SSL сертификаты
```bash
sudo certbot certificates        # Список сертификатов
sudo certbot renew               # Обновить SSL
sudo certbot renew --dry-run     # Тест обновления
```

### Gunicorn (Django приложение)
```bash
sudo systemctl status tulpin_shop    # Статус
sudo systemctl restart tulpin_shop   # Перезапуск
sudo systemctl stop tulpin_shop      # Остановить
sudo journalctl -u tulpin_shop -f    # Логи
```

---

## 📦 Последовательность развёртывания

Скрипт `setup.sh` выполняет шаги в правильном порядке:

1. **Проверки** → root доступ, Python, домен
2. **Система** → установка зависимостей (nginx, certbot, python)
3. **Проект** → venv, зависимости, миграции, суперпользователь, тестовые данные
4. **Шрифты** → скачивание Inter, создание CSS
5. **Gunicorn** → systemd сервис для Django
6. **SSL** → получение сертификата Let's Encrypt
7. **Nginx** → настройка прокси + SSL
8. **Production env** → создание `.env.production`

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

## 🆘 Troubleshooting

### Ошибка 502 Bad Gateway
```bash
# Проверьте Gunicorn
sudo systemctl status tulpin_shop
sudo journalctl -u tulpin_shop -n 50

# Перезапустите
sudo systemctl restart tulpin_shop
```

### SSL не работает
```bash
# Проверьте сертификаты
sudo certbot certificates

# Пересоздайте
sudo certbot delete --cert-name tlpn.shop
sudo ./setup.sh --ssl-only
```

### Nginx не запускается
```bash
sudo nginx -t
sudo systemctl status nginx
sudo journalctl -u nginx -n 50
```

### Ошибка при получении SSL
```bash
# Проверьте, что домен указывает на сервер
dig tlpn.shop

# Проверьте, что порт 80 открыт
sudo ufw status | grep 80

# Запустите в тестовом режиме
sudo certbot certonly --staging --webroot -w /var/www/certbot -d tlpn.shop
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
openssl s_client -connect tlpn.shop:443 -servername tlpn.shop
```
