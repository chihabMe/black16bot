from html import escape

from django.conf import settings

from payments.models import PaymentRequest


def payment_destination(method: str) -> str:
    destinations = {
        PaymentRequest.Method.BINANCE_PAY: settings.BINANCE_PAY_ID,
        PaymentRequest.Method.BINANCE_DEPOSIT: settings.BINANCE_PAY_ID,
        PaymentRequest.Method.BYBIT_PAY: settings.BYBIT_PAY_ID,
        PaymentRequest.Method.USDT_BEP20: settings.USDT_BEP20_WALLET_ADDRESS,
        PaymentRequest.Method.USDT_TRC20: settings.USDT_TRC20_WALLET_ADDRESS,
    }
    return destinations.get(method, "")


def payment_instruction_text(payment: PaymentRequest) -> str:
    destination = payment_destination(payment.method)
    destination_line = destination or "Ask support/admin for the destination before sending funds."
    amount = payment.payable_amount or payment.amount
    destination_block = f"<code>{escape(destination_line)}</code>" if destination else destination_line

    if payment.method == PaymentRequest.Method.BINANCE_PAY:
        method_help = (
            "Send USDT via Binance Pay to the Pay ID below, then submit the "
            "order ID shown by Binance after the transfer. "
            "The bot will verify it automatically."
        )
        destination_label = "Binance Pay ID"
    elif payment.method == PaymentRequest.Method.BINANCE_DEPOSIT:
        method_help = (
            "Send USDT to the configured Binance receiving account, then submit the Binance deposit TXID. "
            "The bot will verify it automatically through Binance."
        )
        destination_label = "Binance destination"
    elif payment.method == PaymentRequest.Method.BYBIT_PAY:
        method_help = "Bybit Pay is not enabled until API verification is configured."
        destination_label = "Bybit Pay ID"
    elif payment.method == PaymentRequest.Method.USDT_BEP20:
        method_help = "Send USDT on BNB Smart Chain / BEP-20 only."
        destination_label = "BEP-20 wallet"
    elif payment.method == PaymentRequest.Method.USDT_TRC20:
        method_help = "Send USDT on Tron / TRC-20 only."
        destination_label = "TRC-20 wallet"
    else:
        method_help = "Send payment, then submit transaction proof."
        destination_label = "Destination"

    return (
        f"Payment request #{payment.pk} created.\n\n"
        f"Credit amount: {payment.amount} USDT\n"
        f"Send exactly: {amount} USDT\n"
        f"Method: {payment.get_method_display()}\n\n"
        f"{method_help}\n\n"
        f"{destination_label}:\n{destination_block}\n\n"
        f"After the transaction is confirmed, reply here with the transaction ID or use:\n"
        f"/topup_proof {payment.pk} transaction-id"
    )


def payment_copy_details_text(payment: PaymentRequest) -> str:
    destination = payment_destination(payment.method)
    amount = payment.payable_amount or payment.amount
    proof_label = "Binance Pay Order ID" if payment.method == PaymentRequest.Method.BINANCE_PAY else "Transaction ID"
    destination_label = "Destination"
    if payment.method == PaymentRequest.Method.BINANCE_PAY:
        destination_label = "Binance Pay ID"
    elif payment.method == PaymentRequest.Method.USDT_BEP20:
        destination_label = "BEP-20 wallet"
    elif payment.method == PaymentRequest.Method.USDT_TRC20:
        destination_label = "TRC-20 wallet"

    destination_line = escape(destination) if destination else "Ask support/admin for destination"
    return (
        f"📋 Copy payment details\n\n"
        f"Payment ID:\n<code>{payment.pk}</code>\n\n"
        f"Send exactly:\n<code>{amount}</code> USDT\n\n"
        f"{destination_label}:\n<code>{destination_line}</code>\n\n"
        f"After paying, tap ✅ I Paid / Submit ID and send your {proof_label}."
    )
