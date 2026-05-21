from django.contrib import admin, messages

from audit.services import log_admin_action
from orders.models import Order
from orders.services import OutOfStock, PurchaseError, refund_order, replace_order_stock


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "product", "price_paid", "status", "created_at", "refunded_at")
    list_filter = ("status", "product", "created_at", "refunded_at")
    search_fields = ("id", "user__telegram_id", "user__username", "product__name")
    readonly_fields = ("created_at", "refunded_at", "replaced_at")
    autocomplete_fields = ("user", "product", "stock_item")
    actions = ("refund_selected_orders", "replace_selected_orders")

    @admin.action(description="Refund selected orders")
    def refund_selected_orders(self, request, queryset):
        refunded = 0
        for order in queryset:
            if order.status == Order.Status.REFUNDED:
                continue
            refund_order(order_id=order.pk, admin_user=request.user, note="Refunded from Django Admin")
            log_admin_action(action="order.refund", actor=request.user, target=order)
            refunded += 1
        self.message_user(request, f"Refunded {refunded} orders.", messages.SUCCESS)

    @admin.action(description="Replace selected orders with fresh stock")
    def replace_selected_orders(self, request, queryset):
        replaced = 0
        for order in queryset:
            try:
                replace_order_stock(
                    order_id=order.pk,
                    admin_user=request.user,
                    note="Replaced from Django Admin",
                )
                log_admin_action(action="order.replace", actor=request.user, target=order)
                replaced += 1
            except (PurchaseError, OutOfStock) as exc:
                self.message_user(request, f"Order #{order.pk}: {exc}", messages.WARNING)
        self.message_user(request, f"Replaced {replaced} orders.", messages.SUCCESS)

# Register your models here.
