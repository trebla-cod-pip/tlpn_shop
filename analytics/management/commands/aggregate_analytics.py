"""
Management команда для ежедневной агрегации аналитических данных

Запуск по cron:
0 2 * * * cd /path/to/project && python manage.py aggregate_analytics

Или через Django-Q / APScheduler для Windows
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F, ExpressionWrapper, DecimalField
from django.contrib.auth import get_user_model
from datetime import timedelta, date
import json

from analytics.models import (
    AggregatedStat, TrackingSession, TrackingEvent,
    RFMSegment, CustomerCohort, ChannelPerformance,
    ProductMarginStat, FunnelStep
)
from store.models import Product
from orders.models import OrderItem, Order as StoreOrder, OrderStatus

User = get_user_model()


class Command(BaseCommand):
    help = 'Агрегация аналитических данных за вчерашний день'

    def add_arguments(self, parser):
        parser.add_argument(
            '--date',
            type=str,
            help='Дата для агрегации (YYYY-MM-DD). По умолчанию вчера.'
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Пересчитать все данные вместо инкрементального обновления'
        )

    def handle(self, *args, **options):
        if options['date']:
            target_date = date.fromisoformat(options['date'])
        else:
            target_date = timezone.now().date() - timedelta(days=1)

        self.stdout.write(f'Начало агрегации за {target_date}...')

        # 1. Агрегация основных метрик
        self.aggregate_daily_metrics(target_date)

        # 2. Агрегация по каналам
        self.aggregate_channel_performance(target_date)

        # 3. Расчёт воронки конверсии
        self.aggregate_funnel_metrics(target_date)

        # 4. Продуктовая аналитика
        self.aggregate_product_metrics(target_date)

        # 5. Когортный анализ (ежемесячно)
        if target_date.day == 1:
            self.calculate_cohorts(target_date)

        # 6. RFM-сегментация (еженедельно)
        if target_date.weekday() == 0:  # Понедельник
            self.calculate_rfm_segments()

        self.stdout.write(
            self.style.SUCCESS(f'Агрегация за {target_date} завершена!')
        )

    def aggregate_daily_metrics(self, target_date):
        """Агрегация основных метрик за день"""
        self.stdout.write('  - Основные метрики...')

        date_next = target_date + timedelta(days=1)

        # Сессии
        sessions_count = TrackingSession.objects.filter(
            started_at__date=target_date
        ).count()

        # Уникальные посетители
        visitors_count = TrackingSession.objects.filter(
            started_at__date=target_date
        ).values('ip_hash').distinct().count()

        # Заказы и выручка
        orders = StoreOrder.objects.filter(
            created_at__date=target_date,
            status=OrderStatus.DELIVERED
        )
        orders_count = orders.count()
        revenue = orders.aggregate(total=Sum('total_amount'))['total'] or 0

        # Сохраняем метрики
        metrics = [
            ('sessions', sessions_count, sessions_count),
            ('visitors', visitors_count, visitors_count),
            ('orders', orders_count, orders_count),
            ('revenue', revenue, orders_count),
        ]

        for stat_type, value, count in metrics:
            AggregatedStat.objects.update_or_create(
                date=target_date,
                granularity='daily',
                stat_type=stat_type,
                dimensions={},
                defaults={
                    'value': value,
                    'count': count,
                }
            )

        # Conversion Rate
        if sessions_count > 0:
            cr = orders_count / sessions_count * 100
            AggregatedStat.objects.update_or_create(
                date=target_date,
                granularity='daily',
                stat_type='conversion_rate',
                dimensions={},
                defaults={'value': cr, 'count': sessions_count}
            )

        # AOV (Average Order Value)
        if orders_count > 0:
            aov = revenue / orders_count
            AggregatedStat.objects.update_or_create(
                date=target_date,
                granularity='daily',
                stat_type='aov',
                dimensions={},
                defaults={'value': aov, 'count': orders_count}
            )

        # Revenue per Visitor
        if visitors_count > 0:
            rpv = revenue / visitors_count
            AggregatedStat.objects.update_or_create(
                date=target_date,
                granularity='daily',
                stat_type='revenue_per_visitor',
                dimensions={},
                defaults={'value': rpv, 'count': visitors_count}
            )

        # Cart Abandonment Rate
        carts = FunnelStep.objects.filter(
            reached_at__date=target_date,
            step=4  # Корзина
        ).values('session').distinct().count()

        checkouts = FunnelStep.objects.filter(
            reached_at__date=target_date,
            step=8  # Заказ создан
        ).values('session').distinct().count()

        if carts > 0:
            abandonment = (carts - checkouts) / carts * 100
            AggregatedStat.objects.update_or_create(
                date=target_date,
                granularity='daily',
                stat_type='cart_abandonment',
                dimensions={},
                defaults={'value': abandonment, 'count': carts}
            )

    def aggregate_channel_performance(self, target_date):
        """Агрегация по каналам трафика"""
        self.stdout.write('  - Каналы трафика...')

        date_next = target_date + timedelta(days=1)

        # Группируем сессии по каналам
        sessions = TrackingSession.objects.filter(
            started_at__date=target_date
        )

        channels_data = {}
        for session in sessions:
            channel = session.traffic_source
            if channel not in channels_data:
                channels_data[channel] = {
                    'sessions': 0,
                    'visitors': set(),
                    'orders': 0,
                    'revenue': 0,
                }
            channels_data[channel]['sessions'] += 1
            channels_data[channel]['visitors'].add(session.ip_hash)

        # Добавляем данные о заказах
        orders = StoreOrder.objects.filter(
            created_at__date=target_date,
            status=OrderStatus.DELIVERED
        )

        for order in orders:
            if order.user:
                session = sessions.filter(user=order.user).first()
            else:
                session = None

            if session:
                channel = session.traffic_source
                channels_data[channel]['orders'] += 1
                channels_data[channel]['revenue'] += float(order.total_amount)

        # Сохраняем
        for channel, data in channels_data.items():
            ChannelPerformance.objects.update_or_create(
                channel=channel,
                date=target_date,
                defaults={
                    'sessions': data['sessions'],
                    'visitors': len(data['visitors']),
                    'orders': data['orders'],
                    'revenue': data['revenue'],
                }
            )

    def aggregate_funnel_metrics(self, target_date):
        """Агрегация воронки конверсии"""
        self.stdout.write('  - Воронка конверсии...')

        for step_num in range(1, 10):
            count = FunnelStep.objects.filter(
                reached_at__date=target_date,
                step=step_num
            ).values('session').distinct().count()

            AggregatedStat.objects.update_or_create(
                date=target_date,
                granularity='daily',
                stat_type='funnel_step',
                dimensions={'step': step_num},
                defaults={'value': count, 'count': count}
            )

    def aggregate_product_metrics(self, target_date):
        """Продуктовая аналитика"""
        self.stdout.write('  - Продуктовая аналитика...')

        # Топ товаров по выручке
        products = OrderItem.objects.filter(
            order__created_at__date=target_date,
            order__status=OrderStatus.DELIVERED
        ).values('product_id').annotate(
            quantity=Sum('quantity'),
            revenue=Sum('total'),
        ).order_by('-revenue')

        for item in products:
            # Предполагаем margin 50% если нет себестоимости
            revenue = item['revenue'] or 0
            cogs = revenue * 0.5
            margin = revenue - cogs

            ProductMarginStat.objects.update_or_create(
                product_id=item['product_id'],
                date=target_date,
                defaults={
                    'quantity_sold': item['quantity'] or 0,
                    'revenue': revenue,
                    'cogs': cogs,
                    'margin': margin,
                    'margin_percent': (margin / revenue * 100) if revenue > 0 else 0,
                }
            )

    def calculate_cohorts(self, target_date):
        """Расчёт когорт и retention"""
        self.stdout.write('  - Когортный анализ...')

        # Когорты по месяцу первой покупки
        cohorts = User.objects.annotate(
            first_order_date=Min('orders__created_at')
        ).filter(
            first_order_date__isnull=False
        ).values(
            cohort_month=TruncMonth('first_order_date')
        ).annotate(
            customer_count=Count('id', distinct=True)
        )

        for cohort_data in cohorts:
            cohort_month = cohort_data['cohort_month']
            customer_count = cohort_data['customer_count']

            # Расчёт retention по месяцам
            retention_rates = {}
            cohort_customers = User.objects.filter(
                orders__created_at__month=cohort_month.month,
                orders__created_at__year=cohort_month.year
            ).distinct()

            for month_offset in range(1, 13):
                check_date = cohort_month + timedelta(days=32 * month_offset)
                retained = User.objects.filter(
                    id__in=cohort_customers,
                    orders__created_at__month=check_date.month,
                    orders__created_at__year=check_date.year
                ).distinct().count()

                if customer_count > 0:
                    retention_rates[month_offset] = round(retained / customer_count, 4)

            # Общая выручка когорты
            total_revenue = StoreOrder.objects.filter(
                user__in=cohort_customers,
                status=OrderStatus.DELIVERED
            ).aggregate(total=Sum('total_amount'))['total'] or 0

            CustomerCohort.objects.update_or_create(
                cohort_month=cohort_month,
                defaults={
                    'customer_count': customer_count,
                    'total_revenue': total_revenue,
                    'retention_rates': retention_rates,
                }
            )

    def calculate_rfm_segments(self):
        """RFM-сегментация клиентов"""
        self.stdout.write('  - RFM-сегментация...')

        now = timezone.now()

        # Получаем всех клиентов с заказами
        customers = User.objects.filter(orders__isnull=False).distinct()

        for customer in customers:
            orders = StoreOrder.objects.filter(
                user=customer,
                status=OrderStatus.DELIVERED
            )

            if not orders.exists():
                continue

            # Recency - дней с последней покупки
            last_order = orders.order_by('-created_at').first()
            recency = (now - last_order.created_at).days

            # Frequency - количество заказов
            frequency = orders.count()

            # Monetary - общая сумма
            monetary = orders.aggregate(total=Sum('total_amount'))['total'] or 0

            # Расчёт scores (1-5)
            # Для простоты используем квантили
            r_score = min(5, max(1, 6 - recency // 30))  # 1 балл за каждый месяц без покупки
            f_score = min(5, max(1, frequency // 2 + 1))  # 1 балл за каждые 2 заказа
            m_score = min(5, max(1, int(monetary) // 5000 + 1))  # 1 балл за каждые 5000₽

            rfm_score = r_score + f_score + m_score

            # Определение сегмента
            segment = self._get_rfm_segment(r_score, f_score, m_score, rfm_score)

            RFMSegment.objects.create(
                user=customer,
                recency=recency,
                frequency=frequency,
                monetary=monetary,
                r_score=r_score,
                f_score=f_score,
                m_score=m_score,
                rfm_score=rfm_score,
                segment=segment,
            )

    def _get_rfm_segment(self, r, f, m, total):
        """Определяет сегмент по RFM scores"""
        if r >= 4 and f >= 4 and m >= 4:
            return 'champions'
        elif r >= 3 and f >= 3 and m >= 3:
            return 'loyal'
        elif r >= 4 and f <= 2:
            return 'new'
        elif r >= 3 and f >= 2 and m >= 3:
            return 'potential'
        elif r >= 3 and f <= 2 and m <= 2:
            return 'promising'
        elif r >= 2 and f >= 3:
            return 'need_attention'
        elif r >= 2 and f <= 2 and m <= 2:
            return 'about_to_sleep'
        elif r <= 2 and f >= 3:
            return 'at_risk'
        elif r <= 2 and f >= 4 and m >= 4:
            return 'cant_lose'
        elif r <= 2 and f <= 2:
            return 'hibernating'
        else:
            return 'lost'
