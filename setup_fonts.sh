#!/bin/bash

# =============================================================================
# Tulpin Shop - Скачивание и установка шрифтов
# =============================================================================
# Шрифт: Inter (Google Fonts)
# Использование: ./setup_fonts.sh
# =============================================================================

set -e

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info() { echo -e "${BLUE}>>> $1${NC}"; }
success() { echo -e "${GREEN}✓ $1${NC}"; }
warning() { echo -e "${YELLOW}⚠ $1${NC}"; }
error() { echo -e "${RED}✗ $1${NC}"; }

# Переменные
FONTS_DIR="static/fonts"
CSS_DIR="static/css"

# Создание директорий
setup_dirs() {
    info "Создание директорий..."
    mkdir -p "$FONTS_DIR"
    mkdir -p "$CSS_DIR"
    success "Директории созданы"
}

# Скачивание шрифтов Inter
download_fonts() {
    info "Скачивание шрифтов Inter..."
    
    # URL для скачивания (WOFF2 - современный формат)
    BASE_URL="https://github.com/rsms/inter/raw/master/docs/font-files"
    
    # Веса шрифтов (300, 400, 500, 600, 700)
    WEIGHTS=(300 400 500 600 700)
    
    for weight in "${WEIGHTS[@]}"; do
        local file="Inter-${weight}.woff2"
        local url="${BASE_URL}/${file}"
        
        info "  Загрузка: Inter-${weight}.woff2"
        curl -sL "$url" -o "${FONTS_DIR}/${file}"
        
        if [ -f "${FONTS_DIR}/${file}" ] && [ -s "${FONTS_DIR}/${file}" ]; then
            success "  Inter-${weight}.woff2 загружен"
        else
            warning "  Не удалось загрузить Inter-${weight}.woff2"
        fi
    done
    
    # Дополнительный вариант через Google Fonts CDN
    if [ ! -f "${FONTS_DIR}/Inter-400.woff2" ]; then
        info "Альтернативная загрузка через Google Fonts..."
        
        # Прямые ссылки на Google Fonts
        curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuLyfAZ9hjp-Ek-_EeA.woff2" -o "${FONTS_DIR}/Inter-400.woff2"
        curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuGKYMZ9hjp-Ek-_EeA.woff2" -o "${FONTS_DIR}/Inter-500.woff2"
        curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuI6fMZ9hjp-Ek-_EeA.woff2" -o "${FONTS_DIR}/Inter-600.woff2"
        curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuFuYMZ9hjp-Ek-_EeA.woff2" -o "${FONTS_DIR}/Inter-700.woff2"
        curl -sL "https://fonts.gstatic.com/s/inter/v18/UcCO3FwrK3iLTeHuS_fvQtMwCp50KnMw2boKoduKmMEVuOKfMZ9hjp-Ek-_EeA.woff2" -o "${FONTS_DIR}/Inter-300.woff2"
        
        success "Шрифты загружены через Google Fonts"
    fi
}

# Создание CSS файла с @font-face
create_css() {
    info "Создание CSS файла шрифтов..."
    
    cat > "${CSS_DIR}/fonts.css" <<'EOF'
/* Inter Font - Local */
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 300;
    font-display: swap;
    src: url('../fonts/Inter-300.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('../fonts/Inter-400.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 500;
    font-display: swap;
    src: url('../fonts/Inter-500.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url('../fonts/Inter-600.woff2') format('woff2');
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 700;
    font-display: swap;
    src: url('../fonts/Inter-700.woff2') format('woff2');
}
EOF
    
    success "CSS файл создан: ${CSS_DIR}/fonts.css"
}

# Обновление шаблона base.html
update_template() {
    info "Updating base.html template..."

    if grep -q "static 'css/fonts.css'" templates/base.html; then
        success "Template already configured for local fonts"
        return
    fi

    # Insert local fonts stylesheet right after <head>
    sed -i '/<head>/a\    <!-- Local Fonts -->\n    <link rel="stylesheet" href="{% static '\''css/fonts.css'\'' %}">' templates/base.html

    success "Template updated: local fonts enabled"
}
# Сбор статических файлов
collect_static() {
    info "Сбор статических файлов..."
    
    if [ -f "manage.py" ]; then
        STATIC_ROOT="${STATIC_ROOT:-/var/www/tlpn_shop/static}" python manage.py collectstatic --noinput
        success "Статические файлы собраны"
    else
        warning "manage.py не найден"
    fi
}

# Показать итог
show_summary() {
    echo ""
    echo "================================================="
    echo "         Шрифты установлены"
    echo "================================================="
    echo ""
    echo "Скачанные файлы:"
    ls -la "${FONTS_DIR}/" 2>/dev/null || echo "  (пусто)"
    echo ""
    echo "CSS файл:"
    ls -la "${CSS_DIR}/" 2>/dev/null || echo "  (пусто)"
    echo ""
    echo "Для использования на production:"
    echo "  1. Загрузите папку static/ на сервер"
    echo "  2. Nginx будет отдавать шрифты из /static/fonts/"
    echo ""
}

# =============================================================================
# Основная логика
# =============================================================================

main() {
    echo ""
    echo "================================================="
    echo "    TULPIN SHOP - Font Setup"
    echo "================================================="
    echo ""
    
    setup_dirs
    download_fonts
    create_css
    update_template
    collect_static
    show_summary
}

main "$@"


