from django.contrib import admin

from support.models import SupportTicket


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "closed_at")
    list_filter = ("status", "created_at", "closed_at")
    search_fields = ("user__telegram_id", "user__username", "message", "admin_note")
    readonly_fields = ("created_at", "closed_at")
    autocomplete_fields = ("user",)

# Register your models here.
