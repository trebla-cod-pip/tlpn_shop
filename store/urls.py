from django.urls import path, include
from rest_framework.routers import DefaultRouter
from store.views import CategoryViewSet, ProductViewSet
from orders.views import OrderViewSet

router = DefaultRouter()
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'products', ProductViewSet, basename='product')
router.register(r'orders', OrderViewSet, basename='order')

urlpatterns = [
    path('', include(router.urls)),
]
