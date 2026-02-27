from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import render
from store.models import Category, Product
from store.serializers import CategorySerializer, ProductListSerializer, ProductDetailSerializer


# ============ Web Views ============

def home(request):
    """Главная страница"""
    return render(request, 'store/home.html')


def item(request, slug):
    """Страница товара"""
    return render(request, 'store/item.html', {'slug': slug})


def bag(request):
    """Корзина"""
    return render(request, 'store/bag.html')


def favorites(request):
    """Избранное"""
    return render(request, 'store/favorites.html')


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
