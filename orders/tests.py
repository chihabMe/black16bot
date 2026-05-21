from decimal import Decimal

from django.test import TransactionTestCase, override_settings

from accounts.models import TelegramUser
from catalog.models import Product, StockItem
from orders.models import Order
from orders.services import InsufficientBalance, OutOfStock, purchase_product, replace_order_stock


@override_settings(TELEGRAM_BOT_TOKEN="")
class PurchaseProductTests(TransactionTestCase):
    reset_sequences = True

    def setUp(self):
        self.user = TelegramUser.objects.create(telegram_id=1001, balance=Decimal("10.00"))
        self.product = Product.objects.create(name="Test Product", price=Decimal("3.50"))

    def test_purchase_deducts_balance_and_sells_one_stock_item(self):
        stock = StockItem.objects.create(product=self.product, secret_content="login:password")

        result = purchase_product(user_id=self.user.pk, product_id=self.product.pk)

        self.user.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("6.50"))
        self.assertEqual(stock.status, StockItem.Status.SOLD)
        self.assertEqual(stock.sold_to, self.user)
        self.assertEqual(result.order.status, Order.Status.COMPLETED)
        self.assertEqual(result.order.stock_item, stock)
        self.assertEqual(result.order.quantity, 1)
        self.assertEqual(result.order.delivered_payload, "login:password")

    def test_purchase_can_buy_multiple_stock_items_atomically(self):
        StockItem.objects.create(product=self.product, secret_content="first")
        StockItem.objects.create(product=self.product, secret_content="second")

        result = purchase_product(user_id=self.user.pk, product_id=self.product.pk, quantity=2)

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("3.00"))
        self.assertEqual(result.order.quantity, 2)
        self.assertEqual(result.order.price_paid, Decimal("7.00"))
        self.assertEqual(result.order.delivered_payload, "first\n\nsecond")
        self.assertEqual(
            StockItem.objects.filter(product=self.product, status=StockItem.Status.SOLD).count(),
            2,
        )

    def test_purchase_rejects_insufficient_balance_without_selling_stock(self):
        self.user.balance = Decimal("1.00")
        self.user.save(update_fields=["balance"])
        stock = StockItem.objects.create(product=self.product, secret_content="login:password")

        with self.assertRaises(InsufficientBalance):
            purchase_product(user_id=self.user.pk, product_id=self.product.pk)

        self.user.refresh_from_db()
        stock.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("1.00"))
        self.assertEqual(stock.status, StockItem.Status.AVAILABLE)

    def test_purchase_rejects_out_of_stock_without_charging_user(self):
        with self.assertRaises(OutOfStock):
            purchase_product(user_id=self.user.pk, product_id=self.product.pk)

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("10.00"))

    def test_replace_order_stock_sends_new_available_stock(self):
        original = StockItem.objects.create(product=self.product, secret_content="old")
        replacement = StockItem.objects.create(product=self.product, secret_content="new")
        result = purchase_product(user_id=self.user.pk, product_id=self.product.pk)

        replace_order_stock(order_id=result.order.pk)

        result.order.refresh_from_db()
        original.refresh_from_db()
        replacement.refresh_from_db()
        self.assertEqual(result.order.status, Order.Status.REPLACED)
        self.assertEqual(result.order.stock_item, replacement)
        self.assertEqual(original.status, StockItem.Status.REPLACED)
        self.assertEqual(replacement.status, StockItem.Status.SOLD)

# Create your tests here.
