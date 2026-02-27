from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from orders.models import Order
from orders.serializers import OrderCreateSerializer, OrderSerializer
from telegram_app.utils import send_order_notification_sync


class OrderViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet
):
    """
    ViewSet для заказов
    
    POST /api/orders/ - создать заказ
    GET /api/orders/ - список заказов пользователя (по telegram_user_id)
    GET /api/orders/{id}/ - детали заказа
    """
    queryset = Order.objects.select_related().prefetch_related('items__product')
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    def get_queryset(self):
        """Фильтруем заказы по пользователю"""
        queryset = super().get_queryset()
        telegram_id = self.request.query_params.get('telegram_user_id')
        if telegram_id:
            queryset = queryset.filter(telegram_user_id=telegram_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Создаём заказ
        order = serializer.save()
        
        # Отправляем уведомление в Telegram
        try:
            send_order_notification_sync(order)
        except Exception as e:
            # Логгируем ошибку, но не прерываем создание заказа
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки уведомления: {e}")
        
        # Возвращаем данные заказа
        response_serializer = OrderSerializer(order)
        headers = self.get_success_headers(response_serializer.data)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
