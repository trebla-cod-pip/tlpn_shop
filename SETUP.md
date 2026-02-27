# =============================================================================
# Tulpin Shop - Setup Instructions
# =============================================================================

## 🚀 Быстрый старт (локальная разработка)

### 1. Клонировать репозиторий
```bash
git clone <repository-url>
cd tulpin
```

### 2. Создать виртуальное окружение
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows
```

### 3. Установить зависимости
```bash
pip install -r requirements.txt
```

### 4. Настроить переменные окружения
```bash
# Скопировать шаблон
cp .env.example .env

# Отредактировать .env (раскомментировать нужные переменные)
# SECRET_KEY=ваш-secret-key
# DJANGO_DEBUG=True
# TELEGRAM_BOT_TOKEN=...
```

### 5. Применить миграции
```bash
python manage.py migrate
```

### 6. Создать суперпользователя
```bash
python manage.py createsuperuser
```

### 7. Запустить сервер
```bash
python manage.py runserver
```

### 8. Запустить Telegram бота (в отдельном терминале)
```bash
python manage.py starttelegram
```

---

## 📁 Структура файлов

```
tulpin/
├── .env                      # Переменные окружения (НЕ КОММИТИТЬ!)
├── .env.example              # Шаблон переменных
├── .gitignore                # Игнорируемые файлы
├── db.sqlite3                # База данных (НЕ КОММИТИТЬ!)
├── manage.py
├── requirements.txt
├── config/
│   ├── settings.py           # Основные настройки (можно коммитить)
│   ├── local_settings.py     # Локальные настройки (НЕ КОММИТИТЬ!)
│   └── local_settings.py.example  # Шаблон локальных настроек
├── staticfiles/              # Собранная статика (НЕ КОММИТИТЬ!)
├── media/                    # Загруженные файлы (НЕ КОММИТИТЬ!)
└── ...
```

---

## 🔐 Безопасность

**Никогда не коммитьте в git:**
- `.env` файлы с секретными ключами
- `db.sqlite3` базу данных
- `local_settings.py` локальные настройки
- `media/` загруженные пользователями файлы
- `staticfiles/` собранную статику

**Можно коммитить:**
- `.env.example` шаблон переменных
- `settings.py` базовые настройки
- `local_settings.py.example` шаблон локальных настроек
- Код приложения

---

## 🛠 Production развёртывание

См. `DEPLOY.md` для инструкций по развёртыванию на сервере.

### Кратко:
1. Склонировать репозиторий на сервер
2. Создать `.env` с production значениями
3. Запустить `sudo ./deploy.sh`
4. Скрипт всё настроит автоматически

---

## ❓ Troubleshooting

### ModuleNotFoundError
```bash
pip install -r requirements.txt
```

### Database locked
```bash
rm db.sqlite3
python manage.py migrate
```

### Static files not found
```bash
python manage.py collectstatic --noinput
```

### Telegram bot не работает
Проверьте токен в `.env` и что бот запущен:
```bash
python manage.py starttelegram
```
