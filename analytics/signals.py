import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import TelegramUser
from analytics.models import UserActivity
from orders.models import Order
from payments.models import PaymentRequest
from support.models import SupportTicket

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Order)
def track_purchase(sender, instance, created, **kwargs):
    """Track when a user makes a purchase."""
    if created:
        try:
            UserActivity.objects.create(
                user=instance.user,
                activity_type=UserActivity.ActivityType.PURCHASE,
                description=f"Purchased {instance.product.name} (Order #{instance.id})",
                metadata={
                    "order_id": instance.id,
                    "product_id": instance.product.id,
                    "product_name": instance.product.name,
                    "amount": str(instance.price_paid),
                    "quantity": instance.quantity,
                },
            )
        except Exception as e:
            logger.error(f"Failed to track purchase activity: {e}")


@receiver(post_save, sender=PaymentRequest)
def track_topup(sender, instance, created, **kwargs):
    """Track when a user tops up their wallet."""
    if instance.status == PaymentRequest.Status.APPROVED and not created:
        # Only track on approval, not on creation
        try:
            UserActivity.objects.create(
                user=instance.user,
                activity_type=UserActivity.ActivityType.TOPUP,
                description=f"Topped up {instance.amount} USDT via {instance.get_method_display()}",
                metadata={
                    "payment_id": instance.id,
                    "amount": str(instance.amount),
                    "method": instance.method,
                    "payable_amount": str(instance.payable_amount) if instance.payable_amount else None,
                },
            )
        except Exception as e:
            logger.error(f"Failed to track topup activity: {e}")


@receiver(post_save, sender=SupportTicket)
def track_support_ticket(sender, instance, created, **kwargs):
    """Track when a user creates a support ticket."""
    if created:
        try:
            UserActivity.objects.create(
                user=instance.user,
                activity_type=UserActivity.ActivityType.SUPPORT_TICKET,
                description=f"Created support ticket #{instance.id}",
                metadata={
                    "ticket_id": instance.id,
                    "message_preview": instance.message[:200] if instance.message else "",
                },
            )
        except Exception as e:
            logger.error(f"Failed to track support ticket activity: {e}")


@receiver(post_save, sender=TelegramUser)
def track_referral_signup(sender, instance, created, **kwargs):
    """Track when a user signs up via referral."""
    if created and instance.referred_by:
        try:
            UserActivity.objects.create(
                user=instance.referred_by,
                activity_type=UserActivity.ActivityType.REFERRAL_SIGNUP,
                description=f"Referred user {instance.username or instance.telegram_id}",
                metadata={
                    "referred_user_id": instance.id,
                    "referred_telegram_id": instance.telegram_id,
                    "referred_username": instance.username,
                },
            )
        except Exception as e:
            logger.error(f"Failed to track referral signup activity: {e}")
