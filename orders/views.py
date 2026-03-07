from rest_framework import viewsets, status, mixins
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from orders.models import Order
from orders.serializers import OrderCreateSerializer, OrderSerializer
from telegram_app.utils import send_order_notification_sync
import logging

logger = logging.getLogger(__name__)


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
    # Отключаем CSRF для API, так как запросы могут идти из Telegram Mini App
    authentication_classes = []

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
        logger.info(f"Получен запрос на создание заказа. Данные: {request.data}")

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Создаём заказ
        order = serializer.save()
        logger.info(f"Заказ #{order.id} успешно создан")

        # Отправляем уведомление в Telegram
        try:
            logger.info(f"Отправка уведомления для заказа #{order.id}")
            send_order_notification_sync(order)
            logger.info(f"Уведомление для заказа #{order.id} отправлено")
        except Exception as e:
            # Логгируем ошибку, но не прерываем создание заказа
            logger.error(f"Ошибка отправки уведомления для заказа #{order.id}: {e}", exc_info=True)

        # Возвращаем данные заказа
        request.session['last_order_id'] = order.id
        response_serializer = OrderSerializer(order)
        headers = self.get_success_headers(response_serializer.data)
        logger.info(f"Заказ #{order.id} возвращен клиенту с статусом {status.HTTP_201_CREATED}")
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )
