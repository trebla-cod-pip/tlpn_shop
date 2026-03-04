from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.contrib import messages as django_messages
from django import forms
from store.models import Category, Product, TelegramUser
from telegram_app.models import Message, VisitLog
from telegram_app.utils import send_telegram_message
from django.utils.text import slugify
import logging

logger = logging.getLogger(__name__)


class VisitLogInline(admin.TabularInline):
    """Inline история посещений для TelegramUser"""
    model = VisitLog
    extra = 0
    readonly_fields = ('status_badge', 'platform', 'opened_at', 'closed_at', 'duration_display', 'start_param')
    fields = ('status_badge', 'platform', 'opened_at', 'closed_at', 'duration_display', 'start_param')
    ordering = ('-opened_at',)
    max_num = 10  # Показываем последние 10 посещений
    can_delete = False

    def status_badge(self, obj):
        if obj.status == 'closed':
            return '✓ Закрыто'
        return '○ Открыто'
    status_badge.short_description = 'Статус'

    def duration_display(self, obj):
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            if minutes > 0:
                return f'{minutes}м {seconds}с'
            return f'{seconds}с'
        return '—'
    duration_display.short_description = 'Длительность'

    def has_add_permission(self, request, obj=None):
        return False


class MessageInline(admin.TabularInline):
    """Inline история сообщений для TelegramUser"""
    model = Message
    extra = 0
    readonly_fields = ('direction_badge', 'status_badge', 'text_preview', 'sent_at', 'created_at')
    fields = ('direction_badge', 'status_badge', 'text_preview', 'sent_at', 'created_at')
    ordering = ('-created_at',)
    max_num = 10  # Показываем последние 10 сообщений
    can_delete = False

    def direction_badge(self, obj):
        if obj.direction == 'outgoing':
            return '→ Исх.'
        return '← Вх.'
    direction_badge.short_description = 'Напр.'

    def status_badge(self, obj):
        status_colors = {
            'pending': 'gray',
            'sent': 'orange',
            'delivered': 'green',
            'failed': 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        return format_html('<span style="color: {};">{}</span>', color, obj.get_status_display())
    status_badge.short_description = 'Статус'

    def text_preview(self, obj):
        text = obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
        return text
    text_preview.short_description = 'Текст'

    def has_add_permission(self, request, obj=None):
        return False


class BulkMessageForm(forms.Form):
    """Форма для массовой отправки сообщений"""
    text = forms.CharField(
        label='Текст сообщения',
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Введите текст сообщения...'}),
        help_text='Сообщение будет отправлено всем выбранным пользователям'
    )


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


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    """Админка для пользователей Telegram"""
    list_display = ('telegram_id', 'username_display', 'full_name', 'chat_id', 'is_premium', 'last_seen', 'created_at', 'visit_stats')
    list_filter = ('is_premium', 'created_at', 'last_seen')
    search_fields = ('telegram_id', 'username', 'first_name', 'last_name')
    readonly_fields = ('telegram_id', 'created_at', 'last_seen', 'visit_stats')
    ordering = ('-last_seen',)
    actions = ['send_message_to_users']
    inlines = [VisitLogInline, MessageInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('telegram_id', 'username', 'first_name', 'last_name', 'full_name', 'visit_stats')
        }),
        ('Дополнительно', {
            'fields': ('language_code', 'is_premium', 'chat_id')
        }),
        ('Даты', {
            'fields': ('created_at', 'last_seen')
        }),
    )

    def username_display(self, obj):
        return f'@{obj.username}' if obj.username else '—'
    username_display.short_description = 'Username'

    def full_name(self, obj):
        name = f'{obj.first_name} {obj.last_name}'.strip()
        return name if name else '—'
    full_name.short_description = 'ФИО'

    def visit_stats(self, obj):
        """Статистика посещений пользователя"""
        stats = VisitLog.get_user_stats(obj, days=30)
        if not stats or not stats.get('total_visits'):
            return 'Нет посещений за 30 дней'
        
        total = stats.get('total_visits', 0)
        avg_duration = stats.get('avg_duration')
        avg_str = ''
        if avg_duration:
            minutes = int(avg_duration) // 60
            seconds = int(avg_duration) % 60
            if minutes > 0:
                avg_str = f'{minutes}м {seconds}с'
            else:
                avg_str = f'{seconds}с'
        
        return f'{total} посещений за 30 дней (среднее: {avg_str})'
    visit_stats.short_description = 'Статистика посещений'

    def send_message_to_users(self, request, queryset):
        """Отправить сообщение выбранным пользователям"""
        users_with_chat_id = queryset.filter(chat_id__isnull=False)
        users_without_chat_id = queryset.filter(chat_id__isnull=True)

        if not users_with_chat_id:
            self.message_user(
                request,
                'У выбранных пользователей нет chat_id. Сообщения не будут отправлены.',
                level=django_messages.ERROR
            )
            return

        # Создаем форму для ввода текста
        if request.POST.get('apply'):
            form = BulkMessageForm(request.POST)
            if form.is_valid():
                text = form.cleaned_data['text']
                sent_count = 0
                failed_count = 0

                for user in users_with_chat_id:
                    # Создаем запись о сообщении
                    message = Message.objects.create(
                        telegram_user=user,
                        text=text,
                        direction='outgoing',
                        status='pending'
                    )

                    # Отправляем сообщение
                    success = send_telegram_message(user.chat_id, text)

                    if success:
                        message.status = 'sent'
                        message.sent_at = timezone.now()
                        message.save(update_fields=['status', 'sent_at'])
                        sent_count += 1
                    else:
                        message.status = 'failed'
                        message.save(update_fields=['status'])
                        failed_count += 1

                # Сообщение о результате
                result_text = f'Отправлено: {sent_count}'
                if failed_count > 0:
                    result_text += f', Не отправлено: {failed_count}'
                if users_without_chat_id:
                    result_text += f', Без chat_id: {users_without_chat_id.count()}'

                self.message_user(request, result_text)
                return None

        # Показываем форму
        form = BulkMessageForm()
        context = {
            'form': form,
            'users_count': users_with_chat_id.count(),
            'title': 'Отправить сообщение',
            'queryset': queryset,
        }

        # Рендерим страницу с формой
        from django.template.response import TemplateResponse
        return TemplateResponse(request, 'admin/send_message.html', context)

    send_message_to_users.short_description = 'Отправить сообщение выбранным пользователям'


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
    list_display = ('name', 'slug', 'price', 'old_price', 'category', 'is_active', 'is_featured', 'stock', 'display_order', 'created_at')
    list_filter = ('is_active', 'is_featured', 'category', 'created_at')
    search_fields = ('name', 'description', 'tags')
    prepopulated_fields = {}  # Отключаем стандартное prepopulated
    ordering = ('display_order', '-created_at',)
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
            'fields': ('is_active', 'is_featured', 'tags', 'display_order')
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
