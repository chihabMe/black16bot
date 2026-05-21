from django.db import models


class Order(models.Model):
    class Status(models.TextChoices):
        COMPLETED = "completed", "Completed"
        REFUNDED = "refunded", "Refunded"
        REPLACED = "replaced", "Replaced"
        CANCELLED = "cancelled", "Cancelled"

    user = models.ForeignKey("accounts.TelegramUser", related_name="orders", on_delete=models.PROTECT)
    product = models.ForeignKey("catalog.Product", related_name="orders", on_delete=models.PROTECT)
    stock_item = models.OneToOneField(
        "catalog.StockItem",
        related_name="order",
        on_delete=models.PROTECT,
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_paid = models.DecimalField(max_digits=12, decimal_places=2)
    delivered_payload = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.COMPLETED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    replaced_at = models.DateTimeField(null=True, blank=True)
    admin_note = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.pk} - {self.user}"

# Create your models here.
