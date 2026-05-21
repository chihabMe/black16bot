from unittest.mock import patch

from django.test import TestCase

from accounts.models import TelegramUser
from broadcasts.models import Broadcast
from broadcasts.services import send_broadcast


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
