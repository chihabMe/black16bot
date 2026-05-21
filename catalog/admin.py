from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html

from audit.services import log_admin_action
from catalog.forms import BulkStockUploadForm
from catalog.models import Product, StockItem
from catalog.services import bulk_create_stock


class StockItemInline(admin.TabularInline):
    model = StockItem
    extra = 0
    fields = ("status", "secret_preview", "sold_to", "sold_at")
    readonly_fields = ("secret_preview", "sold_to", "sold_at")
    can_delete = False
    show_change_link = True

    def secret_preview(self, obj):
        if not obj.pk:
            return ""
        return f"{obj.secret_content[:24]}..."


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "product_type",
        "country_code",
        "category",
        "price",
        "is_active",
        "stock_count",
        "bulk_stock_link",
        "sort_order",
        "updated_at",
    )
    list_filter = ("is_active", "product_type", "country_code", "category", "created_at")
    search_fields = ("name", "description", "note_md", "category", "country_name", "country_code")
    list_editable = ("price", "is_active", "sort_order")
    inlines = (StockItemInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).with_stock_counts()

    @admin.display(description="Available stock")
    def stock_count(self, obj):
        return obj.available_stock_count

    @admin.display(description="Bulk stock")
    def bulk_stock_link(self, obj):
        url = reverse("admin:catalog_product_bulk_stock", args=[obj.pk])
        return format_html('<a class="button" href="{}">Upload stock</a>', url)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<int:product_id>/bulk-stock/",
                staff_member_required(self.admin_site.admin_view(self.bulk_stock_view)),
                name="catalog_product_bulk_stock",
            )
        ]
        return custom_urls + urls

    def bulk_stock_view(self, request, product_id):
        product = get_object_or_404(Product, pk=product_id)
        if request.method == "POST":
            form = BulkStockUploadForm(request.POST)
            if form.is_valid():
                count = bulk_create_stock(
                    product=product,
                    raw_lines=form.cleaned_data["stock_lines"],
                    added_by=request.user,
                )
                log_admin_action(
                    action="stock.bulk_upload",
                    actor=request.user,
                    target=product,
                    message=f"Uploaded {count} stock items",
                    metadata={"count": count},
                )
                self.message_user(request, f"Added {count} stock items to {product.name}.")
                return redirect("admin:catalog_product_change", product.pk)
        else:
            form = BulkStockUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "opts": self.model._meta,
            "product": product,
            "form": form,
            "title": f"Bulk upload stock for {product.name}",
        }
        return TemplateResponse(request, "admin/catalog/bulk_stock_upload.html", context)


@admin.register(StockItem)
class StockItemAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "status", "secret_preview", "sold_to", "order_link", "created_at", "sold_at")
    list_filter = ("status", "product", "created_at", "sold_at")
    search_fields = ("product__name", "sold_to__telegram_id", "sold_to__username", "secret_content")
    readonly_fields = ("created_at", "reserved_at", "sold_at", "secret_warning")
    autocomplete_fields = ("product", "sold_to", "added_by")
    actions = ("disable_stock", "mark_available")

    @admin.display(description="Secret")
    def secret_preview(self, obj):
        if obj.status == StockItem.Status.SOLD:
            return format_html("<span title='Sold secret hidden'>sold item</span>")
        return f"{obj.secret_content[:32]}..."

    def secret_warning(self, obj):
        return "Secret content is delivered to buyers. Be careful when editing sold stock."

    @admin.display(description="Order")
    def order_link(self, obj):
        order = getattr(obj, "order", None)
        return f"#{order.pk}" if order else "-"

    @admin.action(description="Disable selected stock")
    def disable_stock(self, request, queryset):
        count = queryset.exclude(status=StockItem.Status.SOLD).update(status=StockItem.Status.DISABLED)
        log_admin_action(
            action="stock.disable",
            actor=request.user,
            message=f"Disabled {count} stock items",
            metadata={"count": count},
        )
        self.message_user(request, f"Disabled {count} stock items.")

    @admin.action(description="Mark selected disabled stock as available")
    def mark_available(self, request, queryset):
        count = queryset.filter(status=StockItem.Status.DISABLED).update(status=StockItem.Status.AVAILABLE)
        log_admin_action(
            action="stock.mark_available",
            actor=request.user,
            message=f"Marked {count} stock items available",
            metadata={"count": count},
        )
        self.message_user(request, f"Marked {count} stock items as available.")

# Register your models here.
