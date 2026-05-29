from django.contrib import admin
from django.utils.html import format_html

from analytics.models import UserActivity


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "activity_type",
        "description_short",
        "created_at",
    )
    list_filter = ("activity_type", "created_at")
    search_fields = (
        "user__telegram_id",
        "user__username",
        "description",
    )
    readonly_fields = (
        "user",
        "activity_type",
        "description",
        "metadata",
        "ip_address",
        "user_agent",
        "created_at",
    )
    list_select_related = ("user",)
    date_hierarchy = "created_at"

    def description_short(self, obj):
        if len(obj.description) > 50:
            return format_html("<span title='{}'>{}...</span>", obj.description, obj.description[:50])
        return obj.description

    description_short.short_description = "Description"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
