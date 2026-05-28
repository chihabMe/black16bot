from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from accounts.models import TelegramUser
from bot.telegram_client import send_telegram_message
from broadcasts.models import Broadcast


def send_broadcast(*, broadcast_id: int) -> Broadcast:
    with transaction.atomic():
        broadcast = Broadcast.objects.select_for_update().get(pk=broadcast_id)
        if broadcast.status == Broadcast.Status.SENDING:
            return broadcast
        broadcast.status = Broadcast.Status.SENDING
        broadcast.save(update_fields=["status"])

    users = TelegramUser.objects.filter(is_blocked=False, notifications_enabled=True)
    if broadcast.target_language:
        users = users.filter(language=broadcast.target_language)

    sent = 0
    failed = 0
    for user in users.iterator():
        if send_telegram_message(user.telegram_id, broadcast.message):
            sent += 1
        else:
            failed += 1

    broadcast.sent_count = sent
    broadcast.failed_count = failed
    broadcast.sent_at = timezone.now()
    broadcast.status = Broadcast.Status.SENT if failed == 0 else Broadcast.Status.FAILED
    broadcast.save(update_fields=["sent_count", "failed_count", "sent_at", "status"])
    return broadcast


def recover_stuck_broadcasts(minutes: int = 10) -> int:
    """Reset broadcasts stuck in SENDING state for more than N minutes."""
    cutoff = timezone.now() - timedelta(minutes=minutes)
    count = Broadcast.objects.filter(
        status=Broadcast.Status.SENDING,
        created_at__lt=cutoff
    ).update(status=Broadcast.Status.DRAFT)
    return count
