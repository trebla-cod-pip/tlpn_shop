import asyncio
from django.core.management.base import BaseCommand
from django.conf import settings
from telegram_app.bot import init_bot, start_bot_polling, stop_bot


class Command(BaseCommand):
    help = 'Запуск Telegram бота для Tulipa магазина'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Инициализация Telegram бота...'))
        
        if not settings.TELEGRAM_BOT_TOKEN:
            self.stderr.write(self.style.ERROR('TELEGRAM_BOT_TOKEN не настроен в .env'))
            return
        
        if not init_bot():
            self.stderr.write(self.style.ERROR('Не удалось инициализировать бота'))
            return
        
        self.stdout.write(self.style.SUCCESS('Бот успешно инициализирован'))
        self.stdout.write(f'WebApp URL: {settings.TELEGRAM_WEBAPP_URL}')
        self.stdout.write(self.style.WARNING('Нажмите Ctrl+C для остановки'))
        
        try:
            asyncio.run(start_bot_polling())
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nОстановка бота...'))
            asyncio.run(stop_bot())
            self.stdout.write(self.style.SUCCESS('Бот остановлен'))
