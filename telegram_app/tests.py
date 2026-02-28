from datetime import date
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from orders.models import Order, OrderItem
from store.models import Category, Product
from telegram_app.utils import send_order_notification_sync


class TelegramNotificationTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Flowers")
        self.product = Product.objects.create(
            name="Tulip",
            price=250,
            image=SimpleUploadedFile("tulip.jpg", b"filecontent", content_type="image/jpeg"),
            category=self.category,
            stock=10,
            is_active=True,
        )

    def _create_order(self, telegram_user_id=777):
        order = Order.objects.create(
            telegram_user_id=telegram_user_id,
            telegram_username="buyer_user",
            telegram_first_name="Buyer",
            phone="+79990002233",
            preferred_contact_method="telegram",
            delivery_address="Main street 2",
            delivery_date=date.today(),
            delivery_time="10:00-12:00",
            comment="Call before delivery",
            total_amount=250,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=250, total=250)
        return order

    @override_settings(TELEGRAM_ADMIN_ID="999999")
    @patch("telegram_app.utils.send_telegram_message", autospec=True, return_value=True)
    def test_send_notification_to_user_and_admin(self, mocked_send):
        order = self._create_order(telegram_user_id=777)

        result = send_order_notification_sync(order)

        self.assertTrue(result)
        self.assertEqual(mocked_send.call_count, 2)
        chat_ids = [args[0][0] for args in mocked_send.call_args_list]
        self.assertIn(777, chat_ids)
        self.assertIn("999999", chat_ids)

    @override_settings(TELEGRAM_ADMIN_ID="999999")
    @patch("telegram_app.utils.send_telegram_message", autospec=True, return_value=True)
    def test_send_notification_admin_only_when_user_id_missing(self, mocked_send):
        order = self._create_order(telegram_user_id=None)

        result = send_order_notification_sync(order)

        self.assertTrue(result)
        mocked_send.assert_called_once()
        self.assertEqual(mocked_send.call_args[0][0], "999999")
