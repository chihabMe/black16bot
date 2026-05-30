from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone

from accounts.models import TelegramUser
from bot.telegram_client import send_telegram_message
from broadcasts.models import Broadcast
from orders.models import Order


def send_broadcast(*, broadcast_id: int) -> Broadcast:
    with transaction.atomic():
        broadcast = Broadcast.objects.select_for_update().get(pk=broadcast_id)
        if broadcast.status == Broadcast.Status.SENDING:
            return broadcast
        if broadcast.status == Broadcast.Status.SENT:
            return broadcast
        broadcast.status = Broadcast.Status.SENDING
        broadcast.save(update_fields=["status"])

    users = TelegramUser.objects.filter(is_blocked=False, notifications_enabled=True)
    if broadcast.target_language:
        users = users.filter(language=broadcast.target_language)
    if broadcast.min_balance is not None:
        users = users.filter(balance__gte=broadcast.min_balance)
    if broadcast.max_balance is not None:
        users = users.filter(balance__lte=broadcast.max_balance)
    if broadcast.joined_after:
        users = users.filter(joined_at__gte=broadcast.joined_after)
    if broadcast.joined_before:
        users = users.filter(joined_at__lte=broadcast.joined_before)
    if broadcast.active_after:
        users = users.filter(last_active_at__gte=broadcast.active_after)
    if broadcast.active_before:
        users = users.filter(last_active_at__lte=broadcast.active_before)
    if broadcast.has_orders is not None:
        order_exists = Order.objects.filter(user_id=OuterRef("pk"))
        users = users.annotate(has_matching_orders=Exists(order_exists)).filter(
            has_matching_orders=broadcast.has_orders
        )
    if broadcast.product_purchased_id:
        users = users.filter(orders__product_id=broadcast.product_purchased_id).distinct()

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
