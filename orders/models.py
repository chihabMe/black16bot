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
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'status']),
        ]

    def __str__(self) -> str:
        return f"Order #{self.pk} - {self.user}"


class OrderItem(models.Model):
    class Status(models.TextChoices):
        DELIVERED = "delivered", "Delivered"
        REFUNDED = "refunded", "Refunded"
        REPLACED = "replaced", "Replaced"

    order = models.ForeignKey(Order, related_name="items", on_delete=models.CASCADE)
    stock_item = models.OneToOneField("catalog.StockItem", related_name="order_item", on_delete=models.PROTECT)
    secret_snapshot = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DELIVERED, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    replaced_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at", "pk"]

    def __str__(self) -> str:
        return f"Order #{self.order_id} item #{self.pk}"
