from decimal import Decimal

from django.test import TestCase

from accounts.models import ReferralLedger, TelegramUser
from accounts.services import mark_referral_entries_processed, transfer_available_referral_earnings
from wallet.models import WalletTransaction


class ReferralSettlementTests(TestCase):
    def setUp(self):
        self.referrer = TelegramUser.objects.create(telegram_id=9001, balance=Decimal("0.00"))
        self.referee = TelegramUser.objects.create(telegram_id=9002, balance=Decimal("0.00"))

    def test_transfer_available_referral_earnings_credits_wallet_once(self):
        ReferralLedger.objects.create(
            referrer=self.referrer,
            referee=self.referee,
            commission_amount=Decimal("1.50"),
        )
        ReferralLedger.objects.create(
            referrer=self.referrer,
            referee=self.referee,
            commission_amount=Decimal("2.50"),
        )

        count, total = transfer_available_referral_earnings(referrer_id=self.referrer.pk)
        second_count, second_total = transfer_available_referral_earnings(referrer_id=self.referrer.pk)

        self.referrer.refresh_from_db()
        self.assertEqual(count, 2)
        self.assertEqual(total, Decimal("4.00"))
        self.assertEqual(second_count, 0)
        self.assertEqual(second_total, 0)
        self.assertEqual(self.referrer.balance, Decimal("4.00"))
        self.assertEqual(ReferralLedger.objects.filter(status=ReferralLedger.Status.TRANSFERRED).count(), 2)
        self.assertEqual(WalletTransaction.objects.filter(user=self.referrer).count(), 1)

    def test_mark_referral_entries_processed_only_updates_available_entries(self):
        available = ReferralLedger.objects.create(
            referrer=self.referrer,
            referee=self.referee,
            commission_amount=Decimal("1.50"),
        )
        transferred = ReferralLedger.objects.create(
            referrer=self.referrer,
            referee=self.referee,
            commission_amount=Decimal("2.50"),
            status=ReferralLedger.Status.TRANSFERRED,
        )

        count = mark_referral_entries_processed(
            entry_ids=[available.pk, transferred.pk],
            status=ReferralLedger.Status.WITHDRAWN,
        )

        available.refresh_from_db()
        transferred.refresh_from_db()
        self.assertEqual(count, 1)
        self.assertEqual(available.status, ReferralLedger.Status.WITHDRAWN)
        self.assertEqual(transferred.status, ReferralLedger.Status.TRANSFERRED)
