from django.contrib import admin

from audit.models import AdminAuditLog


@admin.register(AdminAuditLog)
class AdminAuditLogAdmin(admin.ModelAdmin):
    list_display = ("id", "action", "actor", "target_model", "target_id", "created_at")
    list_filter = ("action", "target_model", "created_at")
    search_fields = ("action", "target_model", "target_id", "message")
    readonly_fields = ("action", "actor", "target_model", "target_id", "message", "metadata", "created_at")
    list_select_related = ("actor",)
