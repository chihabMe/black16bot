from decimal import Decimal

from django.test import TestCase

from accounts.models import TelegramUser
from wallet.models import WalletTransaction


class WalletTransactionTests(TestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(
            telegram_id=123456,
            username="testuser",
            balance=Decimal("100.00"),
        )

    def test_create_topup_transaction(self):
        tx = WalletTransaction.objects.create(
            user=self.user,
            amount=Decimal("50.00"),
            transaction_type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.COMPLETED,
        )
        self.assertEqual(tx.amount, Decimal("50.00"))
        self.assertEqual(tx.transaction_type, WalletTransaction.Type.TOPUP)
        self.assertEqual(tx.status, WalletTransaction.Status.COMPLETED)

    def test_create_purchase_transaction(self):
        tx = WalletTransaction.objects.create(
            user=self.user,
            amount=Decimal("-25.00"),
            transaction_type=WalletTransaction.Type.PURCHASE,
            status=WalletTransaction.Status.COMPLETED,
        )
        self.assertEqual(tx.amount, Decimal("-25.00"))
        self.assertEqual(tx.transaction_type, WalletTransaction.Type.PURCHASE)

    def test_transaction_types_are_correct(self):
        types = [choice[0] for choice in WalletTransaction.Type.choices]
        self.assertIn("topup", types)
        self.assertIn("purchase", types)
        self.assertIn("refund", types)
        self.assertIn("admin_adjustment", types)

    def test_transaction_statuses_are_correct(self):
        statuses = [choice[0] for choice in WalletTransaction.Status.choices]
        self.assertIn("pending", statuses)
        self.assertIn("completed", statuses)
        self.assertIn("failed", statuses)
        self.assertIn("reversed", statuses)
