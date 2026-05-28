from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounts.models import TelegramUser
from support.models import SupportTicket
from support.services import create_support_ticket


class SupportTicketTests(TestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id=123456,
            username="testuser",
            balance=Decimal("10.00"),
        )

    def test_create_support_ticket(self):
        ticket = create_support_ticket(
            user_id=self.user.pk,
            message="I need help with my order",
        )
        self.assertEqual(ticket.user, self.user)
        self.assertEqual(ticket.message, "I need help with my order")
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)

    @patch("support.services.notify_admins")
    def test_ticket_creation_sends_admin_notification(self, mock_notify):
        create_support_ticket(user_id=self.user.pk, message="Test message")
        mock_notify.assert_called_once()
        call_args = mock_notify.call_args[0][0]
        self.assertIn("New support ticket", call_args)
        self.assertIn("123456", call_args)

    def test_ticket_status_transitions(self):
        ticket = create_support_ticket(user_id=self.user.pk, message="Test")
        self.assertEqual(ticket.status, SupportTicket.Status.OPEN)
        ticket.status = SupportTicket.Status.CLOSED
        ticket.save()
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, SupportTicket.Status.CLOSED)
