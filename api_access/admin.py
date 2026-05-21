from django.contrib import admin

from api_access.models import DeveloperApiKey


@admin.register(DeveloperApiKey)
class DeveloperApiKeyAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "key_prefix", "is_active", "total_orders", "total_spend", "created_at", "last_used_at")
    list_filter = ("is_active", "created_at", "last_used_at")
    search_fields = ("user__telegram_id", "user__username", "key_prefix", "webhook_url")
    readonly_fields = ("key_hash", "key_prefix", "created_at", "last_used_at")
    autocomplete_fields = ("user",)

# Register your models here.
