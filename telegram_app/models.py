from django.db import models
from django.utils import timezone
from store.models import TelegramUser
from datetime import timedelta


class Message(models.Model):
    """
    Сообщение пользователю Telegram
    Хранит историю отправленных сообщений
    """
    DIRECTION_CHOICES = (
        ('outgoing', 'Исходящее'),
        ('incoming', 'Входящее'),
    )

    STATUS_CHOICES = (
        ('pending', 'Ожидает отправки'),
        ('sent', 'Отправлено'),
        ('delivered', 'Доставлено'),
        ('failed', 'Ошибка отправки'),
    )

    # Получатель/отправитель
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Telegram пользователь'
    )

    # Направление сообщения
    direction = models.CharField(
        max_length=10,
        choices=DIRECTION_CHOICES,
        default='outgoing',
        verbose_name='Направление'
    )

    # Текст сообщения
    text = models.TextField(verbose_name='Текст сообщения')

    # Статус отправки
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )

    # Telegram message_id (если отправлено)
    telegram_message_id = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='ID сообщения в Telegram'
    )

    # Даты
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата отправки')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['telegram_user', '-created_at']),
            models.Index(fields=['direction', 'status']),
        ]

    def __str__(self):
        direction_icon = '→' if self.direction == 'outgoing' else '←'
        return f'{direction_icon} {self.telegram_user} ({self.get_status_display()})'

    def mark_as_delivered(self):
        """
        Помечает сообщение как доставленное.
        Вызывается при активности пользователя после отправки сообщения.
        """
        if self.status == 'sent' and self.direction == 'outgoing':
            self.status = 'delivered'
            self.save(update_fields=['status'])
            return True
        return False

    @classmethod
    def mark_user_messages_as_delivered(cls, telegram_user):
        """
        Помечает все отправленные сообщения пользователя как доставленные.
        Вызывается при любой активности пользователя (сообщение боту, открытие Mini App).
        """
        messages = cls.objects.filter(
            telegram_user=telegram_user,
            direction='outgoing',
            status='sent'
        )
        count = messages.count()
        messages.update(status='delivered')
        return count


class VisitLog(models.Model):
    """
    Журнал посещений Mini App
    Отслеживает сессии пользователей: открытие и закрытие приложения
    """
    SESSION_STATUS_CHOICES = (
        ('opened', 'Открыто'),
        ('closed', 'Закрыто'),
        ('active', 'Активно'),
    )

    PLATFORM_CHOICES = (
        ('android', 'Android'),
        ('ios', 'iOS'),
        ('web', 'Web'),
        ('desktop', 'Desktop'),
        ('unknown', 'Unknown'),
    )

    # Пользователь
    telegram_user = models.ForeignKey(
        TelegramUser,
        on_delete=models.CASCADE,
        related_name='visit_logs',
        verbose_name='Telegram пользователь'
    )

    # Сессия
    session_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='ID сессии'
    )

    # Статус
    status = models.CharField(
        max_length=10,
        choices=SESSION_STATUS_CHOICES,
        default='opened',
        verbose_name='Статус'
    )

    # Платформа
    platform = models.CharField(
        max_length=20,
        choices=PLATFORM_CHOICES,
        default='unknown',
        verbose_name='Платформа'
    )

    # Время
    opened_at = models.DateTimeField(auto_now_add=True, verbose_name='Время открытия')
    closed_at = models.DateTimeField(blank=True, null=True, verbose_name='Время закрытия')

    # Длительность сессии (в секундах, вычисляется)
    duration = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Длительность (сек)'
    )

    # Дополнительные данные
    start_param = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Параметр запуска (start_param)'
    )
    user_agent = models.TextField(blank=True, verbose_name='User Agent')

    class Meta:
        verbose_name = 'Журнал посещений'
        verbose_name_plural = 'Журналы посещений'
        ordering = ['-opened_at']
        indexes = [
            models.Index(fields=['telegram_user', '-opened_at']),
            models.Index(fields=['status', 'opened_at']),
            models.Index(fields=['session_id']),
        ]

    def __str__(self):
        status_icon = '✓' if self.status == 'closed' else '○'
        duration_str = f'{self.duration}s' if self.duration else 'active'
        return f'{status_icon} {self.telegram_user} - {self.opened_at.strftime("%d.%m.%Y %H:%M")} ({duration_str})'

    def save(self, *args, **kwargs):
        # Вычисляем длительность сессии при закрытии
        if self.status == 'closed' and self.closed_at and not self.duration:
            delta = self.closed_at - self.opened_at
            self.duration = int(delta.total_seconds())
        super().save(*args, **kwargs)

    @classmethod
    def log_open(cls, telegram_user, session_id='', platform='unknown', start_param='', user_agent=''):
        """
        Создаёт запись об открытии Mini App
        """
        return cls.objects.create(
            telegram_user=telegram_user,
            session_id=session_id,
            status='opened',
            platform=platform,
            start_param=start_param,
            user_agent=user_agent[:1000] if user_agent else ''
        )

    @classmethod
    def close_session(cls, telegram_user, session_id=''):
        """
        Закрывает активную сессию пользователя
        Возвращает количество закрытых сессий
        """
        from django.utils import timezone
        
        filters = {
            'telegram_user': telegram_user,
            'status': 'opened'
        }
        if session_id:
            filters['session_id'] = session_id
        
        sessions = cls.objects.filter(**filters)
        count = sessions.count()
        
        for session in sessions:
            session.status = 'closed'
            session.closed_at = timezone.now()
            session.save(update_fields=['status', 'closed_at'])
        
        return count

    @classmethod
    def get_user_stats(cls, telegram_user, days=30):
        """
        Возвращает статистику посещений пользователя за период
        """
        from django.utils import timezone
        from django.db.models import Count, Avg, Sum
        
        cutoff_date = timezone.now() - timedelta(days=days)
        
        stats = cls.objects.filter(
            telegram_user=telegram_user,
            opened_at__gte=cutoff_date
        ).aggregate(
            total_visits=Count('id'),
            closed_visits=Count('id', filter=models.Q(status='closed')),
            avg_duration=Avg('duration'),
            total_duration=Sum('duration')
        )
        
        return stats
