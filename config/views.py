from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
from orders.models import Order, OrderItem
from store.models import Product


def robots(request):
    """
    Динамическая генерация robots.txt
    Позволяет управлять содержимым через настройки Django
    """
    # Получаем домен из настроек или используем значение по умолчанию
    domain = getattr(settings, 'SITEMAP_DOMAIN', 'tlpn.shop')
    protocol = getattr(settings, 'SITEMAP_PROTOCOL', 'https')

    lines = [
        '# robots.txt для Tulipa Shop (tlpn.shop)',
        '# Интернет-магазин тюльпанов',
        f'# Sitemap: {protocol}://{domain}/sitemap.xml',
        '',
        '# =============================================================================',
        '# Для всех поисковых роботов',
        '# =============================================================================',
        'User-agent: *',
        '',
        '# Разрешить индексацию публичных страниц',
        'Allow: /',
        'Allow: /item/',
        'Allow: /?category=',
        '',
        '# Запретить индексацию служебных разделов',
        'Disallow: /admin/',
        'Disallow: /bag/',
        'Disallow: /cart/',
        'Disallow: /checkout/',
        'Disallow: /profile/',
        'Disallow: /order-success/',
        'Disallow: /cart-sync/',
        'Disallow: /favorites/',
        'Disallow: /api/',
        'Disallow: /telegram/',
        'Disallow: /analytics/',
        '',
        '# Запретить URL с параметрами (фильтры, сортировка, utm-метки)',
        'Disallow: /*?*',
        'Disallow: /*&*',
        'Disallow: /*utm_*',
        'Disallow: /*filter=',
        'Disallow: /*sort=',
        'Disallow: /*page=',
        '',
        '# Разрешить CSS и JS для корректного рендеринга',
        'Allow: /static/css/',
        'Allow: /static/js/',
        'Allow: /static/fonts/',
        '',
        '# Разрешить изображения товаров для Google Images и Яндекс.Картинок',
        'Allow: /media/products/',
        '',
        '# =============================================================================',
        '# Для Яндекс (дополнительные настройки)',
        '# =============================================================================',
        'User-agent: Yandex',
        '',
        '# Разрешить индексацию публичных страниц',
        'Allow: /',
        'Allow: /item/',
        'Allow: /?category=',
        '',
        '# Запретить индексацию служебных разделов',
        'Disallow: /admin/',
        'Disallow: /bag/',
        'Disallow: /cart/',
        'Disallow: /checkout/',
        'Disallow: /profile/',
        'Disallow: /order-success/',
        'Disallow: /cart-sync/',
        'Disallow: /favorites/',
        'Disallow: /api/',
        'Disallow: /telegram/',
        'Disallow: /analytics/',
        '',
        '# Запретить URL с параметрами',
        'Disallow: /*?*',
        'Disallow: /*&*',
        'Disallow: /*utm_*',
        'Disallow: /*filter=',
        'Disallow: /*sort=',
        'Disallow: /*page=',
        '',
        '# Разрешить ресурсы для рендеринга',
        'Allow: /static/css/',
        'Allow: /static/js/',
        'Allow: /static/fonts/',
        'Allow: /media/products/',
        '',
        '# Главный хост для Яндекса',
        f'Host: {protocol}://{domain}/',
        '',
        '# =============================================================================',
        '# Sitemap',
        '# =============================================================================',
        f'Sitemap: {protocol}://{domain}/sitemap.xml',
        '',
    ]

    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')


@staff_member_required(login_url='/admin/login/')
def order_stats(request):
    """
    Статистика заказов: сколько всего заказано по каждому товару
    Доступно только суперпользователям (staff)
    """
    from orders.models import OrderStatus
    
    # Исключаем отмененные заказы из статистики
    active_statuses = [
        OrderStatus.PENDING,
        OrderStatus.CONFIRMED,
        OrderStatus.ASSEMBLING,
        OrderStatus.DELIVERING,
        OrderStatus.DELIVERED,
    ]
    
    # Группируем по товарам и суммируем количество (только для активных заказов)
    stats = OrderItem.objects.filter(
        order__status__in=active_statuses
    ).values(
        'product_id',
        'product__name',
        'product__slug',
        'product__image',
        'product__cart_image'
    ).annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total')
    ).order_by('-total_quantity')

    # Общая статистика (только активные заказы)
    total_orders = Order.objects.filter(status__in=active_statuses).count()
    total_items = sum(item['total_quantity'] or 0 for item in stats)
    
    # Считаем общую выручку с учетом доставки (только активные заказы)
    total_revenue = Order.objects.filter(
        status__in=active_statuses
    ).aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    context = {
        'stats': stats,
        'total_orders': total_orders,
        'total_items': total_items,
        'total_revenue': total_revenue,
        'FREE_DELIVERY_QUANTITY': 35,
    }

    return render(request, 'config/order_stats.html', context)


def delivery_info(request):
    """
    Страница с информацией о доставке
    """
    from django.conf import settings
    context = {
        'PICKUP_ADDRESS': 'ул. Каштановая 9',
        'FREE_DELIVERY_QUANTITY': 35,
        'MIN_ORDER_AMOUNT': getattr(settings, 'MIN_ORDER_AMOUNT', 1000),
        'FREE_DELIVERY_AMOUNT': getattr(settings, 'FREE_DELIVERY_AMOUNT', 5000),
    }
    return render(request, 'config/delivery.html', context)
