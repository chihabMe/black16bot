from django.utils import timezone

from accounts.models import TelegramUser


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
