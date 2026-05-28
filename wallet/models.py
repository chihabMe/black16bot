from django.db import models


class WalletTransaction(models.Model):
    class Type(models.TextChoices):
        TOPUP = "topup", "Top-up"
        PURCHASE = "purchase", "Purchase"
        REFUND = "refund", "Refund"
        ADMIN_ADJUSTMENT = "admin_adjustment", "Admin adjustment"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        REVERSED = "reversed", "Reversed"

    user = models.ForeignKey("accounts.TelegramUser", related_name="wallet_transactions", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(max_length=32, choices=Type.choices, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED, db_index=True)
    related_order = models.ForeignKey(
        "orders.Order",
        null=True,
        blank=True,
        related_name="wallet_transactions",
        on_delete=models.PROTECT,
    )
    related_payment = models.ForeignKey(
        "payments.PaymentRequest",
        null=True,
        blank=True,
        related_name="wallet_transactions",
        on_delete=models.PROTECT,
    )
    created_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        related_name="wallet_transactions",
        on_delete=models.SET_NULL,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self) -> str:
        return f"{self.user} {self.amount} {self.transaction_type}"

# Create your models here.
