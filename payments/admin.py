from django.contrib import admin, messages

from payments.binance import BinanceDepositError
from payments.chain import ChainDepositError
from payments.models import PaymentRequest, VerifiedDeposit
from payments.methods import enabled_payment_method_choices
from payments.services import PaymentApprovalError, approve_payment_request, reject_payment_request
from payments.verification import verify_pending_payment


@admin.register(PaymentRequest)
class PaymentRequestAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "amount",
        "requested_amount",
        "payable_amount",
        "method",
        "status",
        "proof_preview",
        "created_at",
        "approved_at",
        "rejected_at",
    )
    list_filter = ("status", "method", "created_at", "approved_at")
    search_fields = ("user__telegram_id", "user__username", "proof_text", "admin_note")
    readonly_fields = ("created_at", "approved_at", "rejected_at", "cancelled_at")
    autocomplete_fields = ("user", "approved_by")
    list_select_related = ("user", "approved_by")
    actions = ("verify_selected", "approve_selected", "reject_selected")

    @admin.display(description="Proof / order ID")
    def proof_preview(self, obj):
        if not obj.proof_text:
            return "-"
        return obj.proof_text[:32] + ("..." if len(obj.proof_text) > 32 else "")

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "method":
            kwargs["choices"] = enabled_payment_method_choices()
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    @admin.action(description="Verify selected pending payment requests")
    def verify_selected(self, request, queryset):
        checked = 0
        verified = 0
        for payment in queryset.filter(status=PaymentRequest.Status.PENDING).exclude(proof_text=""):
            checked += 1
            try:
                if verify_pending_payment(payment):
                    verified += 1
            except (BinanceDepositError, ChainDepositError) as exc:
                self.message_user(request, f"Payment #{payment.pk}: {exc}", messages.WARNING)
        self.message_user(request, f"Verified {verified} of {checked} checked payment requests.", messages.SUCCESS)

    @admin.action(description="Approve selected payment requests")
    def approve_selected(self, request, queryset):
        approved = 0
        for payment in queryset:
            try:
                approve_payment_request(
                    payment_id=payment.pk,
                    admin_user=request.user,
                    note="Approved from Django Admin",
                )
                approved += 1
            except PaymentApprovalError as exc:
                self.message_user(request, f"Payment #{payment.pk}: {exc}", messages.WARNING)
        self.message_user(request, f"Approved {approved} payment requests.", messages.SUCCESS)

    @admin.action(description="Reject selected payment requests")
    def reject_selected(self, request, queryset):
        rejected = 0
        for payment in queryset:
            try:
                reject_payment_request(
                    payment_id=payment.pk,
                    admin_user=request.user,
                    note="Rejected from Django Admin",
                )
                rejected += 1
            except PaymentApprovalError as exc:
                self.message_user(request, f"Payment #{payment.pk}: {exc}", messages.WARNING)
        self.message_user(request, f"Rejected {rejected} payment requests.", messages.SUCCESS)


@admin.register(VerifiedDeposit)
class VerifiedDepositAdmin(admin.ModelAdmin):
    list_display = ("id", "provider", "user", "coin", "network", "amount", "txid", "credited_at")
    list_filter = ("provider", "coin", "network", "credited_at")
    search_fields = ("txid", "user__telegram_id", "user__username")
    readonly_fields = ("credited_at", "raw_payload")
    autocomplete_fields = ("user", "payment_request")
    list_select_related = ("user", "payment_request")

# Register your models here.
