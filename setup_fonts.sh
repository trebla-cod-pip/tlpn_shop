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
TEMP_DIR="/tmp/inter-fonts"

# Создание директорий
setup_dirs() {
    info "Создание директорий..."
    mkdir -p "$FONTS_DIR"
    mkdir -p "$CSS_DIR"
    mkdir -p "$TEMP_DIR"
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
        curl -sL "$url" -o "${TEMP_DIR}/${file}"

        if [ -f "${TEMP_DIR}/${file}" ] && [ -s "${TEMP_DIR}/${file}" ]; then
            success "  Inter-${weight}.woff2 загружен"
        else
            warning "  Не удалось загрузить Inter-${weight}.woff2"
        fi
    done
}

# Оптимизация шрифтов с помощью pyftsubset
optimize_fonts() {
    info "Оптимизация шрифтов (кириллица + латиница)..."

    # Проверяем наличие pyftsubset
    if ! command -v pyftsubset &> /dev/null; then
        warning "pyftsubset не найден. Установка fonttools..."
        pip install fonttools[woff] || {
            warning "Не удалось установить fonttools. Шрифты не оптимизированы."
            # Копируем оригиналы
            cp "${TEMP_DIR}"/*.woff2 "${FONTS_DIR}/" 2>/dev/null || true
            return
        }
    fi

    # Unicode диапазоны: латиница + кириллица
    UNICODE_RANGES="U+0000-00FF,U+0400-04FF"

    for weight in 300 400 500 600 700; do
        local src="${TEMP_DIR}/Inter-${weight}.woff2"
        local dst="${FONTS_DIR}/Inter-${weight}.woff2"

        if [ -f "$src" ]; then
            info "  Оптимизация: Inter-${weight}.woff2"
            pyftsubset "$src" \
                --output-file="$dst" \
                --unicodes="$UNICODE_RANGES" \
                --flavor=woff2 \
                --layout-features='*' \
                2>/dev/null || {
                warning "  Не удалось оптимизировать Inter-${weight}.woff2"
                cp "$src" "$dst"
            }

            local orig_size=$(stat -c%s "$src" 2>/dev/null || stat -f%z "$src")
            local opt_size=$(stat -c%s "$dst" 2>/dev/null || stat -f%z "$dst")
            local saved=$(( (orig_size - opt_size) * 100 / orig_size ))
            success "  Inter-${weight}.woff2: ${orig_size}Б → ${opt_size}Б (экономия ${saved}%)"
        fi
    done

    # Очистка временных файлов
    rm -rf "$TEMP_DIR"
}

# Создание CSS файла с @font-face
create_css() {
    info "Создание CSS файла шрифтов..."

    cat > "${CSS_DIR}/fonts.css" <<'EOF'
/* Inter Font - Local с оптимизацией (кириллица + латиница) */
@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 300;
    font-display: swap;
    src: url('../fonts/Inter-300.woff2') format('woff2');
    unicode-range: U+0000-00FF, U+0400-04FF;
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 400;
    font-display: swap;
    src: url('../fonts/Inter-400.woff2') format('woff2');
    unicode-range: U+0000-00FF, U+0400-04FF;
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 500;
    font-display: swap;
    src: url('../fonts/Inter-500.woff2') format('woff2');
    unicode-range: U+0000-00FF, U+0400-04FF;
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 600;
    font-display: swap;
    src: url('../fonts/Inter-600.woff2') format('woff2');
    unicode-range: U+0000-00FF, U+0400-04FF;
}

@font-face {
    font-family: 'Inter';
    font-style: normal;
    font-weight: 700;
    font-display: swap;
    src: url('../fonts/Inter-700.woff2') format('woff2');
    unicode-range: U+0000-00FF, U+0400-04FF;
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
    optimize_fonts
    create_css
    update_template
    collect_static
    show_summary
}

main "$@"


