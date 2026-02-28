from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.conf import settings
from store.models import Product, Category


class StaticViewSitemap(Sitemap):
    """Sitemap для статических страниц"""
    priority = 0.8
    changefreq = 'daily'

    def items(self):
        return ['home', 'bag', 'profile']

    def location(self, item):
        return reverse(item)


class ProductSitemap(Sitemap):
    """Sitemap для товаров"""
    priority = 0.9
    changefreq = 'weekly'
    protocol = getattr(settings, 'SITEMAP_PROTOCOL', 'https')

    def items(self):
        return Product.objects.filter(is_active=True).select_related('category')

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return f'/item/{obj.slug}/'


class CategorySitemap(Sitemap):
    """Sitemap для категорий"""
    priority = 0.7
    changefreq = 'weekly'
    protocol = getattr(settings, 'SITEMAP_PROTOCOL', 'https')

    def items(self):
        return Category.objects.filter(is_active=True)

    def lastmod(self, obj):
        return obj.created_at

    def location(self, obj):
        return f'/?category={obj.slug}'
