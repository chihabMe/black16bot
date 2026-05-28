from decimal import Decimal
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import ReferralLedger, TelegramUser
from audit.services import log_admin_action
from bot.telegram_client import notify_admins, send_telegram_message
from payments.methods import ENABLED_PAYMENT_METHODS
from payments.models import PaymentRequest
from wallet.models import WalletTransaction


class PaymentApprovalError(Exception):
    pass


class PaymentRequestError(Exception):
    pass


def unique_payable_amount(*, requested_amount: Decimal, method: str) -> Decimal:
    base_amount = Decimal(str(requested_amount)).quantize(Decimal("0.01"))
    if base_amount <= 0:
        raise PaymentRequestError("Top-up amount must be greater than zero.")
    for cents in range(1, 100):
        candidate = base_amount + Decimal(cents) / Decimal("100")
        if not PaymentRequest.objects.filter(
            method=method,
            status=PaymentRequest.Status.PENDING,
            payable_amount=candidate,
        ).exists():
            return candidate.quantize(Decimal("0.01"))
    raise PaymentRequestError("Could not assign a unique payable amount. Try again later.")


def create_payment_request(
    *,
    user_id: int,
    amount,
    method: str,
    proof_text: str = "",
    proof_file_id: str = "",
) -> PaymentRequest:
    requested_amount = Decimal(str(amount)).quantize(Decimal("0.01"))
    if requested_amount <= 0:
        raise PaymentRequestError("Top-up amount must be greater than zero.")
    if method not in ENABLED_PAYMENT_METHODS:
        raise PaymentRequestError("Unsupported payment method.")
    payable_amount = unique_payable_amount(requested_amount=requested_amount, method=method)

    payment = PaymentRequest.objects.create(
        user_id=user_id,
        amount=requested_amount,
        requested_amount=requested_amount,
        payable_amount=payable_amount,
        method=method,
        proof_text=proof_text,
        proof_file_id=proof_file_id,
        expires_at=timezone.now() + timedelta(hours=2),
    )
    notify_admins(
        "New top-up request\n\n"
        f"Payment: #{payment.pk}\n"
        f"User ID: {payment.user.telegram_id}\n"
        f"Username: @{payment.user.username or '-'}\n"
        f"Credit amount: {payment.amount} USDT\n"
        f"Payable amount: {payment.payable_amount} USDT\n"
        f"Method: {payment.get_method_display()}\n"
        f"Proof: {payment.proof_text[:500] or '-'}"
    )
    return payment


def submit_payment_proof(
    *,
    payment_id: int,
    user_id: int,
    proof_text: str = "",
    proof_file_id: str = "",
) -> PaymentRequest:
    proof_text = proof_text.strip()
    if not proof_text:
        raise PaymentRequestError("Transaction ID is required.")

    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().get(pk=payment_id, user_id=user_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise PaymentRequestError("Only pending payment requests can receive proof.")
        payment.proof_text = proof_text or payment.proof_text
        payment.save(update_fields=["proof_text"])

    notify_admins(
        "Top-up transaction ID submitted\n\n"
        f"Payment: #{payment.pk}\n"
        f"User ID: {payment.user.telegram_id}\n"
        f"Credit amount: {payment.amount} USDT\n"
        f"Payable amount: {payment.payable_amount} USDT\n"
        f"Method: {payment.get_method_display()}\n"
        f"TXID: {payment.proof_text[:500]}"
    )
    return payment


def approve_payment_request(*, payment_id: int, admin_user=None, note: str = "") -> PaymentRequest:
    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status == PaymentRequest.Status.APPROVED:
            return payment
        if payment.status != PaymentRequest.Status.PENDING:
            raise PaymentApprovalError("Only pending payment requests can be approved.")

        user = TelegramUser.objects.select_for_update().get(pk=payment.user_id)
        TelegramUser.objects.filter(pk=user.pk).update(balance=F("balance") + payment.amount)

        payment.status = PaymentRequest.Status.APPROVED
        payment.approved_by = admin_user
        payment.approved_at = timezone.now()
        if note:
            payment.admin_note = note
        payment.save(update_fields=["status", "approved_by", "approved_at", "admin_note"])

        WalletTransaction.objects.create(
            user=user,
            amount=payment.amount,
            transaction_type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.COMPLETED,
            related_payment=payment,
            created_by=admin_user,
            note=note or f"Approved payment request #{payment.pk}",
        )
        create_referral_commission(payment)
        log_admin_action(
            action="payment.approve",
            actor=admin_user,
            target=payment,
            message=f"Approved payment request #{payment.pk}",
            metadata={"amount": str(payment.amount), "user_id": payment.user_id},
        )
        send_telegram_message(
            payment.user.telegram_id,
            f"Your top-up request #{payment.pk} was approved.\n"
            f"Amount credited: {payment.amount} USDT",
        )
        return payment


def reject_payment_request(*, payment_id: int, admin_user=None, note: str = "") -> PaymentRequest:
    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().get(pk=payment_id)
        if payment.status == PaymentRequest.Status.APPROVED:
            raise PaymentApprovalError("Approved payment requests cannot be rejected.")
        if payment.status == PaymentRequest.Status.REJECTED:
            return payment

        payment.status = PaymentRequest.Status.REJECTED
        payment.rejected_at = timezone.now()
        if admin_user:
            payment.approved_by = admin_user
        if note:
            payment.admin_note = note
        payment.save(update_fields=["status", "rejected_at", "approved_by", "admin_note"])
        log_admin_action(
            action="payment.reject",
            actor=admin_user,
            target=payment,
            message=f"Rejected payment request #{payment.pk}",
        )
        send_telegram_message(
            payment.user.telegram_id,
            f"Your top-up request #{payment.pk} was rejected.\n"
            f"Reason: {payment.admin_note or 'Please contact support.'}",
        )
        return payment


def cancel_payment_request(*, payment_id: int, user_id: int | None = None) -> PaymentRequest:
    with transaction.atomic():
        queryset = PaymentRequest.objects.select_for_update()
        if user_id is not None:
            queryset = queryset.filter(user_id=user_id)
        payment = queryset.get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise PaymentApprovalError("Only pending payment requests can be cancelled.")
        payment.status = PaymentRequest.Status.CANCELLED
        payment.cancelled_at = timezone.now()
        payment.save(update_fields=["status", "cancelled_at"])
        return payment


def expire_pending_payment_requests() -> int:
    now = timezone.now()
    return PaymentRequest.objects.filter(
        status=PaymentRequest.Status.PENDING,
        expires_at__isnull=False,
        expires_at__lt=now,
    ).update(status=PaymentRequest.Status.EXPIRED)


def create_referral_commission(payment: PaymentRequest) -> ReferralLedger | None:
    user = payment.user
    if not user.referred_by_id:
        return None
    if ReferralLedger.objects.filter(source_payment=payment).exists():
        return None
    rate = Decimal(str(settings.REFERRAL_COMMISSION_RATE))
    commission = (payment.amount * rate).quantize(Decimal("0.01"))
    if commission <= 0:
        return None
    return ReferralLedger.objects.create(
        referrer=user.referred_by,
        referee=user,
        source_payment=payment,
        commission_amount=commission,
    )
