from django.contrib import admin

from api_access.models import ApiUsageLog, DeveloperApiKey


@admin.register(DeveloperApiKey)
class DeveloperApiKeyAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "key_prefix",
        "is_active",
        "can_create_orders",
        "max_order_quantity",
        "daily_spend_limit",
        "orders_per_minute",
        "total_orders",
        "total_spend",
        "created_at",
        "last_used_at",
    )
    list_filter = ("is_active", "can_create_orders", "created_at", "last_used_at")
    search_fields = ("user__telegram_id", "user__username", "key_prefix", "webhook_url")
    readonly_fields = ("key_hash", "key_prefix", "created_at", "last_used_at")
    autocomplete_fields = ("user",)
    list_select_related = ("user",)


@admin.register(ApiUsageLog)
class ApiUsageLogAdmin(admin.ModelAdmin):
    list_display = ("id", "api_key", "endpoint", "method", "status_code", "cost", "error_code", "created_at")
    list_filter = ("endpoint", "method", "status_code", "created_at")
    search_fields = ("api_key__key_prefix", "api_key__user__telegram_id", "error_code")
    readonly_fields = ("api_key", "endpoint", "method", "status_code", "cost", "error_code", "request_ip", "created_at")
    list_select_related = ("api_key", "api_key__user")

    def has_add_permission(self, request):
        return False
