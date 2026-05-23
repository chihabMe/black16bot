from payments.models import PaymentRequest


ENABLED_PAYMENT_METHODS = (
    PaymentRequest.Method.BINANCE_DEPOSIT,
    PaymentRequest.Method.BYBIT_PAY,
    PaymentRequest.Method.USDT_BEP20,
    PaymentRequest.Method.USDT_TRC20,
)

PAYMENT_METHOD_LABELS = {
    PaymentRequest.Method.BINANCE_DEPOSIT: "Binance",
    PaymentRequest.Method.BYBIT_PAY: "Bybit",
    PaymentRequest.Method.USDT_BEP20: "USDT BEP-20",
    PaymentRequest.Method.USDT_TRC20: "USDT TRC-20",
}


def enabled_payment_method_choices():
    return [(method, PAYMENT_METHOD_LABELS[method]) for method in ENABLED_PAYMENT_METHODS]
