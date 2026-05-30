from unittest.mock import patch
from decimal import Decimal

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.test import TestCase
from django.utils import timezone

from accounts.models import TelegramUser
from broadcasts.admin import BroadcastAdmin
from broadcasts.models import Broadcast
from broadcasts.services import send_broadcast
from catalog.models import Product, StockItem
from orders.models import Order


class BroadcastTests(TestCase):
    @patch("broadcasts.services.send_telegram_message", return_value=True)
    def test_send_broadcast_skips_users_with_notifications_disabled(self, send_message):
        enabled = TelegramUser.objects.create(telegram_id=7001, notifications_enabled=True)
        TelegramUser.objects.create(telegram_id=7002, notifications_enabled=False)
        broadcast = Broadcast.objects.create(message="New stock")

        send_broadcast(broadcast_id=broadcast.pk)

        broadcast.refresh_from_db()
        self.assertEqual(broadcast.sent_count, 1)
        send_message.assert_called_once_with(enabled.telegram_id, "New stock")

    @patch("broadcasts.services.send_telegram_message", return_value=True)
    def test_send_broadcast_filters_by_balance_and_orders(self, send_message):
        product = Product.objects.create(name="VIP", price=Decimal("3.00"))
        buyer = TelegramUser.objects.create(telegram_id=7101, balance=Decimal("20.00"))
        low_balance_buyer = TelegramUser.objects.create(telegram_id=7102, balance=Decimal("2.00"))
        TelegramUser.objects.create(telegram_id=7103, balance=Decimal("30.00"))
        stock = StockItem.objects.create(product=product, secret_content="secret")
        Order.objects.create(user=buyer, product=product, stock_item=stock, price_paid=Decimal("3.00"))
        other_stock = StockItem.objects.create(product=product, secret_content="secret-2")
        Order.objects.create(
            user=low_balance_buyer,
            product=product,
            stock_item=other_stock,
            price_paid=Decimal("3.00"),
        )
        broadcast = Broadcast.objects.create(
            message="VIP offer",
            min_balance=Decimal("10.00"),
            has_orders=True,
            product_purchased=product,
        )

        send_broadcast(broadcast_id=broadcast.pk)

        send_message.assert_called_once_with(buyer.telegram_id, "VIP offer")

    @patch("broadcasts.services.send_telegram_message", return_value=True)
    def test_send_broadcast_filters_by_activity_window(self, send_message):
        cutoff = timezone.now() - timezone.timedelta(days=7)
        active = TelegramUser.objects.create(telegram_id=7201, last_active_at=timezone.now())
        TelegramUser.objects.create(telegram_id=7202, last_active_at=timezone.now() - timezone.timedelta(days=30))
        broadcast = Broadcast.objects.create(message="Welcome back", active_after=cutoff)

        send_broadcast(broadcast_id=broadcast.pk)

        send_message.assert_called_once_with(active.telegram_id, "Welcome back")

    @patch("broadcasts.admin.send_broadcast_task")
    def test_admin_action_queues_broadcasts(self, send_task):
        admin_user = get_user_model().objects.create_superuser("admin", "admin@example.com", "password")
        request = RequestFactory().post("/")
        request.user = admin_user
        broadcast = Broadcast.objects.create(message="Queued")
        model_admin = BroadcastAdmin(Broadcast, AdminSite())

        with patch.object(model_admin, "message_user"):
            model_admin.send_selected_broadcasts(request, Broadcast.objects.filter(pk=broadcast.pk))

        send_task.assert_called_once_with(broadcast.pk)
