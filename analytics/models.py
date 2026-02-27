"""
Система аналитики для Django E-commerce
Без Celery/Redis - агрегации через management команды
"""
import hashlib
import hmac
from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey


# ============================================================================
# БЛОК 1: Модели для сбора сырых данных трекинга
# ============================================================================

class TrackingSession(models.Model):
    """
    Сессия пользователя
    """
    session_key = models.CharField(max_length=64, unique=True, db_index=True, verbose_name='Ключ сессии')
    user = models.ForeignKey(
        'auth.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tracking_sessions', verbose_name='Пользователь'
    )
    
    # Источники трафика
    utm_source = models.CharField(max_length=100, blank=True, verbose_name='UTM Source')
    utm_medium = models.CharField(max_length=100, blank=True, verbose_name='UTM Medium')
    utm_campaign = models.CharField(max_length=200, blank=True, verbose_name='UTM Campaign')
    utm_term = models.CharField(max_length=200, blank=True, verbose_name='UTM Term')
    utm_content = models.CharField(max_length=200, blank=True, verbose_name='UTM Content')
    referer = models.URLField(blank=True, max_length=500, verbose_name='Referer')
    landing_page = models.URLField(blank=True, max_length=500, verbose_name='Целевая страница')
    
    # Технические данные
    ip_hash = models.CharField(max_length=64, db_index=True, verbose_name='Хеш IP')  # SHA256 хеш IP
    user_agent = models.TextField(blank=True, verbose_name='User Agent')
    device_type = models.CharField(max_length=20, default='unknown', choices=[
        ('desktop', 'Компьютер'),
        ('mobile', 'Мобильный'),
        ('tablet', 'Планшет'),
        ('unknown', 'Неизвестно'),
    ], verbose_name='Тип устройства')
    browser = models.CharField(max_length=50, blank=True, verbose_name='Браузер')
    os = models.CharField(max_length=50, blank=True, verbose_name='ОС')
    
    # Временные метки
    started_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Начало')
    last_activity = models.DateTimeField(auto_now=True, verbose_name='Последняя активность')
    ended_at = models.DateTimeField(null=True, blank=True, db_index=True, verbose_name='Окончание')
    
    # Статус
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Активна')
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Сессия'
        verbose_name_plural = 'Сессии'
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['user', '-started_at']),
            models.Index(fields=['utm_source', '-started_at']),
            models.Index(fields=['is_active', '-last_activity']),
        ]
    
    def __str__(self):
        return f"Сессия {self.session_key[:8]}... ({self.user or 'Аноним'})"
    
    @property
    def duration_seconds(self):
        """Длительность сессии в секундах"""
        if self.ended_at:
            return int((self.ended_at - self.started_at).total_seconds())
        return int((timezone.now() - self.started_at).total_seconds())
    
    @property
    def traffic_source(self):
        """Определяет источник трафика"""
        if self.utm_source:
            return f"{self.utm_source}/{self.utm_medium}" if self.utm_medium else self.utm_source
        if 'google' in self.referer.lower():
            return 'organic/google'
        if 'yandex' in self.referer.lower():
            return 'organic/yandex'
        if 'facebook' in self.referer.lower() or 'instagram' in self.referer.lower():
            return 'social'
        if self.referer:
            return 'referral'
        return 'direct'


class TrackingEvent(models.Model):
    """
    Сырое событие трекинга
    Partitioning рекомендуется по started_at (месяц)
    """
    EVENT_TYPES = [
        ('page_view', 'Просмотр страницы'),
        ('scroll_depth', 'Глубина скролла'),
        ('click', 'Клик'),
        ('add_to_cart', 'Добавление в корзину'),
        ('remove_from_cart', 'Удаление из корзины'),
        ('checkout_start', 'Начало оформления'),
        ('checkout_step', 'Шаг оформления'),
        ('purchase', 'Покупка'),
        ('web_vital', 'Web Vitals'),
        ('custom', 'Другое'),
    ]
    
    session = models.ForeignKey(TrackingSession, on_delete=models.CASCADE, related_name='events', verbose_name='Сессия')
    user = models.ForeignKey(
        'auth.User', null=True, blank=True, on_delete=models.SET_NULL,
        related_name='tracking_events', verbose_name='Пользователь'
    )
    
    # Тип события
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, db_index=True, verbose_name='Тип события')
    event_name = models.CharField(max_length=100, db_index=True, verbose_name='Название события')
    
    # Контекст
    url = models.URLField(max_length=500, verbose_name='URL')
    page_title = models.CharField(max_length=500, blank=True, verbose_name='Заголовок страницы')
    
    # Дополнительные данные (JSON)
    meta = models.JSONField(default=dict, blank=True, verbose_name='Метаданные')
    
    # Временная метка
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Время создания')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Событие'
        verbose_name_plural = 'События'
        indexes = [
            models.Index(fields=['session', '-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
            models.Index(fields=['event_name', '-created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.get_event_type_display()}: {self.event_name} @ {self.url[:50]}"


# ============================================================================
# БЛОК 2: Агрегированные метрики (для быстрого доступа)
# ============================================================================

class AggregatedStat(models.Model):
    """
    Агрегированные статистики (рассчитываются periodically)
    """
    STAT_TYPES = [
        ('revenue', 'Выручка'),
        ('orders', 'Заказы'),
        ('sessions', 'Сессии'),
        ('visitors', 'Посетители'),
        ('conversion_rate', 'Конверсия'),
        ('aov', 'Средний чек'),
        ('cart_abandonment', 'Брошенные корзины'),
        ('checkout_abandonment', 'Отток на оформлении'),
        ('revenue_per_visitor', 'Выручка на посетителя'),
        ('ltv', 'LTV'),
        ('retention', 'Удержание'),
        ('churn', 'Отток'),
        ('romi', 'ROMI'),
        ('product_margin', 'Маржа товара'),
    ]

    GRANULARITIES = [
        ('hourly', 'Почасово'),
        ('daily', 'Ежедневно'),
        ('weekly', 'Еженедельно'),
        ('monthly', 'Ежемесячно'),
    ]

    # Период
    date = models.DateField(db_index=True, verbose_name='Дата')
    granularity = models.CharField(max_length=20, choices=GRANULARITIES, default='daily', verbose_name='Гранулярность')

    # Метрика
    stat_type = models.CharField(max_length=50, choices=STAT_TYPES, db_index=True, verbose_name='Тип метрики')

    # Измерения (JSON)
    dimensions = models.JSONField(default=dict, blank=True, db_index=True, verbose_name='Измерения')

    # Значение
    value = models.DecimalField(max_digits=20, decimal_places=4, verbose_name='Значение')

    # Дополнительная метрика для сравнения
    value_prev = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True, verbose_name='Пред. значение')

    # Количество записей в агрегации
    count = models.IntegerField(default=0, verbose_name='Количество')

    # Хеш dimensions для unique constraints
    dimensions_hash = models.CharField(max_length=32, blank=True, db_index=True, verbose_name='Хеш измерений')

    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    class Meta:
        unique_together = ['date', 'granularity', 'stat_type', 'dimensions_hash']
        verbose_name = 'Агрегированная статистика'
        verbose_name_plural = 'Агрегированные статистики'
        indexes = [
            models.Index(fields=['date', 'stat_type']),
            models.Index(fields=['stat_type', 'date']),
        ]

    def _calc_dimensions_hash(self):
        import json
        return hashlib.md5(json.dumps(self.dimensions, sort_keys=True).encode()).hexdigest()

    def save(self, *args, **kwargs):
        if not self.dimensions_hash:
            self.dimensions_hash = self._calc_dimensions_hash()
        super().save(*args, **kwargs)


# ============================================================================
# БЛОК 3: Customer Analytics (RFM, LTV, Cohorts)
# ============================================================================

class CustomerCohort(models.Model):
    """
    Когорта клиентов по месяцу первой покупки
    """
    cohort_month = models.DateField(unique=True)  # Первый день месяца
    customer_count = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # Retention по месяцам (JSON)
    # {1: 0.45, 2: 0.32, 3: 0.25, ...} - % вернувшихся в месяц N
    retention_rates = models.JSONField(default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-cohort_month']
    
    def __str__(self):
        return f"Cohort {self.cohort_month.strftime('%Y-%m')}"


class RFMSegment(models.Model):
    """
    RFM-сегментация клиентов
    Recency: дней с последней покупки
    Frequency: количество покупок
    Monetary: общая сумма покупок
    """
    SEGMENT_LABELS = {
        'champions': 'Champions',
        'loyal': 'Loyal Customers',
        'potential': 'Potential Loyalists',
        'new': 'New Customers',
        'promising': 'Promising',
        'need_attention': 'Need Attention',
        'about_to_sleep': 'About to Sleep',
        'at_risk': 'At Risk',
        'cant_lose': 'Can\'t Lose Them',
        'hibernating': 'Hibernating',
        'lost': 'Lost',
    }
    
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='rfm_segments')
    
    # RFM метрики
    recency = models.IntegerField()  # Дней с последней покупки
    frequency = models.IntegerField()  # Количество заказов
    monetary = models.DecimalField(max_digits=20, decimal_places=2)  # Общая сумма
    
    # RFM scores (1-5)
    r_score = models.IntegerField(default=1)
    f_score = models.IntegerField(default=1)
    m_score = models.IntegerField(default=1)
    rfm_score = models.IntegerField(default=1)  # Сумма scores
    
    # Сегмент
    segment = models.CharField(max_length=50, db_index=True)
    
    # Период расчёта
    calculated_at = models.DateTimeField(auto_now_add=True)
    cohort_month = models.DateField(null=True, blank=True)
    
    class Meta:
        ordering = ['-rfm_score']
        indexes = [
            models.Index(fields=['segment']),
            models.Index(fields=['user', '-calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.SEGMENT_LABELS.get(self.segment, self.segment)}"
    
    @classmethod
    def get_segment_label(cls, segment):
        return cls.SEGMENT_LABELS.get(segment, segment)


# ============================================================================
# БЛОК 4: Продуктовая аналитика
# ============================================================================

class ProductMarginStat(models.Model):
    """
    Статистика маржинальности товаров
    """
    product = models.ForeignKey('store.Product', on_delete=models.CASCADE, related_name='margin_stats')
    
    # Период
    date = models.DateField(db_index=True)
    
    # Метрики
    quantity_sold = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    cogs = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # Cost of Goods Sold
    margin = models.DecimalField(max_digits=20, decimal_places=2, default=0)  # revenue - cogs
    margin_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # ABC/XYZ категории
    abc_category = models.CharField(max_length=1, default='C')  # A, B, C
    xyz_category = models.CharField(max_length=1, default='Z')  # X, Y, Z
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['product', 'date']
        ordering = ['-margin']
        indexes = [
            models.Index(fields=['date', '-margin']),
            models.Index(fields=['abc_category']),
            models.Index(fields=['xyz_category']),
        ]
    
    def __str__(self):
        return f"{self.product} - {self.date} - Margin: {self.margin}"


# ============================================================================
# БЛОК 5: Воронка конверсии
# ============================================================================

class FunnelStep(models.Model):
    """
    Шаги воронки конверсии
    """
    STEPS = [
        (1, 'Главная / Landing'),
        (2, 'Каталог'),
        (3, 'Карточка товара'),
        (4, 'Корзина'),
        (5, 'Начало оформления'),
        (6, 'Доставка'),
        (7, 'Оплата'),
        (8, 'Заказ создан'),
        (9, 'Оплата подтверждена'),
    ]
    
    session = models.ForeignKey(TrackingSession, on_delete=models.CASCADE, related_name='funnel_steps')
    step = models.IntegerField(choices=STEPS)
    reached_at = models.DateTimeField(auto_now_add=True)
    
    # Дополнительные данные
    meta = models.JSONField(default=dict, blank=True)
    
    class Meta:
        unique_together = ['session', 'step']
        ordering = ['session', 'step']
        indexes = [
            models.Index(fields=['step', '-reached_at']),
        ]


# ============================================================================
# БЛОК 6: Каналы трафика и ROMI
# ============================================================================

class ChannelPerformance(models.Model):
    """
    Эффективность каналов трафика
    """
    channel = models.CharField(max_length=100, db_index=True)  # google/organic, facebook/ads, etc.
    date = models.DateField(db_index=True)
    
    # Метрики
    sessions = models.IntegerField(default=0)
    visitors = models.IntegerField(default=0)
    orders = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # Стоимость (вводится вручную или через API)
    cost = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    
    # Рассчитанные метрики
    romi = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # (revenue - cost) / cost
    roas = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # revenue / cost
    cpa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # cost / orders
    conversion_rate = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['channel', 'date']
        ordering = ['-date', '-revenue']
        indexes = [
            models.Index(fields=['channel', '-date']),
        ]
    
    def save(self, *args, **kwargs):
        # Автоматический расчёт метрик
        if self.cost and self.cost > 0:
            self.romi = (self.revenue - self.cost) / self.cost * 100
            self.roas = self.revenue / self.cost
        if self.orders and self.orders > 0:
            self.cpa = self.cost / self.orders
            self.conversion_rate = self.orders / self.sessions if self.sessions else 0
        super().save(*args, **kwargs)


# ============================================================================
# Утилиты
# ============================================================================

def hash_ip(ip_address: str, salt: str = None) -> str:
    """
    Хеширование IP для GDPR/152-ФЗ
    """
    if salt is None:
        salt = getattr(settings, 'ANALYTICS_IP_SALT', 'default-salt-change-me')
    
    salted = f"{ip_address}:{salt}".encode('utf-8')
    return hashlib.sha256(salted).hexdigest()


def detect_device_type(user_agent: str) -> str:
    """Определяет тип устройства из User-Agent"""
    ua = user_agent.lower()
    if any(x in ua for x in ['mobile', 'android', 'iphone', 'ipod']):
        return 'mobile'
    elif any(x in ua for x in ['tablet', 'ipad']):
        return 'tablet'
    return 'desktop'


def parse_user_agent(user_agent: str) -> dict:
    """Парсит User-Agent (упрощённо)"""
    result = {'browser': 'Unknown', 'os': 'Unknown'}
    ua = user_agent.lower()
    
    # Browser
    if 'firefox' in ua:
        result['browser'] = 'Firefox'
    elif 'chrome' in ua and 'edg' not in ua:
        result['browser'] = 'Chrome'
    elif 'safari' in ua and 'chrome' not in ua:
        result['browser'] = 'Safari'
    elif 'edg' in ua:
        result['browser'] = 'Edge'
    elif 'msie' in ua or 'trident' in ua:
        result['browser'] = 'IE'
    
    # OS
    if 'windows' in ua:
        result['os'] = 'Windows'
    elif 'mac os' in ua:
        result['os'] = 'macOS'
    elif 'linux' in ua:
        result['os'] = 'Linux'
    elif 'android' in ua:
        result['os'] = 'Android'
    elif 'ios' in ua or 'iphone' in ua or 'ipad' in ua:
        result['os'] = 'iOS'
    
    return result
