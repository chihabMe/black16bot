from django.contrib import admin, messages

from audit.services import log_admin_action
from broadcasts.models import Broadcast
from broadcasts.services import send_broadcast


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = ("id", "target_language", "status", "sent_count", "failed_count", "created_by", "created_at", "sent_at")
    list_filter = ("status", "target_language", "created_at", "sent_at")
    search_fields = ("message",)
    readonly_fields = ("sent_count", "failed_count", "created_at", "sent_at")
    autocomplete_fields = ("created_by",)
    actions = ("send_selected_broadcasts",)

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description="Send selected broadcasts")
    def send_selected_broadcasts(self, request, queryset):
        sent = 0
        for broadcast in queryset:
            send_broadcast(broadcast_id=broadcast.pk)
            log_admin_action(action="broadcast.send", actor=request.user, target=broadcast)
            sent += 1
        self.message_user(request, f"Processed {sent} broadcasts.", messages.SUCCESS)

# Register your models here.
