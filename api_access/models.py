import hashlib
import secrets

from django.conf import settings
from django.db import models


class DeveloperApiKey(models.Model):
    user = models.ForeignKey("accounts.TelegramUser", related_name="api_keys", on_delete=models.PROTECT)
    key_hash = models.CharField(max_length=128, unique=True)
    key_prefix = models.CharField(max_length=16, db_index=True)
    webhook_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    can_create_orders = models.BooleanField(default=True)
    max_order_quantity = models.PositiveIntegerField(default=10)
    daily_spend_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        help_text="Set to 0 to disable the daily spend cap.",
    )
    orders_per_minute = models.PositiveIntegerField(default=30)
    total_orders = models.PositiveIntegerField(default=0)
    total_spend = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} - {self.key_prefix}"

    @staticmethod
    def hash_key(raw_key: str) -> str:
        peppered = f"{settings.API_KEY_PEPPER}:{raw_key}".encode()
        return hashlib.sha256(peppered).hexdigest()

    @classmethod
    def create_for_user(cls, user):
        raw_key = f"b16_{secrets.token_urlsafe(32)}"
        instance = cls.objects.create(
            user=user,
            key_hash=cls.hash_key(raw_key),
            key_prefix=raw_key[:12],
        )
        return raw_key, instance


class ApiUsageLog(models.Model):
    api_key = models.ForeignKey(DeveloperApiKey, related_name="usage_logs", on_delete=models.CASCADE)
    endpoint = models.CharField(max_length=80, db_index=True)
    method = models.CharField(max_length=10)
    status_code = models.PositiveIntegerField()
    cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    error_code = models.CharField(max_length=80, blank=True)
    request_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["api_key", "endpoint", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.api_key.key_prefix} {self.endpoint} {self.status_code}"
