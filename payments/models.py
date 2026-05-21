from django.db import models


class PaymentRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"
        EXPIRED = "expired", "Expired"

    class Method(models.TextChoices):
        BINANCE_DEPOSIT = "binance_deposit", "Binance Deposit"
        BINANCE_PAY = "binance_pay", "Binance Pay"
        BYBIT_PAY = "bybit_pay", "Bybit Pay"
        CRYPTOBOT = "cryptobot", "CryptoBot"
        USDT_BEP20 = "usdt_bep20", "USDT BEP-20"
        USDT_TRC20 = "usdt_trc20", "USDT TRC-20"
        TON = "ton", "TON"
        TRON = "tron", "TRON"
        OTHER = "other", "Other"

    user = models.ForeignKey("accounts.TelegramUser", related_name="payment_requests", on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=32, choices=Method.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    proof_text = models.TextField(blank=True)
    proof_file_id = models.CharField(max_length=255, blank=True)
    admin_note = models.TextField(blank=True)
    approved_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        related_name="approved_payment_requests",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} {self.amount} {self.method} ({self.status})"


class VerifiedDeposit(models.Model):
    class Provider(models.TextChoices):
        BINANCE = "binance", "Binance"

    user = models.ForeignKey("accounts.TelegramUser", related_name="verified_deposits", on_delete=models.PROTECT)
    payment_request = models.OneToOneField(
        PaymentRequest,
        related_name="verified_deposit",
        on_delete=models.PROTECT,
    )
    provider = models.CharField(max_length=32, choices=Provider.choices, default=Provider.BINANCE)
    txid = models.CharField(max_length=255, unique=True)
    coin = models.CharField(max_length=20)
    network = models.CharField(max_length=40, blank=True)
    amount = models.DecimalField(max_digits=18, decimal_places=8)
    raw_payload = models.JSONField(default=dict)
    credited_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-credited_at"]

    def __str__(self) -> str:
        return f"{self.provider} {self.coin} {self.amount} {self.txid[:12]}"

# Create your models here.
