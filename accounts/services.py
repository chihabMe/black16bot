from django.utils import timezone
from django.db import transaction
from django.db.models import F, Sum

from accounts.models import ReferralLedger, TelegramUser
from wallet.models import WalletTransaction


def upsert_telegram_user(telegram_user, default_language: str = "en") -> TelegramUser:
    user, _ = TelegramUser.objects.update_or_create(
        telegram_id=telegram_user.id,
        defaults={
            "username": telegram_user.username or "",
            "first_name": telegram_user.first_name or "",
            "last_name": telegram_user.last_name or "",
            "last_active_at": timezone.now(),
        },
    )
    if not user.language:
        user.language = default_language
        user.save(update_fields=["language"])
    return user


def apply_referral_code(*, user: TelegramUser, referral_code: str) -> bool:
    if not referral_code or user.referred_by_id:
        return False
    referrer = TelegramUser.objects.filter(referral_code=referral_code).exclude(pk=user.pk).first()
    if referrer is None:
        return False
    user.referred_by = referrer
    user.save(update_fields=["referred_by"])
    return True


def transfer_available_referral_earnings(*, referrer_id: int, admin_user=None, note: str = "") -> tuple[int, object]:
    with transaction.atomic():
        referrer = TelegramUser.objects.select_for_update().get(pk=referrer_id)
        entries = ReferralLedger.objects.select_for_update().filter(
            referrer=referrer,
            status=ReferralLedger.Status.AVAILABLE,
        )
        aggregate = entries.aggregate(total=Sum("commission_amount"))
        total = aggregate["total"] or 0
        count = entries.count()
        if total <= 0 or count == 0:
            return 0, total

        TelegramUser.objects.filter(pk=referrer.pk).update(balance=F("balance") + total)
        entries.update(
            status=ReferralLedger.Status.TRANSFERRED,
            processed_by=admin_user,
            processed_at=timezone.now(),
            admin_note=note,
        )
        WalletTransaction.objects.create(
            user=referrer,
            amount=total,
            transaction_type=WalletTransaction.Type.ADMIN_ADJUSTMENT,
            status=WalletTransaction.Status.COMPLETED,
            created_by=admin_user,
            note=note or "Transferred referral commissions to wallet.",
        )
        return count, total


def mark_referral_entries_processed(*, entry_ids, status: str, admin_user=None, note: str = "") -> int:
    allowed_statuses = {ReferralLedger.Status.WITHDRAWN, ReferralLedger.Status.REVERSED}
    if status not in allowed_statuses:
        raise ValueError("Unsupported referral processing status.")
    with transaction.atomic():
        return ReferralLedger.objects.select_for_update().filter(
            pk__in=entry_ids,
            status=ReferralLedger.Status.AVAILABLE,
        ).update(
            status=status,
            processed_by=admin_user,
            processed_at=timezone.now(),
            admin_note=note,
        )
