from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounts.models import TelegramUser
from catalog.notifications import notify_users_about_product, product_notification_text
from catalog.models import Product, StockItem
from catalog.services import bulk_create_stock
from security.crypto import decrypt_text


class BulkCreateStockTests(TestCase):
    def test_bulk_create_stock_ignores_blank_lines(self):
        product = Product.objects.create(name="Demo", price=Decimal("1.00"))

        count = bulk_create_stock(product=product, raw_lines="a:b\n\n c:d \n")

        self.assertEqual(count, 2)
        self.assertEqual(StockItem.objects.filter(product=product).count(), 2)
        secrets = [decrypt_text(item.secret_content) for item in StockItem.objects.filter(product=product)]
        self.assertIn("c:d", secrets)


class ProductNotificationTests(TestCase):
    def test_product_notification_text_includes_telegram_account_country(self):
        product = Product.objects.create(
            name="Vietnam Telegram Account",
            product_type=Product.ProductType.TELEGRAM_ACCOUNT,
            country_name="Vietnam",
            price=Decimal("4.00"),
        )

        text = product_notification_text(product, event="product")

        self.assertIn("New product", text)
        self.assertIn("Vietnam", text)

    @patch("catalog.notifications.send_telegram_message", return_value=True)
    def test_notify_users_about_product_skips_disabled_notifications(self, send_message):
        product = Product.objects.create(name="Fresh Product", price=Decimal("1.00"))
        TelegramUser.objects.create(telegram_id=8001, notifications_enabled=True)
        TelegramUser.objects.create(telegram_id=8002, notifications_enabled=False)

        sent, failed = notify_users_about_product(product_id=product.pk, event="stock")

        self.assertEqual(sent, 1)
        self.assertEqual(failed, 0)
        send_message.assert_called_once()
