from django.db import models


class Broadcast(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    class TargetLanguage(models.TextChoices):
        ENGLISH = "en", "English"
        ARABIC = "ar", "Arabic"
        FRENCH = "fr", "French"
        SPANISH = "es", "Spanish"

    message = models.TextField()
    target_language = models.CharField(max_length=16, choices=TargetLanguage.choices, blank=True)
    min_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    max_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    joined_after = models.DateTimeField(null=True, blank=True)
    joined_before = models.DateTimeField(null=True, blank=True)
    active_after = models.DateTimeField(null=True, blank=True)
    active_before = models.DateTimeField(null=True, blank=True)
    has_orders = models.BooleanField(null=True, blank=True)
    product_purchased = models.ForeignKey(
        "catalog.Product",
        null=True,
        blank=True,
        related_name="targeted_broadcasts",
        on_delete=models.SET_NULL,
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        related_name="broadcasts",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Broadcast #{self.pk} ({self.status})"

# Create your models here.
