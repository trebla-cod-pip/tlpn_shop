"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.sitemaps.views import sitemap
from store import views
from config.sitemap import StaticViewSitemap, ProductSitemap, CategorySitemap
from config.views import robots, order_stats, delivery_info

sitemaps = {
    'static': StaticViewSitemap,
    'products': ProductSitemap,
    'categories': CategorySitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots, name='robots'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('stats/', order_stats, name='order_stats'),  # Статистика заказов
    path('delivery/', delivery_info, name='delivery'),  # Информация о доставке
    path('', views.home, name='home'),
    path('item/<slug:slug>/', views.item, name='item'),
    path('bag/', views.bag, name='bag'),
    path('order-success/', views.order_success, name='order_success'),
    path('cart-sync/', views.sync_cart_session, name='cart_sync'),
    path('profile/', views.profile, name='profile'),
    path('api/', include('store.urls')),
    path('analytics/', include('analytics.urls')),
    path('telegram/', include('telegram_app.urls')),
]

# Раздача медиа файлов в режиме разработки
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
