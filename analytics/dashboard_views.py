"""
Dashboard Views для аналитики
"""
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.db.models import Count, Sum, Avg, F, FloatField
from django.db.models.functions import TruncDate, TruncMonth
from datetime import timedelta, date
import json

from analytics.models import (
    TrackingSession, TrackingEvent, AggregatedStat,
    RFMSegment, CustomerCohort, ChannelPerformance,
    ProductMarginStat, FunnelStep
)
from orders.models import Order as StoreOrder, OrderStatus


@staff_member_required
def analytics_dashboard(request):
    """
    Главная страница дашборда аналитики
    """
    # Период по умолчанию
    days = int(request.GET.get('days', 30))
    date_from = timezone.now().date() - timedelta(days=days)
    date_to = timezone.now().date()

    # Основные метрики
    sessions_count = TrackingSession.objects.filter(started_at__date__gte=date_from).count()
    visitors_count = TrackingSession.objects.filter(
        started_at__date__gte=date_from
    ).values('ip_hash').distinct().count()

    orders = StoreOrder.objects.filter(
        created_at__date__gte=date_from,
        status=OrderStatus.DELIVERED
    )
    orders_count = orders.count()
    revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0

    # Расчёт метрик
    aov = revenue / orders_count if orders_count > 0 else 0
    conversion_rate = (orders_count / sessions_count * 100) if sessions_count > 0 else 0

    # Предыдущий период для сравнения
    prev_date_from = date_from - timedelta(days=days)
    prev_sessions = TrackingSession.objects.filter(
        started_at__date__gte=prev_date_from,
        started_at__lt=date_from
    ).count()
    prev_revenue = StoreOrder.objects.filter(
        created_at__date__gte=prev_date_from,
        created_at__lt=date_from,
        status=OrderStatus.DELIVERED
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Динамика
    sessions_growth = ((sessions_count - prev_sessions) / prev_sessions * 100) if prev_sessions > 0 else 0
    revenue_growth = ((revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    context = {
        'title': 'Дашборд аналитики',
        'days': days,
        'date_from': date_from,
        'date_to': date_to,
        'metrics': {
            'sessions': sessions_count,
            'sessions_growth': round(sessions_growth, 1),
            'visitors': visitors_count,
            'orders': orders_count,
            'revenue': float(revenue),
            'revenue_growth': round(revenue_growth, 1),
            'aov': float(aov),
            'conversion_rate': round(conversion_rate, 2),
        }
    }

    return render(request, 'analytics/dashboard.html', context)


@staff_member_required
def analytics_traffic_chart(request):
    """
    Данные для графика трафика по дням
    """
    days = int(request.GET.get('days', 30))
    date_from = timezone.now().date() - timedelta(days=days)

    data = TrackingSession.objects.filter(
        started_at__date__gte=date_from
    ).annotate(
        date=TruncDate('started_at')
    ).values('date').annotate(
        sessions=Count('id'),
        visitors=Count('ip_hash', distinct=True)
    ).order_by('date')

    chart_data = {
        'labels': [item['date'].strftime('%d.%m') for item in data],
        'datasets': [
            {
                'name': 'Сессии',
                'data': [item['sessions'] for item in data]
            },
            {
                'name': 'Посетители',
                'data': [item['visitors'] for item in data]
            }
        ]
    }

    return render(request, 'analytics/chart_data.html', {'chart_data': chart_data})


@staff_member_required
def analytics_revenue_chart(request):
    """
    Данные для графика выручки по дням
    """
    days = int(request.GET.get('days', 30))
    date_from = timezone.now().date() - timedelta(days=days)

    data = StoreOrder.objects.filter(
        created_at__date__gte=date_from,
        status=OrderStatus.DELIVERED
    ).annotate(
        date=TruncDate('created_at')
    ).values('date').annotate(
        revenue=Sum('total_amount'),
        orders=Count('id')
    ).order_by('date')

    chart_data = {
        'labels': [item['date'].strftime('%d.%m') for item in data],
        'datasets': [
            {
                'name': 'Выручка (₽)',
                'data': [float(item['revenue'] or 0) for item in data]
            },
            {
                'name': 'Заказы',
                'data': [item['orders'] for item in data]
            }
        ]
    }

    return render(request, 'analytics/chart_data.html', {'chart_data': chart_data})


@staff_member_required
def analytics_channels_chart(request):
    """
    Данные для графика по каналам трафика
    """
    days = int(request.GET.get('days', 30))
    date_from = timezone.now().date() - timedelta(days=days)

    sessions = TrackingSession.objects.filter(started_at__date__gte=date_from)

    channels = {}
    for session in sessions:
        source = session.traffic_source
        if source not in channels:
            channels[source] = {'sessions': 0, 'revenue': 0}
        channels[source]['sessions'] += 1

    # Добавляем выручку
    orders = StoreOrder.objects.filter(
        created_at__date__gte=date_from,
        status=OrderStatus.DELIVERED
    )
    for order in orders:
        if order.user:
            session = sessions.filter(user=order.user).first()
            if session:
                source = session.traffic_source
                channels[source]['revenue'] += float(order.total_amount)

    chart_data = {
        'labels': list(channels.keys()),
        'datasets': [
            {
                'name': 'Сессии',
                'data': [data['sessions'] for data in channels.values()]
            },
            {
                'name': 'Выручка (₽)',
                'data': [data['revenue'] for data in channels.values()]
            }
        ]
    }

    return render(request, 'analytics/chart_data.html', {'chart_data': chart_data})


@staff_member_required
def analytics_funnel_chart(request):
    """
    Данные для воронки конверсии
    """
    days = int(request.GET.get('days', 30))
    date_from = timezone.now().date() - timedelta(days=days)

    steps_data = []
    for step_num, step_name in FunnelStep.STEPS:
        count = FunnelStep.objects.filter(
            reached_at__date__gte=date_from,
            step=step_num
        ).values('session').distinct().count()
        steps_data.append({
            'step': step_name,
            'count': count
        })

    # Расчёт конверсии между шагами
    funnel_data = {
        'labels': [item['step'] for item in steps_data],
        'data': [item['count'] for item in steps_data]
    }

    return render(request, 'analytics/chart_data.html', {'chart_data': funnel_data})


@staff_member_required
def analytics_rfm_chart(request):
    """
    Данные для графика RFM-сегментов
    """
    segments = RFMSegment.objects.values('segment').annotate(
        count=Count('id')
    ).order_by('-count')

    segment_labels = {
        'champions': 'Чемпионы',
        'loyal': 'Лояльные',
        'potential': 'Потенциальные',
        'new': 'Новые',
        'promising': 'Перспективные',
        'need_attention': 'Требуют внимания',
        'about_to_sleep': 'Засыпающие',
        'at_risk': 'Под угрозой',
        'cant_lose': 'Не потерять',
        'hibernating': 'Спящие',
        'lost': 'Потерянные',
    }

    chart_data = {
        'labels': [segment_labels.get(s['segment'], s['segment']) for s in segments],
        'datasets': [{
            'name': 'Клиенты',
            'data': [s['count'] for s in segments]
        }]
    }

    return render(request, 'analytics/chart_data.html', {'chart_data': chart_data})


@staff_member_required
def analytics_products_chart(request):
    """
    Данные для графика топ товаров по марже
    """
    days = int(request.GET.get('days', 30))
    date_from = timezone.now().date() - timedelta(days=days)

    products = ProductMarginStat.objects.filter(
        date__gte=date_from
    ).values(
        'product__name'
    ).annotate(
        total_margin=Sum('margin'),
        total_revenue=Sum('revenue')
    ).order_by('-total_margin')[:10]

    chart_data = {
        'labels': [p['product__name'][:30] for p in products],
        'datasets': [
            {
                'name': 'Маржа (₽)',
                'data': [float(p['total_margin'] or 0) for p in products]
            },
            {
                'name': 'Выручка (₽)',
                'data': [float(p['total_revenue'] or 0) for p in products]
            }
        ]
    }

    return render(request, 'analytics/chart_data.html', {'chart_data': chart_data})
