from rest_framework import serializers
from orders.models import Order, OrderItem
from store.models import Product
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Минимальная сумма заказа (берётся из настроек)
# FREE_DELIVERY_AMOUNT также из настроек


class OrderItemSerializer(serializers.Serializer):
    """Товар в заказе (для создания)"""
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, default=1)


class OrderCreateSerializer(serializers.Serializer):
    """Сериалайзер для создания заказа"""
    # Товары
    items = OrderItemSerializer(many=True)

    # Контактные данные
    phone = serializers.CharField(max_length=25)
    email = serializers.EmailField(required=False, allow_blank=True)

    # Доставка
    delivery_address = serializers.CharField()
    delivery_date = serializers.DateField()
    delivery_time = serializers.CharField(required=False, allow_blank=True)
    comment = serializers.CharField(required=False, allow_blank=True)

    # Данные Telegram (передаются из WebApp)
    telegram_user_id = serializers.IntegerField(required=False, allow_null=True)
    telegram_username = serializers.CharField(required=False, allow_blank=True)
    telegram_first_name = serializers.CharField(required=False, allow_blank=True)
    telegram_last_name = serializers.CharField(required=False, allow_blank=True)

    # Предпочтительный способ связи
    preferred_contact_method = serializers.CharField(required=False, default='telegram')

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Корзина пуста")

        # Проверяем минимальную сумму заказа
        total_amount = sum(
            Product.objects.get(id=item['product_id']).price * item.get('quantity', 1)
            for item in items
        )
        
        min_amount = getattr(settings, 'MIN_ORDER_AMOUNT', 1000)
        free_delivery_amount = getattr(settings, 'FREE_DELIVERY_AMOUNT', 3500)
        
        if total_amount < min_amount:
            raise serializers.ValidationError(
                f"Минимальная сумма заказа — {min_amount} ₽. "
                f"Сейчас в корзине {total_amount} ₽. "
                f"Доставка до двери — от {free_delivery_amount} ₽."
            )

        validated_items = []
        for item in items:
            try:
                product = Product.objects.get(id=item['product_id'], is_active=True)
            except Product.DoesNotExist:
                raise serializers.ValidationError(f"Товар с ID {item['product_id']} не найден")

            if product.stock < item['quantity']:
                raise serializers.ValidationError(f"Недостаточно товара: {product.name}")

            validated_items.append({
                'product': product,
                'quantity': item['quantity'],
                'price': product.price
            })

        return validated_items

    def create(self, validated_data):
        items_data = validated_data.pop('items')

        # Создаём заказ
        order = Order.objects.create(
            **validated_data,
            total_amount=0  # Будет обновлено ниже
        )

        # Создаём товары заказа и списываем со склада
        total = 0
        for item in items_data:
            order_item = OrderItem.objects.create(
                order=order,
                product=item['product'],
                quantity=item['quantity'],
                price=item['price'],
                total=item['price'] * item['quantity']
            )
            total += order_item.total
            
            # Списываем товар со склада
            product = item['product']
            product.stock = max(0, product.stock - item['quantity'])
            product.save()
            logger.info(f"Списано {item['quantity']} шт. товара '{product.name}'. Остаток: {product.stock} шт.")

        # Обновляем общую сумму
        order.total_amount = total
        order.save()

        return order


class OrderSerializer(serializers.ModelSerializer):
    """Сериалайзер для отображения заказа"""
    items = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'status', 'status_display', 'total_amount',
            'delivery_address', 'delivery_date', 'delivery_time',
            'phone', 'telegram_user_id', 'telegram_username',
            'preferred_contact_method', 'items', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_items(self, obj):
        items_data = []
        for item in obj.items.all().select_related('product'):
            items_data.append({
                'product_id': item.product.id,
                'product_name': item.product.name,
                'product_slug': item.product.slug,
                'product_image': item.product.image.url if item.product.image else None,
                'quantity': item.quantity,
                'price': str(item.price),
                'total': str(item.total)
            })
        return items_data
