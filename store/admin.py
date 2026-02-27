from django.contrib import admin
from store.models import Category, Product
from django.utils.text import slugify


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
    list_display = ('name', 'slug', 'price', 'old_price', 'category', 'is_active', 'is_featured', 'stock', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category', 'created_at')
    search_fields = ('name', 'description', 'tags')
    prepopulated_fields = {}  # Отключаем стандартное prepopulated
    ordering = ('-created_at',)
    readonly_fields = ('discount', 'created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'description', 'category')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'old_price', 'stock', 'discount')
        }),
        ('Изображения', {
            'fields': ('image', 'cart_image')
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
