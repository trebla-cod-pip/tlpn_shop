# helper to reuse WebP spec serialization
from rest_framework import serializers

from store.models import Category, Product


def _image_exists(image_field):
    """Return False if the source image file is missing."""
    if not image_field or not getattr(image_field, 'name', None):
        return False
    try:
        with image_field.storage.open(image_field.name):
            pass
    except (FileNotFoundError, OSError):
        return False
    return True


def _webp_url(obj, attr):
    # Ensure source image exists before triggering ImageKit.
    if not _image_exists(getattr(obj, 'image', None)):
        return None

    spec = getattr(obj, attr, None)
    if spec is None:
        return None
    try:
        return spec.url
    except (FileNotFoundError, OSError):
        return None


def _safe_image_url(obj):
    """Безопасное получение URL изображения"""
    if not obj.image:
        return None
    try:
        return obj.image.url
    except (FileNotFoundError, OSError, ValueError):
        return None


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
    discount = serializers.SerializerMethodField()
    image_webp_url = serializers.SerializerMethodField()
    image_webp_400 = serializers.SerializerMethodField()
    image_webp_800 = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'old_price',
            'image', 'cart_image', 'category', 'category_name', 'category_slug',
            'tags_list', 'is_active', 'is_featured', 'stock', 'discount', 'created_at',
            'image_webp_url', 'image_webp_400', 'image_webp_800'
        ]
        read_only_fields = ['slug']

    def get_tags_list(self, obj):
        if obj.tags:
            return [tag.strip() for tag in obj.tags.split(',')]
        return []

    def get_discount(self, obj):
        try:
            return obj.discount
        except Exception:
            return 0

    def get_image_webp_url(self, obj):
        """Безопасное получение WebP URL"""
        if not obj.image:
            return None
        try:
            # Пробуем получить image_webp_800
            if hasattr(obj, 'image_webp_800') and obj.image_webp_800:
                try:
                    url = obj.image_webp_800.url
                    if url:
                        return url
                except Exception:
                    pass
            # Fallback на оригинал
            return obj.image.url
        except Exception:
            return None

    def get_image_webp_400(self, obj):
        try:
            if obj.image_webp_400:
                return obj.image_webp_400.url
        except Exception:
            pass
        return _safe_image_url(obj)

    def get_image_webp_800(self, obj):
        try:
            if obj.image_webp_800:
                return obj.image_webp_800.url
        except Exception:
            pass
        return _safe_image_url(obj)


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
        data = ProductListSerializer(related, many=True).data
        return data

    def get_image_webp_400(self, obj):
        return _webp_url(obj, 'image_webp_400')

    def get_image_webp_800(self, obj):
        return _webp_url(obj, 'image_webp_800')
