from django.contrib import admin
from django.contrib import messages
from django.utils.html import format_html
from store.models import Category, Product
from django.utils.text import slugify
import logging

logger = logging.getLogger(__name__)


def translit_slug(text):
    """Транслитерация русских букв в slug"""
    translits = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        ' ': '-', '_': '',
    }
    text = text.lower()
    for ru, en in translits.items():
        text = text.replace(ru, en)
    result = ''
    for char in text:
        if char.isalnum() or char in '-_':
            result += char
    return result.strip('-')


@admin.action(description='🔄 Сгенерировать WebP изображения для выбранных товаров')
def generate_webp_images(modeladmin, request, queryset):
    """
    Генерирует WebP изображения для выбранных товаров
    """
    from imagekit.cachefiles import ImageCacheFile
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    
    for product in queryset:
        if not product.image:
            skipped_count += 1
            continue
        
        try:
            # Генерируем image_webp_400
            if product.image_webp_400:
                product.image_webp_400.generate()
            
            # Генерируем image_webp_800
            if product.image_webp_800:
                product.image_webp_800.generate()
            
            success_count += 1
            logger.info(f"WebP сгенерировано для товара: {product.name}")
        except Exception as e:
            error_count += 1
            logger.error(f"Ошибка генерации WebP для {product.name}: {e}")
    
    # Выводим сообщение
    if success_count > 0:
        modeladmin.message_user(request, f"✅ Успешно сгенерировано: {success_count}", messages.SUCCESS)
    if error_count > 0:
        modeladmin.message_user(request, f"❌ Ошибок: {error_count}", messages.ERROR)
    if skipped_count > 0:
        modeladmin.message_user(request, f"⚠️ Пропущено (нет изображения): {skipped_count}", messages.WARNING)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    prepopulated_fields = {}  # Отключаем стандартное prepopulated
    ordering = ('name',)

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            obj.slug = translit_slug(obj.name)
        super().save_model(request, obj, form, change)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'old_price', 'category', 'is_active', 'is_featured', 'stock', 'created_at', 'has_webp')
    list_filter = ('is_active', 'is_featured', 'category', 'created_at')
    search_fields = ('name', 'description', 'tags')
    prepopulated_fields = {}  # Отключаем стандартное prepopulated
    ordering = ('-created_at',)
    readonly_fields = ('discount', 'created_at', 'updated_at')
    actions = [generate_webp_images]

    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'old_price', 'stock', 'discount')
        }),
        ('Изображения', {
            'fields': ('image', 'cart_image', 'webp_status')
        }),
        ('Настройки отображения', {
            'fields': ('is_active', 'is_featured', 'tags')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        if not obj.slug:
            base_slug = translit_slug(obj.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            obj.slug = slug
        super().save_model(request, obj, form, change)
    
    def has_webp(self, obj):
        """Показывает статус WebP изображений"""
        if not obj.image:
            return format_html('<span style="color: #999;">Нет изображения</span>')
        
        # Проверяем наличие URL без вызова исключения
        try:
            url_400 = None
            url_800 = None
            
            if obj.image_webp_400:
                try:
                    url_400 = obj.image_webp_400.url
                except:
                    pass
            
            if obj.image_webp_800:
                try:
                    url_800 = obj.image_webp_800.url
                except:
                    pass
            
            if url_400 and url_800:
                return format_html('<span style="color: green;">✅ 400px | ✅ 800px</span>')
            elif url_400:
                return format_html('<span style="color: orange;">✅ 400px | ❌ 800px</span>')
            elif url_800:
                return format_html('<span style="color: orange;">❌ 400px | ✅ 800px</span>')
            else:
                return format_html('<span style="color: red;">❌ Не сгенерировано</span>')
        except Exception as e:
            return format_html('<span style="color: red;">Ошибка</span>')
    has_webp.short_description = 'WebP статус'
    
    def webp_status(self, obj):
        """Развёрнутая информация о WebP для отображения в форме"""
        if not obj.image:
            return 'Изображение не загружено'
        
        try:
            status = []
            
            if obj.image_webp_400:
                try:
                    status.append(f'✅ 400px: {obj.image_webp_400.url}')
                except:
                    status.append('❌ 400px: не сгенерировано')
            else:
                status.append('❌ 400px: не сгенерировано')
                
            if obj.image_webp_800:
                try:
                    status.append(f'✅ 800px: {obj.image_webp_800.url}')
                except:
                    status.append('❌ 800px: не сгенерировано')
            else:
                status.append('❌ 800px: не сгенерировано')
            
            return format_html('<br>'.join(status))
        except Exception as e:
            return format_html('<span style="color: red;">Ошибка</span>')
    webp_status.short_description = 'Статус генерации WebP'
