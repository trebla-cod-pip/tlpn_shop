import html
import logging
from typing import Any

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _escape(value: Any) -> str:
    return html.escape(_clean_text(value), quote=False)


def _with_scheme(url: str) -> str:
    if not url:
        return ""
    if url.startswith("http://") or url.startswith("https://"):
        return url
    return f"https://{url}"


def send_telegram_message(chat_id: Any, text: str, parse_mode: str = "HTML") -> bool:
    token = _clean_text(getattr(settings, "TELEGRAM_BOT_TOKEN", ""))
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty")
        return False

    chat_id = _clean_text(chat_id)
    if not chat_id:
        logger.warning("chat_id is empty, skip telegram message")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    logger.info(f"Sending Telegram message to {chat_id}")

    try:
        response = requests.post(url, json=payload, timeout=15)
        logger.info(f"Telegram response status: {response.status_code}")
    except requests.RequestException as exc:
        logger.error("Telegram request failed for chat_id=%s: %s", chat_id, exc)
        return False

    try:
        result = response.json()
        logger.info(f"Telegram response: {result}")
    except ValueError:
        result = {"raw": response.text}
        logger.warning(f"Telegram non-JSON response: {result}")

    if response.ok and result.get("ok") is True:
        logger.info("Telegram message sent to chat_id=%s", chat_id)
        return True

    logger.error(
        "Telegram API rejected message for chat_id=%s status=%s response=%s",
        chat_id,
        response.status_code,
        result,
    )
    return False


def _build_items_text(order) -> str:
    lines = []
    for item in order.items.all().select_related("product"):
        product_name = _escape(getattr(item.product, "name", "Item"))
        lines.append(f"- {product_name} x {item.quantity} - {_escape(item.total)} RUB")
    return "\n".join(lines) or "- No items"


def _format_contact_text(order) -> str:
    if order.preferred_contact_method == "phone":
        return f"Phone: {_escape(order.phone)}"

    username = _clean_text(order.telegram_username).lstrip("@")
    if username:
        return f"Telegram: @{_escape(username)}"

    full_name = _clean_text(f"{order.telegram_first_name or ''} {order.telegram_last_name or ''}")
    if full_name:
        return f"Telegram: {_escape(full_name)}"

    if order.telegram_user_id:
        return f"Telegram ID: {_escape(order.telegram_user_id)}"

    return "Not provided"


def _client_name(order) -> str:
    full_name = _clean_text(f"{order.telegram_first_name or ''} {order.telegram_last_name or ''}")
    if full_name:
        return full_name

    username = _clean_text(order.telegram_username).lstrip("@")
    if username:
        return f"@{username}"

    if order.telegram_user_id:
        return f"User #{order.telegram_user_id}"

    return "Customer"


def send_order_notification(order) -> bool:
    """
    Отправляет уведомление о заказе пользователю и админу
    """
    from analytics.models import TrackingEvent

    # Формируем список товаров
    items_text = ""
    for item in order.items.all():
        items_text += f"• {item.product.name} x {item.quantity} — {item.total}₽\n"

    # Иконка способа связи
    contact_icon = "📱" if order.preferred_contact_method == 'phone' else "✈️"

    # Формируем текст способа связи
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

    user_sent = False
    admin_sent = False

    # Получаем chat_id пользователя из TelegramUser
    user_chat_id = None
    if order.telegram_user_id:
        try:
            from store.models import TelegramUser
            tg_user = TelegramUser.objects.filter(telegram_id=order.telegram_user_id).first()
            if tg_user and tg_user.chat_id:
                user_chat_id = tg_user.chat_id
                logger.info(f"Найден chat_id {user_chat_id} для пользователя {order.telegram_user_id}")
            else:
                logger.warning(f"Order #{order.id}: telegram_user_id={order.telegram_user_id}, но chat_id не найден")
        except Exception as e:
            logger.error(f"Error getting TelegramUser for order #{order.id}: {e}")

    # Отправляем пользователю
    if user_chat_id:
        logger.info(f"Отправка сообщения пользователю в chat_id={user_chat_id}")
        try:
            user_sent = send_telegram_message(user_chat_id, user_message)
            logger.info(f"Результат отправки пользователю: {user_sent}")
        except Exception as e:
            logger.error(f"Ошибка отправки пользователю #{order.telegram_user_id}: {e}")
    elif order.telegram_user_id:
        logger.warning(f"Order #{order.id}: не удалось отправить пользователю - нет chat_id")
    else:
        logger.warning(f"Order #{order.id}: нет telegram_user_id")

    # Отправляем админу
    admin_chat_id = _clean_text(getattr(settings, "TELEGRAM_ADMIN_ID", ""))
    if admin_chat_id:
        try:
            admin_sent = send_telegram_message(int(admin_chat_id), admin_message)
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
    except Exception as e:
        logger.error(f"Ошибка трекинга purchase: {e}")

    need_user = bool(user_chat_id)
    need_admin = bool(admin_chat_id)

    # Success means all configured recipients were delivered.
    return (not need_user or user_sent) and (not need_admin or admin_sent)


def send_order_notification_sync(order) -> bool:
    logger.info("send_order_notification_sync called for order #%s", order.id)
    return send_order_notification(order)
