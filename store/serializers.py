# helper to reuse WebP spec serialization
from rest_framework import serializers

from store.models import Category, Product


def _webp_url(obj, attr):
    spec = getattr(obj, attr, None)
    return spec.url if getattr(spec, 'url', None) else None


class CategorySerializer(serializers.ModelSerializer):
    """Сериалайзер для категорий"""
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'image', 'is_active', 'products_count']
        read_only_fields = ['slug']

    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()


class ProductListSerializer(serializers.ModelSerializer):
    """Сериалайзер для списка товаров"""
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_slug = serializers.CharField(source='category.slug', read_only=True)
    tags_list = serializers.SerializerMethodField()
    discount = serializers.ReadOnlyField()
    image_webp_400 = serializers.SerializerMethodField()
    image_webp_800 = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'old_price',
            'image', 'cart_image', 'category', 'category_name', 'category_slug',
            'tags_list', 'is_active', 'is_featured', 'stock', 'discount', 'created_at',
            'image_webp_400', 'image_webp_800'
        ]
        read_only_fields = ['slug']

    def get_tags_list(self, obj):
        if obj.tags:
            return [tag.strip() for tag in obj.tags.split(',')]
        return []

    def get_image_webp_400(self, obj):
        return _webp_url(obj, 'image_webp_400')

    def get_image_webp_800(self, obj):
        return _webp_url(obj, 'image_webp_800')


class ProductDetailSerializer(serializers.ModelSerializer):
    """Сериалайзер для детальной информации о товаре"""
    category = CategorySerializer(read_only=True)
    tags_list = serializers.SerializerMethodField()
    discount = serializers.ReadOnlyField()
    related_products = serializers.SerializerMethodField()
    image_webp_400 = serializers.SerializerMethodField()
    image_webp_800 = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'old_price',
            'image', 'cart_image', 'category', 'tags_list', 'is_active', 'is_featured',
            'stock', 'discount', 'created_at', 'updated_at', 'related_products',
            'image_webp_400', 'image_webp_800'
        ]
        read_only_fields = ['slug']

    def get_tags_list(self, obj):
        if obj.tags:
            return [tag.strip() for tag in obj.tags.split(',')]
        return []

    def get_related_products(self, obj):
        """Похожие товары из той же категории"""
        related = Product.objects.filter(
            category=obj.category,
            is_active=True
        ).exclude(id=obj.id)[:4]
        return ProductListSerializer(related, many=True).data
