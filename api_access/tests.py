import json
from decimal import Decimal

from django.test import TestCase, override_settings

from accounts.models import TelegramUser
from api_access.models import DeveloperApiKey
from catalog.models import Product, StockItem


@override_settings(TELEGRAM_BOT_TOKEN="")
class DeveloperApiTests(TestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(telegram_id=3001, balance=Decimal("10.00"))
        self.raw_key, self.api_key = DeveloperApiKey.create_for_user(self.user)
        self.product = Product.objects.create(name="API Product", price=Decimal("2.00"))
        StockItem.objects.create(product=self.product, secret_content="api-stock")
        StockItem.objects.create(product=self.product, secret_content="api-stock-2")

    def auth(self):
        return {"HTTP_AUTHORIZATION": f"Bearer {self.raw_key}"}

    def test_products_requires_api_key(self):
        response = self.client.get("/api/v1/products/")

        self.assertEqual(response.status_code, 401)

    @override_settings(DEVELOPER_API_ENABLED=False)
    def test_products_can_be_disabled_globally(self):
        response = self.client.get("/api/v1/products/", **self.auth())

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "developer_api_disabled")

    def test_products_lists_active_products(self):
        response = self.client.get("/api/v1/products/", **self.auth())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["products"][0]["name"], "API Product")

    def test_create_order_delivers_stock_and_updates_api_stats(self):
        response = self.client.post(
            "/api/v1/orders/",
            data=json.dumps({"product_id": self.product.pk}),
            content_type="application/json",
            **self.auth(),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["order"]["secret_content"], "api-stock")
        self.user.refresh_from_db()
        self.api_key.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("8.00"))
        self.assertEqual(self.api_key.total_orders, 1)
        self.assertEqual(self.api_key.total_spend, Decimal("2.00"))

    def test_create_order_supports_quantity(self):
        response = self.client.post(
            "/api/v1/orders/",
            data=json.dumps({"product_id": self.product.pk, "quantity": 2}),
            content_type="application/json",
            **self.auth(),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["order"]["quantity"], 2)
        self.assertEqual(response.json()["order"]["price_paid"], "4.00")

    def test_create_order_enforces_quantity_limit(self):
        self.api_key.max_order_quantity = 1
        self.api_key.save(update_fields=["max_order_quantity"])

        response = self.client.post(
            "/api/v1/orders/",
            data=json.dumps({"product_id": self.product.pk, "quantity": 2}),
            content_type="application/json",
            **self.auth(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "quantity_limit_exceeded")

    def test_create_order_enforces_daily_spend_limit(self):
        self.api_key.daily_spend_limit = Decimal("1.00")
        self.api_key.save(update_fields=["daily_spend_limit"])

        response = self.client.post(
            "/api/v1/orders/",
            data=json.dumps({"product_id": self.product.pk}),
            content_type="application/json",
            **self.auth(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "daily_spend_limit_exceeded")

    def test_create_order_enforces_order_scope(self):
        self.api_key.can_create_orders = False
        self.api_key.save(update_fields=["can_create_orders"])

        response = self.client.post(
            "/api/v1/orders/",
            data=json.dumps({"product_id": self.product.pk}),
            content_type="application/json",
            **self.auth(),
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"], "orders_disabled")

# Create your tests here.
