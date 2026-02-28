"""
Management command для генерации WebP изображений для всех товаров

Использование:
    python manage.py generate_webp
    python manage.py generate_webp --all  # перегенерировать все
"""

from django.core.management.base import BaseCommand
from django.db.models import Q
from store.models import Product
import logging

logger = logging.getLogger(__name__)


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

    def handle(self, *args, **options):
        regenerate_all = options['all']
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
                # Генерируем image_webp_400
                generated_400 = False
                if regenerate_all or not product.image_webp_400.exists():
                    product.image_webp_400.generate()
                    generated_400 = True

                # Генерируем image_webp_800
                generated_800 = False
                if regenerate_all or not product.image_webp_800.exists():
                    product.image_webp_800.generate()
                    generated_800 = True

                if generated_400 or generated_800:
                    self.stdout.write(self.style.SUCCESS('✅'))
                    success_count += 1
                else:
                    self.stdout.write(self.style.WARNING('⏭️ (уже существует)'))
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
