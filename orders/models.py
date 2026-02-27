from django.db import models
from store.models import Product


class OrderStatus(models.TextChoices):
    """Статусы заказа"""
    PENDING = 'pending', 'Ожидает подтверждения'
    CONFIRMED = 'confirmed', 'Подтверждён'
    ASSEMBLING = 'assembling', 'Собирается'
    DELIVERING = 'delivering', 'Доставляется'
    DELIVERED = 'delivered', 'Доставлен'
    CANCELLED = 'cancelled', 'Отменён'


class Order(models.Model):
    """Заказ покупателя"""
    # Данные из Telegram
    telegram_user_id = models.BigIntegerField(verbose_name='Telegram User ID')
    telegram_username = models.CharField(max_length=100, blank=True, verbose_name='Telegram username')
    telegram_first_name = models.CharField(max_length=100, blank=True, verbose_name='Имя Telegram')
    telegram_last_name = models.CharField(max_length=100, blank=True, verbose_name='Фамилия Telegram')
    
    # Контактные данные
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    preferred_contact_method = models.CharField(max_length=20, default='telegram', verbose_name='Предпочтительный способ связи')

    # Доставка
    delivery_address = models.TextField(verbose_name='Адрес доставки')
    delivery_date = models.DateField(verbose_name='Дата доставки')
    delivery_time = models.CharField(max_length=50, blank=True, verbose_name='Время доставки')
    comment = models.TextField(blank=True, verbose_name='Комментарий к заказу')
    
    # Статус и оплата
    status = models.CharField(max_length=20, choices=OrderStatus.choices, default=OrderStatus.PENDING, verbose_name='Статус')
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Общая сумма')
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.id} - {self.telegram_first_name}'

    def get_items_count(self):
        """Количество товаров в заказе"""
        return self.items.aggregate(total=models.Sum('quantity'))['total'] or 0


class OrderItem(models.Model):
    """Товар в заказе"""
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, verbose_name='Товар')
    quantity = models.PositiveIntegerField(default=1, verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена на момент заказа')
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма')

    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказах'

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    def save(self, *args, **kwargs):
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)
