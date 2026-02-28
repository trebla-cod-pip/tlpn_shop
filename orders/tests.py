from datetime import date

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from orders.models import Order, OrderItem
from orders.serializers import OrderSerializer
from store.models import Category, Product


class OrderSerializerTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Flowers")
        self.product = Product.objects.create(
            name="Rose",
            price=100,
            image=SimpleUploadedFile("rose.jpg", b"filecontent", content_type="image/jpeg"),
            category=self.category,
            stock=10,
            is_active=True,
        )

    def test_serializer_contains_contact_fields_for_checkout_prefill(self):
        order = Order.objects.create(
            telegram_user_id=12345,
            telegram_username="test_user",
            phone="+79990001122",
            preferred_contact_method="phone",
            delivery_address="Test street 1",
            delivery_date=date.today(),
            total_amount=100,
        )
        OrderItem.objects.create(order=order, product=self.product, quantity=1, price=100, total=100)

        data = OrderSerializer(order).data

        self.assertEqual(data["phone"], "+79990001122")
        self.assertEqual(data["telegram_user_id"], 12345)
        self.assertEqual(data["telegram_username"], "test_user")
        self.assertEqual(data["preferred_contact_method"], "phone")
