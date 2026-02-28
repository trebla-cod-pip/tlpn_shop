from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from store.models import Category, Product
from store.serializers import CategorySerializer, ProductListSerializer, ProductDetailSerializer

from orders.models import Order
from orders.serializers import OrderSerializer


# ============ Web Views ============

def home(request):
    """Главная страница"""
    return render(request, 'store/home.html')


def item(request, slug):
    """Страница товара"""
    # Оптимизация: select_related для category чтобы избежать N+1
    from store.models import Product
    product = Product.objects.select_related('category').get(slug=slug)
    return render(request, 'store/item.html', {'product': product})


def bag(request):
    """Корзина"""
    # Корзина хранится в localStorage на клиенте
    # Session используется только для аналитики
    return render(request, 'store/bag.html')


def order_success(request):
    """Страница успеха заказа"""
    order_id = request.GET.get('order_id')
    order = None
    if order_id:
        order = get_object_or_404(Order, pk=order_id)
    elif 'last_order_id' in request.session:
        order = get_object_or_404(Order, pk=request.session.get('last_order_id'))

    order_data = OrderSerializer(order).data if order else {}
    if order_data:
        order_data['total_amount'] = float(order_data.get('total_amount') or 0)
    # Добавим категорию в каждый элемент
    for item in order_data.get('items', []):
        item.setdefault('category', 'Тюльпаны')
    return render(request, 'store/order_success.html', {'order': order_data})


@csrf_exempt
@require_POST
def sync_cart_session(request):
    """Сохраняем содержимое корзины в сессии для аналитики"""
    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        payload = []

    cart_items = []
    total = 0
    for raw_item in payload:
        price = float(raw_item.get('price') or 0)
        qty = int(raw_item.get('quantity') or 1)
        name = raw_item.get('name') or ''
        item = {
            'id': raw_item.get('id'),
            'name': name,
            'price': price,
            'quantity': qty,
            'category': raw_item.get('category', 'Тюльпаны'),
            'total': price * qty,
            'image': raw_item.get('image'),
        }
        total += item['total']
        cart_items.append(item)

    request.session['cart_items'] = cart_items
    request.session['cart_total'] = total
    request.session['cart_currency'] = 'RUB'
    return JsonResponse({'status': 'ok', 'items': len(cart_items), 'total': total})


def profile(request):
    """Профиль"""
    return render(request, 'store/profile.html')


# ============ API Views ============

class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для категорий - только чтение"""
    queryset = Category.objects.filter(is_active=True)
    pagination_class = None  # Отключаем пагинацию
    serializer_class = CategorySerializer
    lookup_field = 'slug'
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=False, methods=['get'])
    def with_products(self, request):
        """Категории с товарами"""
        categories = self.get_queryset()
        serializer = self.get_serializer(categories, many=True)
        return Response(serializer.data)


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для товаров - только чтение"""
    queryset = Product.objects.filter(is_active=True).select_related('category')
    pagination_class = None  # Отключаем пагинацию для товаров
    lookup_field = 'slug'  # Используем slug для поиска
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_featured']
    search_fields = ['name', 'description', 'tags']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ProductDetailSerializer
        return ProductListSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Фильтр по категории через slug
        category_slug = self.request.query_params.get('category', None)
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Фильтр по тегам
        tag = self.request.query_params.get('tag', None)
        if tag:
            queryset = queryset.filter(tags__icontains=tag)
        
        # Только рекомендуемые
        featured = self.request.query_params.get('featured', None)
        if featured == 'true':
            queryset = queryset.filter(is_featured=True)
        
        return queryset

    @action(detail=False, methods=['get'])
    def featured(self, request):
        """Рекомендуемые товары"""
        featured_products = self.get_queryset().filter(is_featured=True)[:8]
        serializer = ProductListSerializer(featured_products, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def fresh(self, request):
        """Новые товары"""
        fresh_products = self.get_queryset().order_by('-created_at')[:8]
        serializer = ProductListSerializer(fresh_products, many=True)
        return Response(serializer.data)
