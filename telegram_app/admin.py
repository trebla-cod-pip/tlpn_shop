from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils import timezone
from django.contrib import messages as django_messages
import logging

from telegram_app.models import Message, VisitLog
from telegram_app.forms import MessageAdminForm
from telegram_app.utils import send_telegram_message

logger = logging.getLogger(__name__)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Админка для сообщений Telegram"""
    list_display = ('telegram_user', 'direction_badge', 'status_badge', 'text_preview', 'sent_at', 'created_at')
    list_filter = ('direction', 'status', 'created_at')
    search_fields = ('text', 'telegram_user__username', 'telegram_user__first_name', 'telegram_user__last_name')
    readonly_fields = ('telegram_message_id', 'sent_at', 'created_at', 'send_status', 'delivery_info')
    ordering = ('-created_at',)
    form = MessageAdminForm

    fieldsets = (
        ('Получатель', {
            'fields': ('telegram_user', 'direction')
        }),
        ('Сообщение', {
            'fields': ('text',)
        }),
        ('Статус', {
            'fields': ('status', 'send_status', 'delivery_info', 'telegram_message_id', 'sent_at', 'created_at')
        }),
    )

    actions = ['send_selected_messages', 'mark_as_delivered']

    def direction_badge(self, obj):
        """Иконка направления сообщения"""
        if obj.direction == 'outgoing':
            return mark_safe('<span style="color: green;">→ Исходящее</span>')
        return mark_safe('<span style="color: blue;">← Входящее</span>')
    direction_badge.short_description = 'Направление'

    def status_badge(self, obj):
        """Иконка статуса сообщения"""
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
        """Предпросмотр текста"""
        text = obj.text[:50] + '...' if len(obj.text) > 50 else obj.text
        return text
    text_preview.short_description = 'Текст'

    def send_status(self, obj):
        """Кнопка для повторной отправки"""
        if obj.status == 'failed' or obj.status == 'pending':
            return format_html(
                '<a href="/admin/telegram_app/message/{}/send/" class="button">Отправить</a>',
                obj.pk
            )
        return 'Отправлено'
    send_status.short_description = 'Действия'

    def delivery_info(self, obj):
        """Информация о доставке"""
        from django.utils.safestring import mark_safe
        
        if obj.direction == 'incoming':
            return 'Входящее сообщение'

        info = []
        if obj.status == 'sent':
            info.append('⏳ Ожидает подтверждения доставки')
            info.append('Статус изменится на "Доставлено" при следующей активности пользователя')
        elif obj.status == 'delivered':
            if obj.sent_at:
                info.append('✓ Сообщение доставлено')
        elif obj.status == 'failed':
            info.append('✗ Ошибка отправки')
        elif obj.status == 'pending':
            info.append('⏳ Ожидает отправки')

        if info:
            return mark_safe('<br>'.join(info))
        return '—'
    delivery_info.short_description = 'Информация о доставке'

    def send_selected_messages(self, request, queryset):
        """Отправить выбранные сообщения"""
        pending_messages = queryset.filter(status__in=['pending', 'failed'])
        sent_count = 0
        failed_count = 0

        for message in pending_messages:
            if message.direction == 'outgoing':
                success = self._send_message(message)
                if success:
                    sent_count += 1
                else:
                    failed_count += 1

        if sent_count > 0:
            self.message_user(request, f'Успешно отправлено: {sent_count}')
        if failed_count > 0:
            self.message_user(request, f'Не удалось отправить: {failed_count}', level=django_messages.ERROR)

    send_selected_messages.short_description = 'Отправить выбранные сообщения'

    def mark_as_delivered(self, request, queryset):
        """Пометить выбранные сообщения как доставленные"""
        count = 0
        for message in queryset.filter(status='sent', direction='outgoing'):
            message.status = 'delivered'
            message.save(update_fields=['status'])
            count += 1
        self.message_user(request, f'Помечено {count} сообщений как доставленные')

    mark_as_delivered.short_description = 'Пометить как доставленные'

    def _send_message(self, message):
        """Отправляет сообщение в Telegram"""
        if message.direction != 'outgoing':
            return False

        tg_user = message.telegram_user
        if not tg_user.chat_id:
            message.status = 'failed'
            message.save(update_fields=['status'])
            logger.warning(f"Message #{message.id}: Нет chat_id для пользователя {tg_user}")
            return False

        success = send_telegram_message(tg_user.chat_id, message.text)

        if success:
            message.status = 'sent'
            message.sent_at = timezone.now()
            message.save(update_fields=['status', 'sent_at'])
            logger.info(f"Message #{message.id}: Отправлено пользователю {tg_user}")
        else:
            message.status = 'failed'
            message.save(update_fields=['status'])
            logger.error(f"Message #{message.id}: Ошибка отправки пользователю {tg_user}")

        return success

    def save_model(self, request, obj, form, change):
        """При сохранении исходящего сообщения - отправляем его"""
        super().save_model(request, obj, form, change)

        if obj.direction == 'outgoing' and obj.status == 'pending':
            self._send_message(obj)


@admin.register(VisitLog)
class VisitLogAdmin(admin.ModelAdmin):
    """Админка для журнала посещений"""
    list_display = ('telegram_user', 'status_badge', 'platform_icon', 'session_id_display', 'opened_at', 'closed_at', 'duration_display')
    list_filter = ('status', 'platform', 'opened_at')
    search_fields = ('telegram_user__username', 'telegram_user__first_name', 'telegram_user__last_name', 'session_id')
    readonly_fields = ('telegram_user', 'session_id', 'status', 'platform', 'opened_at', 'closed_at', 'duration', 'start_param', 'user_agent')
    ordering = ('-opened_at',)
    date_hierarchy = 'opened_at'
    list_per_page = 50

    fieldsets = (
        ('Сессия', {
            'fields': ('telegram_user', 'session_id', 'status')
        }),
        ('Платформа', {
            'fields': ('platform', 'start_param')
        }),
        ('Время', {
            'fields': ('opened_at', 'closed_at', 'duration')
        }),
        ('Дополнительно', {
            'fields': ('user_agent',),
            'classes': ('collapse',)
        }),
    )

    def status_badge(self, obj):
        """Иконка статуса"""
        if obj.status == 'closed':
            return mark_safe('<span style="color: gray;">✓ Закрыто</span>')
        elif obj.status == 'opened':
            return mark_safe('<span style="color: green;">○ Открыто</span>')
        return mark_safe('<span style="color: orange;">⋅ Активно</span>')
    status_badge.short_description = 'Статус'

    def platform_icon(self, obj):
        """Иконка платформы"""
        icons = {
            'android': '🤖 Android',
            'ios': '🍎 iOS',
            'web': '🌐 Web',
            'desktop': '💻 Desktop',
            'unknown': '❓ Unknown',
        }
        return icons.get(obj.platform, obj.platform)
    platform_icon.short_description = 'Платформа'

    def session_id_display(self, obj):
        """Отображение session_id"""
        return obj.session_id[:20] + '...' if obj.session_id and len(obj.session_id) > 20 else (obj.session_id or '—')
    session_id_display.short_description = 'Session ID'

    def duration_display(self, obj):
        """Отображение длительности"""
        if obj.duration:
            minutes = obj.duration // 60
            seconds = obj.duration % 60
            if minutes > 0:
                return f'{minutes}м {seconds}с'
            return f'{seconds}с'
        return '—'
    duration_display.short_description = 'Длительность'

    def has_add_permission(self, request):
        """Запрет ручного добавления записей"""
        return False

    def has_change_permission(self, request, obj=None):
        """Запрет редактирования записей"""
        return False

    def has_delete_permission(self, request, obj=None):
        """Разрешить удаление только для админов"""
        return request.user.is_superuser
