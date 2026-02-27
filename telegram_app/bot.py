import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import WebAppInfo, InlineKeyboardMarkup, InlineKeyboardButton
from django.conf import settings

logger = logging.getLogger(__name__)

# Инициализация бота
bot = None
dp = None


def init_bot():
    """Инициализация бота"""
    global bot, dp
    
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN не настроен")
        return False
    
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()
    
    # Регистрируем хендлеры
    dp.message(register_start_handler)
    
    return True


async def register_start_handler(message: types.Message):
    """Обработчик команды /start"""
    # Создаём клавиатуру с кнопкой WebApp
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🌷 Открыть магазин",
                    web_app=WebAppInfo(url=settings.TELEGRAM_WEBAPP_URL)
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 Мои заказы",
                    web_app=WebAppInfo(url=f"{settings.TELEGRAM_WEBAPP_URL}/profile/")
                )
            ]
        ]
    )
    
    welcome_text = """
🌷 <b>Dobro pozhalovat' v Tulipa!</b>

Premium tulip boutique s dostavkoy po gorodu.

Nashite buketы:
• Svezhie tyulpany iz Gollandii
• Minimalistichnyy skandinavskiy stil'
• Dostavka v den' zakaza

Nazhmite "Otkryt' magazin", chtoby nachat'!
    """.strip()
    
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode='HTML')


async def send_order_message(chat_id: int, order_data: dict):
    """Отправляет сообщение о заказе"""
    if not bot:
        return False
    
    text = f"""
🌷 <b>Заказ #{order_data.get('id')} принят!</b>

Спасибо за заказ в Tulipa!

📦 <b>Ваш заказ:</b>
{order_data.get('items_text', '')}
💰 <b>Итого:</b> {order_data.get('total', '0')}₽

🚚 <b>Доставка:</b>
📍 {order_data.get('address', '')}
📅 {order_data.get('date', '')}

Мы свяжемся с вами для подтверждения.
    """.strip()
    
    try:
        await bot.send_message(chat_id, text, parse_mode='HTML')
        return True
    except Exception as e:
        logger.error(f"Ошибка отправки сообщения: {e}")
        return False


async def start_bot_polling():
    """Запуск поллинга бота"""
    if not bot or not dp:
        logger.error("Бот не инициализирован")
        return
    
    logger.info("Запуск бота...")
    await dp.start_polling(bot)


async def stop_bot():
    """Остановка бота"""
    if bot:
        await bot.session.close()
