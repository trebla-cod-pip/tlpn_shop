import asyncio
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


async def send_telegram_message(chat_id: int, text: str, parse_mode: str = 'HTML') -> bool:
    """
    Отправляет сообщение в Telegram

    Args:
        chat_id: ID чата или пользователя
        text: Текст сообщения
        parse_mode: Режим парсинга (HTML или Markdown)

    Returns:
        True если успешно, False иначе
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN не настроен")
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"

    data = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode,
    }

    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                result = await response.json()
                if response.status == 200:
                    logger.info(f"Сообщение отправлено в Telegram: {chat_id}")
                    return True
                else:
                    logger.error(f"Ошибка Telegram API ({response.status}): {result}")
                    return False
    except ImportError:
        logger.error("aiohttp не установлен. Установите: pip install aiohttp")
        return False
    except Exception as e:
        logger.error(f"Ошибка отправки в Telegram: {e}")
        return False


async def send_order_notification(order) -> bool:
    """
    Отправляет уведомление о заказе пользователю и админу
    """
    from analytics.models import TrackingEvent

    logger.info(f"Начало отправки уведомления для заказа #{order.id}")

    # Формируем список товаров
    items_text = ""
    for item in order.items.all():
        items_text += f"• {item.product.name} x {item.quantity} — {item.total}₽\n"

    # Иконка способа связи
    contact_icon = "📱" if order.preferred_contact_method == 'phone' else "✈️"

    # Формируем текст способа связи с учётом краевых случаев
    if order.preferred_contact_method == 'phone':
        contact_text = f"Телефон: {order.phone}"
    else:
        if order.telegram_username:
            contact_text = f"Telegram: @{order.telegram_username}"
        elif order.telegram_first_name:
            contact_text = f"Telegram: {order.telegram_first_name} {order.telegram_last_name or ''}"
        else:
            contact_text = f"Telegram (ID: {order.telegram_user_id})"

    # Имя клиента
    client_name = f"{order.telegram_first_name or ''} {order.telegram_last_name or ''}".strip()
    if not client_name:
        client_name = f"Telegram @{order.telegram_username}" if order.telegram_username else f"Пользователь #{order.telegram_user_id}"

    # Сообщение пользователю
    user_message = f"""
🌷 <b>Заказ #{order.id} принят!</b>

Спасибо за заказ в Tulipa!

📦 <b>Ваш заказ:</b>
{items_text}
💰 <b>Итого:</b> {order.total_amount}₽

🚚 <b>Доставка:</b>
📍 {order.delivery_address}
📅 {order.delivery_date.strftime('%d.%m.%Y')}
⏰ {order.delivery_time or 'В течение дня'}

📞 <b>Контакты:</b>
{order.phone}
{contact_icon} <b>Предпочтительный способ связи:</b> {contact_text}

Мы свяжемся с вами для подтверждения доставки.
    """.strip()

    # Сообщение админу
    admin_message = f"""
🔔 <b>Новый заказ #{order.id}!</b>

👤 <b>Клиент:</b>
• {client_name}
• Телефон: {order.phone}
• <b>Предпочтительный способ связи:</b> {contact_text}

📦 <b>Заказ:</b>
{items_text}
💰 <b>Итого:</b> {order.total_amount}₽

🚚 <b>Доставка:</b>
📍 {order.delivery_address}
📅 {order.delivery_date.strftime('%d.%m.%Y')}
⏰ {order.delivery_time or 'В течение дня'}

💬 <b>Комментарий:</b>
{order.comment or 'Нет'}

<a href='http://localhost:8000/admin/orders/order/{order.id}/change/'>Открыть в админке</a>
    """.strip()

    # Отправляем пользователю (если есть telegram_user_id)
    user_sent = False
    if order.telegram_user_id:
        logger.info(f"Отправка уведомления пользователю #{order.telegram_user_id}")
        try:
            user_sent = await send_telegram_message(order.telegram_user_id, user_message)
            logger.info(f"Уведомление пользователю {'отправлено' if user_sent else 'не отправлено'}")
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю #{order.telegram_user_id}: {e}")
    else:
        logger.warning(f"У заказа #{order.id} нет telegram_user_id, уведомление пользователю не отправлено")

    # Отправляем админу
    admin_sent = False
    if settings.TELEGRAM_ADMIN_ID:
        logger.info(f"Отправка уведомления админу (ID: {settings.TELEGRAM_ADMIN_ID})")
        try:
            admin_sent = await send_telegram_message(
                int(settings.TELEGRAM_ADMIN_ID),
                admin_message
            )
            logger.info(f"Уведомление админу {'отправлено' if admin_sent else 'не отправлено'}")
        except Exception as e:
            logger.error(f"Ошибка отправки админу: {e}")
    else:
        logger.warning("TELEGRAM_ADMIN_ID не настроен")

    # Трекаем событие purchase для аналитики
    try:
        TrackingEvent.objects.create(
            event_type='purchase',
            event_data={
                'order_id': order.id,
                'total_amount': str(order.total_amount),
                'items_count': order.get_items_count()
            }
        )
        logger.info(f"Событие purchase сохранено для заказа #{order.id}")
    except Exception as e:
        logger.error(f"Ошибка трекинга purchase: {e}")

    result = user_sent and admin_sent
    logger.info(f"Результат отправки уведомлений: user={user_sent}, admin={admin_sent}, total={result}")
    return result


def send_order_notification_sync(order) -> bool:
    """
    Синхронная обёртка для отправки уведомлений
    """
    logger.info(f"send_order_notification_sync вызван для заказа #{order.id}")

    # Проверяем, есть ли уже запущенный event loop
    try:
        loop = asyncio.get_running_loop()
        # Если loop уже запущен, создаём новый в отдельном потоке
        logger.info("Event loop уже запущен, используем run_coroutine_threadsafe")
        future = asyncio.run_coroutine_threadsafe(send_order_notification(order), loop)
        return future.result(timeout=10)  # Ждём максимум 10 секунд
    except RuntimeError:
        # Нет running loop, создаём новый
        logger.info("Event loop не запущен, создаём новый")
        return asyncio.run(send_order_notification(order))
