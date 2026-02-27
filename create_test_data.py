"""
Скрипт для создания тестовых данных
Запуск: python manage.py shell < create_test_data.py
"""

from store.models import Category, Product
from django.core.files.base import ContentFile
import requests
from io import BytesIO

def create_test_data():
    print("Создание категорий...")
    
    # Категории
    categories_data = [
        {'name': 'White', 'description': 'Белые тюльпаны - классика и элегантность'},
        {'name': 'Pastel mix', 'description': 'Нежные пастельные оттенки'},
        {'name': 'Seasonal', 'description': 'Сезонные сорта'},
        {'name': 'Premium', 'description': 'Премиальные букеты'},
    ]
    
    categories = {}
    for cat_data in categories_data:
        cat, created = Category.objects.get_or_create(
            name=cat_data['name'],
            defaults=cat_data
        )
        categories[cat_data['name']] = cat
        print(f"  {'Создана' if created else 'Существует'} категория: {cat.name}")
    
    print("\nСоздание товаров...")
    
    # Товары с изображениями из шаблонов
    products_data = [
        {
            'name': 'Nordic White Tulips',
            'price': '65.00',
            'category': categories['White'],
            'description': 'Freshly picked from the fields of Holland, these pristine white tulips bring an elegant and calming presence to any space.',
            'tags': 'Bestseller',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/d6471770-84ed-470c-8349-c8f125af64ac.jpg',
        },
        {
            'name': 'Pastel Dawn Mix',
            'price': '72.00',
            'category': categories['Pastel mix'],
            'description': 'Soft pastel pink and white tulips in an airy composition.',
            'tags': 'New',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/654367ff-6b58-4222-83cb-6afc65b11ab5.jpg',
        },
        {
            'name': 'Noir Contrast',
            'price': '78.00',
            'category': categories['Premium'],
            'description': 'Deep burgundy and white tulip bouquet with minimal backdrop.',
            'tags': 'Limited',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/dd41c14f-459e-4c2a-b9ff-d14fe24104e9.jpg',
        },
        {
            'name': 'Sunlit Meadow',
            'price': '59.00',
            'category': categories['Seasonal'],
            'description': 'Bright yellow tulips with green stems in Scandinavian style.',
            'tags': 'Spring',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/75f9e861-9578-43c7-b842-3227e0e73ef9.jpg',
        },
        {
            'name': 'Queen of Night',
            'price': '85.00',
            'category': categories['Premium'],
            'description': 'Dark purple-black tulips, luxury and mysterious.',
            'tags': 'Limited',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/d7838824-6c69-4596-ae9e-d0d299a10789.jpg',
        },
        {
            'name': 'Apricot Beauty',
            'price': '60.00',
            'category': categories['Pastel mix'],
            'description': 'Peach orange tulips with soft daylight beauty.',
            'tags': 'Bestseller',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/ea3e0247-d760-489e-996d-fda10dd4d656.jpg',
        },
        {
            'name': 'Flaming Parrot',
            'price': '75.00',
            'category': categories['Seasonal'],
            'description': 'Red yellow fringed tulips with vivid details.',
            'tags': 'New',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/61f3407a-dc57-489a-9f13-83700b420e12.jpg',
        },
        {
            'name': 'White French Tulips',
            'price': '65.00',
            'category': categories['White'],
            'description': 'Freshly picked from the fields of Holland, these pristine white tulips bring an elegant and calming presence to any space. Wrapped in our signature sustainable paper.',
            'tags': 'Bestseller',
            'is_featured': True,
            'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/d298b649-b97f-474b-ac8b-017e7e43be51.jpg',
        },
    ]
    
    for prod_data in products_data:
        image_url = prod_data.pop('image_url')
        
        product, created = Product.objects.get_or_create(
            name=prod_data['name'],
            defaults=prod_data
        )
        
        if created:
            # Загружаем изображение
            try:
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    image_file = BytesIO(response.content)
                    product.image.save(f'{product.slug}.jpg', ContentFile(image_file.read()), save=True)
                    print(f"  Создан товар: {product.name} (с изображением)")
            except Exception as e:
                print(f"  Создан товар: {product.name} (без изображения: {e})")
        else:
            print(f"  Существует товар: {product.name}")
    
    print("\n✓ Тестовые данные созданы!")
    print(f"  Категорий: {Category.objects.count()}")
    print(f"  Товаров: {Product.objects.count()}")


if __name__ == '__main__':
    create_test_data()
