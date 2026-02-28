
from django.db import models
from django.utils import timezone
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFit


def translit_slug(text):
    """Транслитерация русских букв в slug"""
    translits = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd',
        'е': 'e', 'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i',
        'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n',
        'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't',
        'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch',
        'ш': 'sh', 'щ': 'sch', 'ъ': '', 'ы': 'y', 'ь': '',
        'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D',
        'Е': 'E', 'Ё': 'Yo', 'Ж': 'Zh', 'З': 'Z', 'И': 'I',
        'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M', 'Н': 'N',
        'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T',
        'У': 'U', 'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch',
        'Ш': 'Sh', 'Щ': 'Sch', 'Ъ': '', 'Ы': 'Y', 'Ь': '',
        'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        ' ': '-', '_': '', '.': '', ',': '', '!': '', '?': '',
        '(': '', ')': '', '[': '', ']': '', '/': '-', '\\': '-',
    }
    text = text.lower()
    for ru, en in translits.items():
        text = text.replace(ru, en)
    # Удаляем недопустимые символы и оставляем только a-z, 0-9, -, _
    result = ''
    for char in text:
        if char.isalnum() or char in '-_':
            result += char
        elif ord(char) > 127:
            # Пропускаем не-ASCII символы
            continue
    # Очищаем от множественных дефисов
    while '--' in result:
        result = result.replace('--', '-')
    return result.strip('-_')


class Category(models.Model):
    """Категория товаров (например: Белые, Пастель, Сезонные)"""
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True, blank=True, verbose_name='Slug')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name='Изображение')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = translit_slug(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    """Товар - букет тюльпанов"""
    name = models.CharField(max_length=200, verbose_name='Название')
    slug = models.SlugField(unique=True, blank=True, verbose_name='Slug')
    description = models.TextField(blank=True, verbose_name='Описание')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена')
    old_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, verbose_name='Старая цена')
    image = models.ImageField(upload_to='products/', verbose_name='Изображение')
    cart_image = models.ImageField(upload_to='products/cart/', blank=True, null=True, verbose_name='Изображение для корзины')
    image_webp = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='WebP версия')
    image_webp_400 = ImageSpecField(
        source='image',
        processors=[ResizeToFit(400, 400)],
        format='WEBP',
        options={'quality': 80},
    )
    image_webp_800 = ImageSpecField(
        source='image',
        processors=[ResizeToFit(800, 800)],
        format='WEBP',
        options={'quality': 80},
    )
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products', verbose_name='Категория')
    tags = models.CharField(max_length=200, blank=True, help_text='Теги через запятую (Хит, Новинка, Ограниченный)', verbose_name='Теги')
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    is_featured = models.BooleanField(default=False, verbose_name='Рекомендуемый')
    stock = models.PositiveIntegerField(default=0, verbose_name='Количество на складе')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = translit_slug(self.name)
            slug = base_slug
            counter = 1
            # Проверяем уникальность slug
            while Product.objects.filter(slug=slug).exists():
                slug = f'{base_slug}-{counter}'
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    @property
    def discount(self):
        """Процент скидки"""
        if self.old_price and self.old_price > self.price:
            return int(((self.old_price - self.price) / self.old_price) * 100)
        return 0

    @property
    def image_webp_url(self):
        """Возвращает URL WebP изображения или оригинал если WebP нет"""
        # Сначала пробуем image_webp (ручное WebP)
        if self.image_webp:
            try:
                return self.image_webp.url
            except:
                pass
        
        # Потом пробуем image_webp_800 (ImageKit кэш)
        try:
            return self.image_webp_800.url
        except:
            pass
        
        # Fallback на оригинал
        return self.image.url if self.image else None


class TelegramUser(models.Model):
    """
    Пользователь Telegram Mini App
    Сохраняет данные из Telegram для аналитики и уведомлений
    """
    telegram_id = models.BigIntegerField(unique=True, verbose_name='Telegram ID')
    username = models.CharField(max_length=100, blank=True, verbose_name='Username')
    first_name = models.CharField(max_length=100, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Фамилия')
    language_code = models.CharField(max_length=10, blank=True, verbose_name='Язык')
    is_premium = models.BooleanField(default=False, verbose_name='Premium')
    
    # Связь с Django User (опционально)
    user = models.OneToOneField(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='telegram_profile',
        verbose_name='Пользователь Django'
    )
    
    # Для уведомлений
    chat_id = models.BigIntegerField(blank=True, null=True, verbose_name='Chat ID для уведомлений')
    
    # Даты
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    last_seen = models.DateTimeField(auto_now=True, verbose_name='Последний раз')
    
    class Meta:
        verbose_name = 'Telegram пользователь'
        verbose_name_plural = 'Telegram пользователи'
        ordering = ['-last_seen']
        indexes = [
            models.Index(fields=['telegram_id']),
            models.Index(fields=['username']),
            models.Index(fields=['last_seen']),
        ]
    
    def __str__(self):
        name = f'{self.first_name} {self.last_name}'.strip() or self.username
        return f'@{name} (ID: {self.telegram_id})'
    
    def update_from_telegram(self, user_data: dict):
        """Обновляет данные пользователя из Telegram"""
        self.username = user_data.get('username', '')
        self.first_name = user_data.get('first_name', '')
        self.last_name = user_data.get('last_name', '')
        self.language_code = user_data.get('language_code', '')
        self.is_premium = user_data.get('is_premium', False)
        self.last_seen = timezone.now()
        self.save()
