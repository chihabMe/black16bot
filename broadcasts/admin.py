from django.contrib import admin, messages

from audit.services import log_admin_action
from broadcasts.models import Broadcast
from broadcasts.tasks import send_broadcast_task


@admin.register(Broadcast)
class BroadcastAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "target_summary",
        "status",
        "sent_count",
        "failed_count",
        "created_by",
        "created_at",
        "sent_at",
    )
    list_filter = ("status", "target_language", "has_orders", "product_purchased", "created_at", "sent_at")
    search_fields = ("message",)
    readonly_fields = ("sent_count", "failed_count", "created_at", "sent_at")
    autocomplete_fields = ("created_by",)
    actions = ("send_selected_broadcasts",)
    fieldsets = (
        (None, {"fields": ("message", "status")}),
        ("Targeting", {
            "fields": (
                "target_language",
                "min_balance",
                "max_balance",
                "joined_after",
                "joined_before",
                "active_after",
                "active_before",
                "has_orders",
                "product_purchased",
            )
        }),
        ("Delivery", {"fields": ("sent_count", "failed_count", "sent_at", "created_by", "created_at")}),
    )

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.display(description="Target")
    def target_summary(self, obj):
        parts = []
        if obj.target_language:
            parts.append(f"lang={obj.target_language}")
        if obj.min_balance is not None:
            parts.append(f"min={obj.min_balance}")
        if obj.max_balance is not None:
            parts.append(f"max={obj.max_balance}")
        if obj.has_orders is not None:
            parts.append("buyers" if obj.has_orders else "no orders")
        if obj.product_purchased_id:
            parts.append(f"bought {obj.product_purchased}")
        return ", ".join(parts) or "All notification-enabled users"

    @admin.action(description="Queue selected broadcasts for sending")
    def send_selected_broadcasts(self, request, queryset):
        queued = 0
        for broadcast in queryset.filter(status__in=[Broadcast.Status.DRAFT, Broadcast.Status.FAILED]):
            send_broadcast_task(broadcast.pk)
            log_admin_action(action="broadcast.queue", actor=request.user, target=broadcast)
            queued += 1
        self.message_user(request, f"Queued {queued} broadcasts for sending.", messages.SUCCESS)

# Register your models here.
