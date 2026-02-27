from django.core.management.base import BaseCommand
from store.models import Category, Product
from django.core.files.base import ContentFile
import requests
from io import BytesIO


class Command(BaseCommand):
    help = 'Sozdanie testovykh dannykh dlya magazina Tulipa'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('Sozdanie kategoriy...'))
        
        # Kategorii
        categories_data = [
            {'name': 'Belye', 'description': 'Belye tyulpany - klassika i elegantnost'},
            {'name': 'Pastel', 'description': 'Nezhnye pastelnye ottenki'},
            {'name': 'Sezonnye', 'description': 'Sezonnye sorta'},
            {'name': 'Premium', 'description': 'Premiumnye bukety'},
        ]
        
        categories = {}
        for cat_data in categories_data:
            cat, created = Category.objects.get_or_create(
                slug=cat_data['name'].lower(),  # Used slug for lookup
                defaults=cat_data
            )
            categories[cat_data['name']] = cat
            status = 'Sozdana' if created else 'Sushchestvuyet'
            self.stdout.write(f'  {status}: {cat.name} (slug: {cat.slug})')
        
        self.stdout.write(self.style.SUCCESS('\nSozdanie tovarov...'))
        
        # Tovary s russkimi nazvaniyami i opisaniyami
        # name_en используется для генерации slug
        products_data = [
            {
                'name': 'Nordic White - Букет белых тюльпанов',
                'name_en': 'nordic-white-bouquet',
                'price': '2500.00',
                'category_slug': 'belye',
                'description': 'Свежие белые тюльпаны из Голландии. Минималистичный букет в скандинавском стиле. Идеально подходит для светлого интерьера.',
                'tags': 'Хит',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/d6471770-84ed-470c-8349-c8f125af64ac.jpg',
            },
            {
                'name': 'Pastel Dawn - Пастельный микс',
                'name_en': 'pastel-dawn-mix',
                'price': '2900.00',
                'category_slug': 'pastel',
                'description': 'Нежные розово-белые тюльпаны в воздушной композиции. Романтический букет для особых случаев.',
                'tags': 'Новинка',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/654367ff-6b58-4222-83cb-6afc65b11ab5.jpg',
            },
            {
                'name': 'Noir Contrast - Тёмный контраст',
                'name_en': 'noir-contrast',
                'price': '3200.00',
                'category_slug': 'premium',
                'description': 'Глубокие бордовые и белые тюльпаны. Современный букет в стиле минимализм.',
                'tags': 'Ограниченный',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/dd41c14f-459e-4c2a-b9ff-d14fe24104e9.jpg',
            },
            {
                'name': 'Sunlit Meadow - Солнечный луг',
                'name_en': 'sunlit-meadow',
                'price': '2300.00',
                'category_slug': 'sezonnye',
                'description': 'Яркие жёлтые тюльпаны с зелёными стеблями. Скандинавский стиль для весеннего настроения.',
                'tags': 'Весна',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/75f9e861-9578-43c7-b842-3227e0e73ef9.jpg',
            },
            {
                'name': 'Queen of Night - Королева ночи',
                'name_en': 'queen-of-night',
                'price': '3500.00',
                'category_slug': 'premium',
                'description': 'Тёмные фиолетово-чёрные тюльпаны. Роскошный и загадочный букет.',
                'tags': 'Ограниченный,Хит',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/d7838824-6c69-4596-ae9e-d0d299a10789.jpg',
            },
            {
                'name': 'Apricot Beauty - Абрикосовая красота',
                'name_en': 'apricot-beauty',
                'price': '2600.00',
                'category_slug': 'pastel',
                'description': 'Персиково-оранжевые тюльпаны с мягким дневным освещением. Нежный букет для тёплых чувств.',
                'tags': 'Хит',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/ea3e0247-d760-489e-996d-fda10dd4d656.jpg',
            },
            {
                'name': 'Flaming Parrot - Огненный попугай',
                'name_en': 'flaming-parrot',
                'price': '3100.00',
                'category_slug': 'sezonnye',
                'description': 'Красно-жёлтые бахромчатые тюльпаны с яркими деталями. Экзотический букет для смелых решений.',
                'tags': 'Новинка',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/61f3407a-dc57-489a-9f13-83700b420e12.jpg',
            },
            {
                'name': 'White French - Французские белые',
                'name_en': 'white-french',
                'price': '2500.00',
                'category_slug': 'belye',
                'description': 'Свежесобранные белые тюльпаны из Голландии. Элегантность и чистота в каждой детали. Упакованы в нашу фирменную бумагу.',
                'tags': 'Хит',
                'is_featured': True,
                'image_url': 'https://storage.googleapis.com/banani-generated-images/generated-images/d298b649-b97f-474b-ac8b-017e7e43be51.jpg',
            },
        ]
        
        for prod_data in products_data:
            image_url = prod_data.pop('image_url')
            category_slug = prod_data.pop('category_slug')
            name_en = prod_data.pop('name_en')
            
            # Получаем категорию по slug
            category = categories.get(category_slug.capitalize()) or Category.objects.get(slug=category_slug)
            
            # Создаём товар с готовым slug
            product, created = Product.objects.get_or_create(
                slug=name_en,
                defaults={**prod_data, 'category': category},
            )
            
            if created and image_url:
                try:
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        image_file = BytesIO(response.content)
                        product.image.save(f'{product.slug}.jpg', ContentFile(image_file.read()), save=True)
                        self.stdout.write(f'  Sozdan: {product.name} (s izobrazheniyem)')
                except Exception as e:
                    self.stdout.write(f'  Sozdan: {product.name} (bez izobrazheniya)')
            else:
                status = 'Sozdan' if created else 'Sushchestvuyet'
                self.stdout.write(f'  {status}: {product.name}')
        
        self.stdout.write(self.style.SUCCESS('\n[OK] Gotovo!'))
        self.stdout.write(f'  Kategiriy: {Category.objects.count()}')
        self.stdout.write(f'  Tovarov: {Product.objects.count()}')
