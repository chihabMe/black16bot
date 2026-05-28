from payments.models import PaymentRequest


ENABLED_PAYMENT_METHODS = (
    PaymentRequest.Method.BINANCE_PAY,
    PaymentRequest.Method.BINANCE_DEPOSIT,
    PaymentRequest.Method.USDT_BEP20,
    PaymentRequest.Method.USDT_TRC20,
)

PAYMENT_METHOD_LABELS = {
    PaymentRequest.Method.BINANCE_PAY: "Binance Pay",
    PaymentRequest.Method.BINANCE_DEPOSIT: "Binance Deposit",
    PaymentRequest.Method.USDT_BEP20: "USDT BEP-20",
    PaymentRequest.Method.USDT_TRC20: "USDT TRC-20",
}


def enabled_payment_method_choices():
    return [(method, PAYMENT_METHOD_LABELS[method]) for method in ENABLED_PAYMENT_METHODS]
