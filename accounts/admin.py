from django.contrib import admin
from django.contrib import messages

from accounts.models import ReferralLedger, TelegramUser
from accounts.services import mark_referral_entries_processed, transfer_available_referral_earnings


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
    list_display = (
        "id",
        "referrer",
        "referee",
        "commission_amount",
        "status",
        "source_payment",
        "processed_by",
        "processed_at",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("referrer__telegram_id", "referee__telegram_id", "referrer__username", "referee__username")
    autocomplete_fields = ("referrer", "referee", "source_payment")
    readonly_fields = ("created_at", "processed_by", "processed_at")
    actions = ("transfer_selected_referrers_to_wallet", "mark_selected_withdrawn", "reverse_selected")

    @admin.action(description="Transfer available commissions for selected referrers to wallet")
    def transfer_selected_referrers_to_wallet(self, request, queryset):
        referrer_ids = queryset.values_list("referrer_id", flat=True).distinct()
        total_count = 0
        total_amount = 0
        for referrer_id in referrer_ids:
            count, amount = transfer_available_referral_earnings(
                referrer_id=referrer_id,
                admin_user=request.user,
                note="Admin transferred referral commissions.",
            )
            total_count += count
            total_amount += amount
        self.message_user(
            request,
            f"Transferred {total_count} referral entries totaling {total_amount} USDT.",
            messages.SUCCESS,
        )

    @admin.action(description="Mark selected available commissions as externally withdrawn")
    def mark_selected_withdrawn(self, request, queryset):
        count = mark_referral_entries_processed(
            entry_ids=queryset.values_list("pk", flat=True),
            status=ReferralLedger.Status.WITHDRAWN,
            admin_user=request.user,
            note="Admin marked referral commission as externally withdrawn.",
        )
        self.message_user(request, f"Marked {count} referral entries as withdrawn.", messages.SUCCESS)

    @admin.action(description="Reverse selected available commissions")
    def reverse_selected(self, request, queryset):
        count = mark_referral_entries_processed(
            entry_ids=queryset.values_list("pk", flat=True),
            status=ReferralLedger.Status.REVERSED,
            admin_user=request.user,
            note="Admin reversed referral commission.",
        )
        self.message_user(request, f"Reversed {count} referral entries.", messages.SUCCESS)

# Register your models here.
