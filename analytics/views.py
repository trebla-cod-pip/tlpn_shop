"""
API для приёма и отдачи аналитических данных
"""
from rest_framework import serializers, viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F, ExpressionWrapper, DecimalField
from django.db.models.functions import TruncDate, TruncMonth, Cast
from datetime import datetime, timedelta
import json

from analytics.models import (
    TrackingSession, TrackingEvent, AggregatedStat,
    RFMSegment, CustomerCohort, ProductMarginStat,
    ChannelPerformance, FunnelStep, hash_ip
)
from store.models import Product
from orders.models import OrderItem


# ============================================================================
# Сериалайзеры
# ============================================================================

class TrackingEventSerializer(serializers.Serializer):
    session_id = serializers.CharField()
    event_type = serializers.CharField()
    event_name = serializers.CharField()
    url = serializers.URLField()
    page_title = serializers.CharField(required=False, allow_blank=True)
    meta = serializers.JSONField(required=False, default=dict)
    timestamp = serializers.DateTimeField()


class TrackingEventBatchSerializer(serializers.Serializer):
    events = serializers.ListField(child=TrackingEventSerializer())


# ============================================================================
# API для приёма событий (Frontend -> Backend)
# ============================================================================

class TrackingAPIView(APIView):
    """
    Принимает события от JavaScript-трекера
    POST /api/analytics/track/
    
    Body:
    {
        "events": [
            {
                "session_id": "sess_abc123",
                "event_type": "page_view",
                "event_name": "page_view",
                "url": "https://...",
                "meta": {...},
                "timestamp": "2024-01-01T12:00:00Z"
            }
        ]
    }
    """
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = TrackingEventBatchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        events_data = serializer.validated_data['events']
        created_count = 0
        
        for event_data in events_data:
            # Находим сессию
            session = TrackingSession.objects.filter(
                session_key=event_data['session_id']
            ).first()
            
            if not session:
                # Создаём сессию если не найдена
                session = TrackingSession.objects.create(
                    session_key=event_data['session_id'],
                    ip_hash=hash_ip(request.META.get('REMOTE_ADDR', '')),
                )
            
            # Создаём событие
            TrackingEvent.objects.create(
                session=session,
                user=request.user if request.user.is_authenticated else None,
                event_type=event_data['event_type'],
                event_name=event_data['event_name'],
                url=event_data['url'],
                page_title=event_data.get('page_title', ''),
                meta=event_data.get('meta', {}),
            )
            created_count += 1
        
        return Response({
            'status': 'ok',
            'events_processed': created_count
        }, status=status.HTTP_202_ACCEPTED)


# ============================================================================
# API для дашборда аналитики
# ============================================================================

class DashboardMetricsAPIView(APIView):
    """
    Основные метрики для дашборда
    GET /api/analytics/dashboard/?days=30
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        date_from = timezone.now().date() - timedelta(days=days)
        
        # Сессии и посетители
        sessions = TrackingSession.objects.filter(
            started_at__date__gte=date_from
        )
        visitors = sessions.values('ip_hash').distinct().count()

        # Заказы и выручка
        orders = StoreOrder.objects.filter(
            created_at__date__gte=date_from,
            status=OrderStatus.DELIVERED
        )
        revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0
        order_count = orders.count()
        
        # Метрики
        aov = revenue / order_count if order_count > 0 else 0
        revenue_per_visitor = revenue / visitors if visitors > 0 else 0
        
        # Конверсия
        conversion_rate = (order_count / sessions.count() * 100) if sessions.count() > 0 else 0
        
        return Response({
            'period': {'days': days, 'from': str(date_from)},
            'sessions': sessions.count(),
            'visitors': visitors,
            'orders': order_count,
            'revenue': float(revenue),
            'aov': float(aov),
            'revenue_per_visitor': float(revenue_per_visitor),
            'conversion_rate': float(conversion_rate),
        })


class RevenuePerChannelAPIView(APIView):
    """
    Revenue per Visitor по каналам за период
    GET /api/analytics/revenue-per-channel/?days=30
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        date_from = timezone.now().date() - timedelta(days=days)
        
        # Группировка по каналам
        channels = []
        
        # Получаем сессии с источниками
        sessions = TrackingSession.objects.filter(
            started_at__date__gte=date_from
        ).select_related('user')
        
        # Группируем по traffic_source
        from collections import defaultdict
        stats = defaultdict(lambda: {'sessions': 0, 'visitors': set(), 'revenue': 0, 'orders': 0})
        
        for session in sessions:
            source = session.traffic_source
            stats[source]['sessions'] += 1
            stats[source]['visitors'].add(session.ip_hash)

        # Добавляем данные о заказах
        orders = StoreOrder.objects.filter(
            created_at__date__gte=date_from,
            status=OrderStatus.DELIVERED
        ).select_related('user')
        
        for order in orders:
            # Находим последнюю сессию пользователя
            if order.user:
                session = sessions.filter(user=order.user).first()
            else:
                session = None
            
            if session:
                source = session.traffic_source
                stats[source]['revenue'] += float(order.total_amount)
                stats[source]['orders'] += 1
        
        # Формируем ответ
        for source, data in stats.items():
            visitor_count = len(data['visitors'])
            channels.append({
                'channel': source,
                'sessions': data['sessions'],
                'visitors': visitor_count,
                'orders': data['orders'],
                'revenue': data['revenue'],
                'revenue_per_visitor': data['revenue'] / visitor_count if visitor_count > 0 else 0,
                'conversion_rate': data['orders'] / data['sessions'] * 100 if data['sessions'] > 0 else 0,
            })
        
        # Сортируем по revenue
        channels.sort(key=lambda x: x['revenue'], reverse=True)
        
        return Response({'channels': channels})


class FunnelAPIView(APIView):
    """
    Воронка конверсии по шагам
    GET /api/analytics/funnel/?days=30
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        date_from = timezone.now().date() - timedelta(days=days)
        
        # Считаем пользователей на каждом шаге
        steps = []
        total_sessions = TrackingSession.objects.filter(
            started_at__date__gte=date_from
        ).count()
        
        for step_num in range(1, 10):
            count = FunnelStep.objects.filter(
                reached_at__date__gte=date_from,
                step=step_num
            ).values('session').distinct().count()
            
            steps.append({
                'step': step_num,
                'count': count,
                'conversion_rate': count / total_sessions * 100 if total_sessions > 0 else 0,
            })
        
        # Cart Abandonment Rate
        carts_created = FunnelStep.objects.filter(
            reached_at__date__gte=date_from,
            step=4  # Корзина
        ).values('session').distinct().count()
        
        orders_placed = FunnelStep.objects.filter(
            reached_at__date__gte=date_from,
            step=8  # Заказ создан
        ).values('session').distinct().count()
        
        cart_abandonment = ((carts_created - orders_placed) / carts_created * 100) if carts_created > 0 else 0
        
        return Response({
            'steps': steps,
            'total_sessions': total_sessions,
            'cart_abandonment_rate': float(cart_abandonment),
        })


class TopProductsByMarginAPIView(APIView):
    """
    Топ-10 товаров по марже
    GET /api/analytics/top-products-margin/?days=30
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        date_from = timezone.now().date() - timedelta(days=days)
        
        # Запрос с аннотацией для расчёта маржи
        # Предполагается что в OrderItem есть поле cost (себестоимость)
        # Если нет - добавьте в модель OrderItem: cost = models.DecimalField(...)
        
        products = OrderItem.objects.filter(
            order__created_at__date__gte=date_from,
            order__status='delivered'
        ).values(
            'product_id',
            'product__name'
        ).annotate(
            quantity_sold=Sum('quantity'),
            revenue=Sum('total'),
            # Если есть cost: cogs=Sum(F('cost') * F('quantity'))
            # Иначе предполагаем что margin = 50% от revenue
            cogs=Sum('total') * 0.5,
        ).annotate(
            margin=F('revenue') - F('cogs'),
            margin_percent=F('margin') / F('revenue') * 100
        ).order_by('-margin')[:10]
        
        return Response({
            'products': list(products.values(
                'product_id',
                'product__name',
                'quantity_sold',
                'revenue',
                'cogs',
                'margin',
                'margin_percent'
            ))
        })


class RFMSegmentsAPIView(APIView):
    """
    RFM-сегментация клиентов
    GET /api/analytics/rfm-segments/
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Группировка по сегментам
        segments = RFMSegment.objects.values('segment').annotate(
            customer_count=Count('id'),
            avg_monetary=Avg('monetary'),
            avg_frequency=Avg('frequency'),
            avg_recency=Avg('recency'),
        ).order_by('-customer_count')
        
        # Словарь с названиями сегментов
        segment_labels = {
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
        
        return Response({
            'segments': [
                {
                    'segment': s['segment'],
                    'label': segment_labels.get(s['segment'], s['segment']),
                    'count': s['customer_count'],
                    'avg_monetary': float(s['avg_monetary'] or 0),
                    'avg_frequency': float(s['avg_frequency'] or 0),
                    'avg_recency': float(s['avg_recency'] or 0),
                }
                for s in segments
            ]
        })


class CohortRetentionAPIView(APIView):
    """
    Когортный анализ retention
    GET /api/analytics/cohort-retention/
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        cohorts = CustomerCohort.objects.all().order_by('-cohort_month')[:12]
        
        data = []
        for cohort in cohorts:
            data.append({
                'cohort_month': cohort.cohort_month.strftime('%Y-%m'),
                'customer_count': cohort.customer_count,
                'total_revenue': float(cohort.total_revenue),
                'retention_rates': cohort.retention_rates,
            })
        
        return Response({'cohorts': data})


class ChannelROMIAPIView(APIView):
    """
    ROMI/ROAS по каналам
    GET /api/analytics/channel-romi/?days=30
    """
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        days = int(request.GET.get('days', 30))
        date_from = timezone.now().date() - timedelta(days=days)
        
        channels = ChannelPerformance.objects.filter(
            date__gte=date_from
        ).values('channel').annotate(
            total_sessions=Sum('sessions'),
            total_revenue=Sum('revenue'),
            total_cost=Sum('cost'),
            total_orders=Sum('orders'),
        ).annotate(
            romi=(F('total_revenue') - F('total_cost')) / F('total_cost') * 100,
            roas=F('total_revenue') / F('total_cost'),
        ).order_by('-romi')
        
        return Response({'channels': list(channels)})
