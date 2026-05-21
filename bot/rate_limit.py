from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from bot.models import BotRateLimit


def is_rate_limited(user_id: int, action: str, *, limit: int = 12, window_seconds: int = 60) -> bool:
    now = timezone.now()
    with transaction.atomic():
        bucket, _ = BotRateLimit.objects.select_for_update().get_or_create(
            user_id=user_id,
            action=action,
            defaults={"window_start": now, "count": 0},
        )
        if now - bucket.window_start >= timedelta(seconds=window_seconds):
            bucket.window_start = now
            bucket.count = 1
            bucket.save(update_fields=["window_start", "count", "updated_at"])
            return False
        if bucket.count >= limit:
            return True
        bucket.count += 1
        bucket.save(update_fields=["count", "updated_at"])
        return False
