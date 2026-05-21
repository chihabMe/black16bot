from django.db import models
from django.db.models import Count, Q


class ProductQuerySet(models.QuerySet):
    def with_stock_counts(self):
        return self.annotate(
            available_stock=Count(
                "stock_items",
                filter=Q(stock_items__status=StockItem.Status.AVAILABLE),
            )
        )


class Product(models.Model):
    class ProductType(models.TextChoices):
        DIGITAL = "digital", "Digital product"
        TELEGRAM_ACCOUNT = "telegram_account", "Telegram account"

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    note_md = models.TextField(blank=True)
    category = models.CharField(max_length=120, blank=True)
    product_type = models.CharField(max_length=32, choices=ProductType.choices, default=ProductType.DIGITAL)
    country_code = models.CharField(max_length=8, blank=True)
    country_name = models.CharField(max_length=80, blank=True)
    warranty_note = models.TextField(blank=True)
    allow_infinite_stock = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ProductQuerySet.as_manager()

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    @property
    def available_stock_count(self) -> int:
        if self.allow_infinite_stock:
            return 999999
        if hasattr(self, "available_stock"):
            return self.available_stock
        return self.stock_items.filter(status=StockItem.Status.AVAILABLE).count()


class StockItem(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        RESERVED = "reserved", "Reserved"
        SOLD = "sold", "Sold"
        REFUNDED = "refunded", "Refunded"
        REPLACED = "replaced", "Replaced"
        DISABLED = "disabled", "Disabled"

    product = models.ForeignKey(Product, related_name="stock_items", on_delete=models.PROTECT)
    secret_content = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AVAILABLE, db_index=True)
    sold_to = models.ForeignKey(
        "accounts.TelegramUser",
        null=True,
        blank=True,
        related_name="stock_items",
        on_delete=models.PROTECT,
    )
    added_by = models.ForeignKey(
        "auth.User",
        null=True,
        blank=True,
        related_name="added_stock_items",
        on_delete=models.SET_NULL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reserved_at = models.DateTimeField(null=True, blank=True)
    sold_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["product", "created_at"]
        indexes = [
            models.Index(fields=["product", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.product} - {self.status} #{self.pk}"

# Create your models here.
