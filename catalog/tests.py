from decimal import Decimal

from django.test import TestCase

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

# Create your tests here.
