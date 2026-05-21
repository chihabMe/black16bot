from decimal import Decimal
from unittest.mock import patch

from django.test import TransactionTestCase, override_settings

from accounts.models import ReferralLedger, TelegramUser
from payments.binance import BinanceDepositError, verify_binance_deposit
from payments.models import PaymentRequest
from payments.models import VerifiedDeposit
from payments.services import (
    PaymentRequestError,
    approve_payment_request,
    cancel_payment_request,
    create_payment_request,
    expire_pending_payment_requests,
    reject_payment_request,
)
from wallet.models import WalletTransaction


@override_settings(TELEGRAM_BOT_TOKEN="")
class PaymentRequestServiceTests(TransactionTestCase):
    def setUp(self):
        self.user = TelegramUser.objects.create(telegram_id=2001, balance=Decimal("0.00"))

    def test_approve_payment_request_credits_balance_once(self):
        payment = PaymentRequest.objects.create(
            user=self.user,
            amount=Decimal("12.00"),
            method=PaymentRequest.Method.CRYPTOBOT,
        )

        approve_payment_request(payment_id=payment.pk)
        approve_payment_request(payment_id=payment.pk)

        self.user.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("12.00"))
        self.assertEqual(payment.status, PaymentRequest.Status.APPROVED)
        self.assertEqual(WalletTransaction.objects.filter(related_payment=payment).count(), 1)

    def test_reject_payment_request_does_not_credit_balance(self):
        payment = PaymentRequest.objects.create(
            user=self.user,
            amount=Decimal("12.00"),
            method=PaymentRequest.Method.CRYPTOBOT,
        )

        reject_payment_request(payment_id=payment.pk)

        self.user.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("0.00"))
        self.assertEqual(payment.status, PaymentRequest.Status.REJECTED)

    def test_cancel_payment_request_only_changes_pending_payment(self):
        payment = PaymentRequest.objects.create(
            user=self.user,
            amount=Decimal("12.00"),
            method=PaymentRequest.Method.CRYPTOBOT,
        )

        cancel_payment_request(payment_id=payment.pk, user_id=self.user.pk)

        payment.refresh_from_db()
        self.assertEqual(payment.status, PaymentRequest.Status.CANCELLED)
        self.assertIsNotNone(payment.cancelled_at)

    def test_approve_payment_request_creates_referral_commission(self):
        referrer = TelegramUser.objects.create(telegram_id=2002, balance=Decimal("0.00"))
        self.user.referred_by = referrer
        self.user.save(update_fields=["referred_by"])
        payment = PaymentRequest.objects.create(
            user=self.user,
            amount=Decimal("20.00"),
            method=PaymentRequest.Method.CRYPTOBOT,
        )

        approve_payment_request(payment_id=payment.pk)

        entry = ReferralLedger.objects.get(source_payment=payment)
        self.assertEqual(entry.referrer, referrer)
        self.assertEqual(entry.referee, self.user)
        self.assertEqual(entry.commission_amount, Decimal("1.00"))

    def test_create_payment_request_rejects_non_positive_amount(self):
        with self.assertRaises(PaymentRequestError):
            create_payment_request(
                user_id=self.user.pk,
                amount=Decimal("0.00"),
                method=PaymentRequest.Method.CRYPTOBOT,
            )

    def test_create_payment_request_rejects_unsupported_method(self):
        with self.assertRaises(PaymentRequestError):
            create_payment_request(
                user_id=self.user.pk,
                amount=Decimal("10.00"),
                method="cash",
            )

    @patch("payments.binance.notify_admins", return_value=1)
    @patch("payments.binance.send_telegram_message", return_value=True)
    @patch("payments.binance.fetch_binance_deposit_by_txid")
    def test_verify_binance_deposit_credits_user_once(self, fetch_deposit, send_message, notify_admins):
        fetch_deposit.return_value = {
            "txId": "tx123",
            "coin": "USDT",
            "network": "BSC",
            "amount": "15.00000000",
            "status": 1,
        }

        verified = verify_binance_deposit(
            user_id=self.user.pk,
            amount=Decimal("10.00"),
            txid="tx123",
            network="BSC",
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.balance, Decimal("15.00"))
        self.assertEqual(verified.txid, "tx123")
        self.assertEqual(verified.payment_request.amount, Decimal("15.00"))
        self.assertEqual(verified.payment_request.status, PaymentRequest.Status.APPROVED)
        self.assertEqual(VerifiedDeposit.objects.count(), 1)

        with self.assertRaises(BinanceDepositError):
            verify_binance_deposit(
                user_id=self.user.pk,
                amount=Decimal("10.00"),
                txid="tx123",
                network="BSC",
            )

    def test_expire_pending_payment_requests_marks_old_requests(self):
        from django.utils import timezone

        old_payment = PaymentRequest.objects.create(
            user=self.user,
            amount=Decimal("5.00"),
            method=PaymentRequest.Method.CRYPTOBOT,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        fresh_payment = PaymentRequest.objects.create(
            user=self.user,
            amount=Decimal("5.00"),
            method=PaymentRequest.Method.CRYPTOBOT,
            expires_at=timezone.now() + timezone.timedelta(minutes=1),
        )

        count = expire_pending_payment_requests()

        old_payment.refresh_from_db()
        fresh_payment.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertEqual(old_payment.status, PaymentRequest.Status.EXPIRED)
        self.assertEqual(fresh_payment.status, PaymentRequest.Status.PENDING)

# Create your tests here.
