#!/bin/bash

# =============================================================================
# Tulpin Shop - Стартовый скрипт для запуска проекта
# =============================================================================
# Использование:
#   ./start.sh              - полный запуск (миграции + данные + сервер)
#   ./start.sh --no-data    - запуск без создания тестовых данных
#   ./start.sh --migrate    - только миграции
#   ./start.sh --data       - только создание тестовых данных
#   ./start.sh --clean      - очистить БД и начать заново
# =============================================================================

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для вывода
info() {
    echo -e "${BLUE}>>> $1${NC}"
}

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

# Проверка наличия Python
check_python() {
    if command -v python &> /dev/null; then
        PYTHON_CMD=python
    elif command -v python3 &> /dev/null; then
        PYTHON_CMD=python3
    else
        error "Python не найден! Установите Python 3.10+"
        exit 1
    fi
    info "Используется: $($PYTHON_CMD --version)"
}

# Проверка виртуального окружения
check_venv() {
    if [ -z "$VIRTUAL_ENV" ]; then
        warning "Виртуальное окружение не активировано"
        info "Рекомендуется создать и активировать venv:"
        echo "   python -m venv venv"
        echo "   source venv/bin/activate  (Linux/Mac)"
        echo "   venv\Scripts\activate     (Windows)"
        echo ""
    else
        success "Виртуальное окружение: $VIRTUAL_ENV"
    fi
}

# Установка зависимостей
install_deps() {
    info "Установка зависимостей..."
    $PYTHON_CMD -m pip install -q -r requirements.txt
    success "Зависимости установлены"
}

# Применение миграций
run_migrations() {
    info "Применение миграций..."
    $PYTHON_CMD manage.py migrate
    success "Миграции применены"
}

# Создание суперпользователя (интерактивно)
create_superuser() {
    info "Создание суперпользователя..."
    echo "Создайте администратора для доступа к Django Admin"
    $PYTHON_CMD manage.py createsuperuser
    success "Суперпользователь создан"
}

# Заполнение тестовыми данными
load_test_data() {
    info "Заполнение тестовыми данными..."
    $PYTHON_CMD manage.py shell < create_test_data.py
    success "Тестовые данные созданы"
}

# Очистка базы данных
clean_db() {
    warning "Очистка базы данных..."
    rm -f db.sqlite3
    info "База данных удалена"
}

# Сбор статических файлов (для production)
collect_static() {
    info "Сбор статических файлов..."
    $PYTHON_CMD manage.py collectstatic --noinput
    success "Статические файлы собраны"
}

# Запуск сервера
run_server() {
    info "Запуск Django сервера..."
    echo ""
    echo "================================================="
    echo "  Сервер запущен!"
    echo "  - Основной сайт: http://localhost:8000"
    echo "  - Admin панель:  http://localhost:8000/admin"
    echo "  - API:           http://localhost:8000/api/"
    echo "================================================="
    echo ""
    $PYTHON_CMD manage.py runserver
}

# Помощь
show_help() {
    echo "Tulpin Shop - стартовый скрипт"
    echo ""
    echo "Использование:"
    echo "  ./start.sh              - полный запуск проекта"
    echo "  ./start.sh --no-data    - запуск без тестовых данных"
    echo "  ./start.sh --migrate    - только миграции"
    echo "  ./start.sh --data       - только тестовые данные"
    echo "  ./start.sh --clean      - очистить БД и начать заново"
    echo "  ./start.sh --help       - показать эту справку"
    echo ""
}

# =============================================================================
# Основная логика
# =============================================================================

main() {
    echo ""
    echo "================================================="
    echo "         TULPIN SHOP - Startup Script"
    echo "================================================="
    echo ""

    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --clean)
            clean_db
            check_python
            check_venv
            install_deps
            run_migrations
            create_superuser
            load_test_data
            run_server
            ;;
        --migrate)
            check_python
            run_migrations
            ;;
        --data)
            check_python
            load_test_data
            ;;
        --no-data)
            check_python
            check_venv
            run_migrations
            run_server
            ;;
        "")
            # Полный запуск по умолчанию
            check_python
            check_venv
            install_deps
            run_migrations
            load_test_data
            run_server
            ;;
        *)
            error "Неизвестная опция: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
