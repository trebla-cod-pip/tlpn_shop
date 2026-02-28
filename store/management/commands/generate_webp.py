"""
Management command для генерации WebP изображений для всех товаров

Использование:
    python manage.py generate_webp
    python manage.py generate_webp --all  # перегенерировать все
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from store.models import Product
from imagekit.cachefiles import ImageCacheFile
import os
import logging

logger = logging.getLogger(__name__)


def force_generate_webp(imagekit_field):
    """Принудительная генерация WebP с удалением старого файла"""
    if not imagekit_field:
        return False
    
    try:
        # Получаем путь к файлу
        file_path = imagekit_field.name
        
        # Если файл существует - удаляем
        if imagekit_field.storage.exists(file_path):
            imagekit_field.storage.delete(file_path)
        
        # Генерируем заново
        imagekit_field.generate()
        
        # Проверяем что сгенерировалось
        return imagekit_field.storage.exists(file_path)
    except Exception as e:
        logger.error(f"Ошибка генерации WebP: {e}")
        return False


class Command(BaseCommand):
    help = 'Генерирует WebP изображения для товаров'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Перегенерировать все изображения (даже если уже существуют)',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительная генерация без подтверждения',
        )
        parser.add_argument(
            '--regenerate',
            action='store_true',
            help='Удалить старые и сгенерировать заново',
        )

    def handle(self, *args, **options):
        regenerate_all = options['all'] or options['regenerate']
        force = options['force']

        # Получаем все товары с изображениями
        products = Product.objects.filter(
            ~Q(image='') & Q(image__isnull=False)
        )

        total_count = products.count()
        success_count = 0
        error_count = 0
        skipped_count = 0

        self.stdout.write(f'Найдено товаров с изображениями: {total_count}')

        if not force and total_count > 10:
            confirm = input(f'Сгенерировать WebP для {total_count} товаров? (y/n): ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Отменено'))
                return

        for i, product in enumerate(products, 1):
            self.stdout.write(f'[{i}/{total_count}] {product.name}...', ending=' ')

            try:
                generated = False
                
                # Если --regenerate - удаляем старые и генерируем заново
                if regenerate_all:
                    gen_400 = force_generate_webp(product.image_webp_400)
                    gen_800 = force_generate_webp(product.image_webp_800)
                    generated = gen_400 or gen_800
                else:
                    # Просто генерируем если нет
                    try:
                        if not product.image_webp_400.storage.exists(product.image_webp_400.name):
                            product.image_webp_400.generate()
                            generated = True
                        if not product.image_webp_800.storage.exists(product.image_webp_800.name):
                            product.image_webp_800.generate()
                            generated = True
                    except:
                        # Если ошибка при проверке - генерируем принудительно
                        product.image_webp_400.generate()
                        product.image_webp_800.generate()
                        generated = True

                if generated:
                    self.stdout.write(self.style.SUCCESS('✅'))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING('⏭️'))
                    skipped_count += 1

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'❌ {e}'))
                error_count += 1
                logger.error(f'Ошибка генерации WebP для {product.name}: {e}')

        # Итоговый отчёт
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS(f'✅ Успешно: {success_count}'))
        if error_count > 0:
            self.stdout.write(self.style.ERROR(f'❌ Ошибок: {error_count}'))
        if skipped_count > 0:
            self.stdout.write(self.style.WARNING(f'⏭️ Пропущено: {skipped_count}'))
        self.stdout.write('=' * 50)
