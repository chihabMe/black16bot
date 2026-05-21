from django.contrib import admin

from wallet.models import WalletTransaction


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "amount", "transaction_type", "status", "created_by", "created_at")
    list_filter = ("transaction_type", "status", "created_at")
    search_fields = ("user__telegram_id", "user__username", "note")
    readonly_fields = ("created_at",)
    autocomplete_fields = ("user", "related_order", "related_payment", "created_by")

# Register your models here.
