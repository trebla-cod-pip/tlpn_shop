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

    try:
        response = requests.post(url, json=payload, timeout=15)
    except requests.RequestException as exc:
        logger.error("Telegram request failed for chat_id=%s: %s", chat_id, exc)
        return False

    try:
        result = response.json()
    except ValueError:
        result = {"raw": response.text}

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
    items_text = _build_items_text(order)
    contact_text = _format_contact_text(order)
    client_name = _escape(_client_name(order))
    address = _escape(order.delivery_address)
    phone = _escape(order.phone)
    total_amount = _escape(order.total_amount)
    comment = _escape(order.comment or "No comment")
    delivery_date = _escape(order.delivery_date.strftime("%d.%m.%Y"))
    delivery_time = _escape(order.delivery_time or "During the day")

    admin_base_url = _with_scheme(_clean_text(getattr(settings, "TELEGRAM_WEBAPP_URL", ""))).rstrip("/")
    admin_link = ""
    if admin_base_url:
        admin_link = f"{admin_base_url}/admin/orders/order/{order.id}/change/"

    user_message = (
        f"<b>Order #{order.id} accepted</b>\n\n"
        f"Items:\n{items_text}\n\n"
        f"<b>Total:</b> {total_amount} RUB\n\n"
        f"<b>Delivery:</b>\n"
        f"{address}\n"
        f"{delivery_date}\n"
        f"{delivery_time}\n\n"
        f"<b>Contact:</b>\n"
        f"{phone}\n"
        f"{contact_text}"
    )

    admin_message = (
        f"<b>New order #{order.id}</b>\n\n"
        f"<b>Client:</b> {client_name}\n"
        f"<b>Phone:</b> {phone}\n"
        f"<b>Preferred contact:</b> {contact_text}\n\n"
        f"<b>Items:</b>\n{items_text}\n\n"
        f"<b>Total:</b> {total_amount} RUB\n\n"
        f"<b>Delivery:</b>\n"
        f"{address}\n"
        f"{delivery_date}\n"
        f"{delivery_time}\n\n"
        f"<b>Comment:</b>\n{comment}"
    )
    if admin_link:
        admin_message += f"\n\n<a href='{admin_link}'>Open in admin</a>"

    user_sent = False
    admin_sent = False

    if order.telegram_user_id:
        user_sent = send_telegram_message(order.telegram_user_id, user_message)
    else:
        logger.warning("Order #%s has no telegram_user_id", order.id)

    admin_chat_id = _clean_text(getattr(settings, "TELEGRAM_ADMIN_ID", ""))
    if admin_chat_id:
        admin_sent = send_telegram_message(admin_chat_id, admin_message)
    else:
        logger.warning("TELEGRAM_ADMIN_ID is empty")

    need_user = bool(order.telegram_user_id)
    need_admin = bool(admin_chat_id)

    # Success means all configured recipients were delivered.
    return (not need_user or user_sent) and (not need_admin or admin_sent)


def send_order_notification_sync(order) -> bool:
    logger.info("send_order_notification_sync called for order #%s", order.id)
    return send_order_notification(order)
