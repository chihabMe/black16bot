from decimal import Decimal
import secrets

from django.db import models


class TelegramUser(models.Model):
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=150, blank=True)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    language = models.CharField(max_length=16, default="en")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    referral_code = models.CharField(max_length=32, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        related_name="referrals",
        on_delete=models.SET_NULL,
    )
    is_blocked = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=True)
    joined_at = models.DateTimeField(auto_now_add=True)
    last_active_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-joined_at"]

    def __str__(self) -> str:
        label = self.username or self.first_name or str(self.telegram_id)
        return f"{label} ({self.telegram_id})"

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self.generate_referral_code()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_referral_code() -> str:
        return secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10]


class ReferralLedger(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        AVAILABLE = "available", "Available"
        TRANSFERRED = "transferred", "Transferred"
        WITHDRAWN = "withdrawn", "Withdrawn"
        REVERSED = "reversed", "Reversed"

    referrer = models.ForeignKey(TelegramUser, related_name="referral_earnings", on_delete=models.PROTECT)
    referee = models.ForeignKey(TelegramUser, related_name="referral_sources", on_delete=models.PROTECT)
    source_payment = models.ForeignKey(
        "payments.PaymentRequest",
        null=True,
        blank=True,
        related_name="referral_entries",
        on_delete=models.PROTECT,
    )
    commission_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    processed_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        related_name="processed_referral_entries",
        on_delete=models.SET_NULL,
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.referrer} earned {self.commission_amount} from {self.referee}"

# Create your models here.
