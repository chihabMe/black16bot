from django.contrib import admin

from accounts.models import ReferralLedger, TelegramUser


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = (
        "telegram_id",
        "username",
        "first_name",
        "language",
        "balance",
        "referral_code",
        "referred_by",
        "is_blocked",
        "joined_at",
        "last_active_at",
    )
    list_filter = ("language", "is_blocked", "notifications_enabled", "joined_at")
    search_fields = ("telegram_id", "username", "first_name", "last_name", "referral_code")
    readonly_fields = ("joined_at", "last_active_at")
    autocomplete_fields = ("referred_by",)
    ordering = ("-joined_at",)


@admin.register(ReferralLedger)
class ReferralLedgerAdmin(admin.ModelAdmin):
    list_display = ("id", "referrer", "referee", "commission_amount", "status", "source_payment", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("referrer__telegram_id", "referee__telegram_id", "referrer__username", "referee__username")
    autocomplete_fields = ("referrer", "referee", "source_payment")
    readonly_fields = ("created_at",)

# Register your models here.
