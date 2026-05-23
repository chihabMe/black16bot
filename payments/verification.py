from dataclasses import dataclass

from payments.binance import BinanceDepositError, verify_pending_binance_payment
from payments.models import PaymentRequest


@dataclass(frozen=True)
class VerificationResult:
    checked: int
    approved: int
    failed: int
    errors: tuple[str, ...] = ()


def verify_pending_payment(payment: PaymentRequest) -> bool:
    if payment.method == PaymentRequest.Method.BINANCE_DEPOSIT:
        verify_pending_binance_payment(payment_id=payment.pk)
        return True
    return False


def verify_pending_payments(*, limit: int = 100) -> VerificationResult:
    queryset = (
        PaymentRequest.objects.filter(status=PaymentRequest.Status.PENDING)
        .exclude(proof_text="")
        .order_by("created_at")[:limit]
    )
    checked = 0
    approved = 0
    failed = 0
    errors = []
    for payment in queryset:
        checked += 1
        try:
            if verify_pending_payment(payment):
                approved += 1
        except BinanceDepositError as exc:
            failed += 1
            errors.append(f"Payment #{payment.pk}: {exc}")
    return VerificationResult(checked=checked, approved=approved, failed=failed, errors=tuple(errors))
