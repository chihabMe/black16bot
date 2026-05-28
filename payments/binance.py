import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import TelegramUser
from bot.telegram_client import notify_admins, send_telegram_message
from payments.models import PaymentRequest, VerifiedDeposit
from payments.services import create_referral_commission
from wallet.models import WalletTransaction


class BinanceDepositError(Exception):
    pass


def signed_binance_request(path: str, params: dict[str, str]) -> list[dict]:
    if not settings.BINANCE_API_KEY or not settings.BINANCE_API_SECRET:
        raise BinanceDepositError("Binance API key/secret is not configured.")

    params = {
        **params,
        "timestamp": str(int(time.time() * 1000)),
        "recvWindow": "5000",
    }
    query = urllib.parse.urlencode(params)
    signature = hmac.new(
        settings.BINANCE_API_SECRET.encode(),
        query.encode(),
        hashlib.sha256,
    ).hexdigest()
    url = f"{settings.BINANCE_API_BASE_URL.rstrip('/')}{path}?{query}&signature={signature}"
    request = urllib.request.Request(url, headers={"X-MBX-APIKEY": settings.BINANCE_API_KEY})

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except Exception as exc:
        raise BinanceDepositError(f"Could not query Binance: {exc}") from exc


def fetch_binance_deposit_by_txid(*, txid: str, coin: str = "USDT") -> dict | None:
    payload = signed_binance_request(
        "/sapi/v1/capital/deposit/hisrec",
        {"coin": coin.upper(), "txId": txid},
    )
    for row in payload:
        if str(row.get("txId", "")).lower() == txid.lower():
            return row
    return None


def verify_binance_deposit(
    *,
    user_id: int,
    amount: Decimal,
    txid: str,
    coin: str = "USDT",
    network: str = "",
) -> VerifiedDeposit:
    if amount <= 0:
        raise BinanceDepositError("Amount must be greater than zero.")
    if not txid:
        raise BinanceDepositError("Transaction ID is required.")
    if VerifiedDeposit.objects.filter(provider=VerifiedDeposit.Provider.BINANCE, txid=txid).exists():
        raise BinanceDepositError("This transaction ID was already used.")

    deposit = fetch_binance_deposit_by_txid(txid=txid, coin=coin)
    if not deposit:
        raise BinanceDepositError("Deposit transaction was not found on Binance.")

    if int(deposit.get("status", -1)) != 1:
        raise BinanceDepositError("Deposit is not confirmed yet.")

    deposit_coin = str(deposit.get("coin", "")).upper()
    if deposit_coin != coin.upper():
        raise BinanceDepositError(f"Deposit coin mismatch: expected {coin.upper()}, got {deposit_coin}.")

    deposit_network = str(deposit.get("network", ""))
    if network and deposit_network.upper() != network.upper():
        raise BinanceDepositError(f"Deposit network mismatch: expected {network}, got {deposit_network}.")

    deposit_amount = Decimal(str(deposit.get("amount", "0")))
    if deposit_amount < amount:
        raise BinanceDepositError(f"Deposit amount is too small: found {deposit_amount}, expected {amount}.")
    credited_amount = deposit_amount.quantize(Decimal("0.01"))
    if credited_amount <= 0:
        raise BinanceDepositError("Deposit amount is too small after wallet rounding.")

    with transaction.atomic():
        if VerifiedDeposit.objects.select_for_update().filter(
            provider=VerifiedDeposit.Provider.BINANCE,
            txid=txid,
        ).exists():
            raise BinanceDepositError("This transaction ID was already used.")

        user = TelegramUser.objects.select_for_update().get(pk=user_id)
        payment = PaymentRequest.objects.create(
            user=user,
            amount=credited_amount,
            method=PaymentRequest.Method.BINANCE_DEPOSIT,
            status=PaymentRequest.Status.APPROVED,
            proof_text=txid,
            approved_at=timezone.now(),
            admin_note="Auto-approved by Binance deposit TXID check.",
        )
        TelegramUser.objects.filter(pk=user.pk).update(balance=F("balance") + credited_amount)
        WalletTransaction.objects.create(
            user=user,
            amount=credited_amount,
            transaction_type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.COMPLETED,
            related_payment=payment,
            note=f"Auto-approved Binance deposit {txid}",
        )
        verified = VerifiedDeposit.objects.create(
            user=user,
            payment_request=payment,
            provider=VerifiedDeposit.Provider.BINANCE,
            txid=txid,
            coin=deposit_coin,
            network=deposit_network,
            amount=deposit_amount,
            raw_payload=deposit,
        )
        create_referral_commission(payment)

    send_telegram_message(
        user.telegram_id,
        f"Your Binance top-up was verified automatically.\nAmount credited: {credited_amount} USDT",
    )
    notify_admins(
        "Binance top-up auto-approved\n\n"
        f"User ID: {user.telegram_id}\n"
        f"Amount: {credited_amount} USDT\n"
        f"TXID: {txid}"
    )
    return verified


def verify_pending_binance_payment(*, payment_id: int) -> VerifiedDeposit:
    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise BinanceDepositError("Only pending payment requests can be verified.")
        if payment.method != PaymentRequest.Method.BINANCE_DEPOSIT:
            raise BinanceDepositError("Payment request is not a Binance payment.")
        txid = payment.proof_text.strip()
        if not txid:
            raise BinanceDepositError("Payment request does not include a transaction ID.")
        if VerifiedDeposit.objects.select_for_update().filter(
            provider=VerifiedDeposit.Provider.BINANCE,
            txid=txid,
        ).exists():
            raise BinanceDepositError("This transaction ID was already used.")
        expected_amount = payment.payable_amount or payment.amount

    deposit = fetch_binance_deposit_by_txid(txid=txid, coin="USDT")
    if not deposit:
        raise BinanceDepositError("Deposit transaction was not found on Binance.")
    if int(deposit.get("status", -1)) != 1:
        raise BinanceDepositError("Deposit is not confirmed yet.")
    deposit_coin = str(deposit.get("coin", "")).upper()
    if deposit_coin != "USDT":
        raise BinanceDepositError(f"Deposit coin mismatch: expected USDT, got {deposit_coin}.")
    deposit_amount = Decimal(str(deposit.get("amount", "0"))).quantize(Decimal("0.01"))
    if deposit_amount != expected_amount:
        raise BinanceDepositError(f"Deposit amount mismatch: found {deposit_amount}, expected {expected_amount}.")

    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise BinanceDepositError("Only pending payment requests can be verified.")
        if VerifiedDeposit.objects.select_for_update().filter(
            provider=VerifiedDeposit.Provider.BINANCE,
            txid=txid,
        ).exists():
            raise BinanceDepositError("This transaction ID was already used.")
        user = TelegramUser.objects.select_for_update().get(pk=payment.user_id)
        TelegramUser.objects.filter(pk=user.pk).update(balance=F("balance") + payment.amount)
        payment.status = PaymentRequest.Status.APPROVED
        payment.approved_at = timezone.now()
        payment.admin_note = "Auto-approved by Binance pending payment verifier."
        payment.save(update_fields=["status", "approved_at", "admin_note"])
        WalletTransaction.objects.create(
            user=user,
            amount=payment.amount,
            transaction_type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.COMPLETED,
            related_payment=payment,
            note=f"Auto-approved Binance deposit {txid}",
        )
        verified = VerifiedDeposit.objects.create(
            user=user,
            payment_request=payment,
            provider=VerifiedDeposit.Provider.BINANCE,
            txid=txid,
            coin=deposit_coin,
            network=str(deposit.get("network", "")),
            amount=Decimal(str(deposit.get("amount", "0"))),
            raw_payload=deposit,
        )
        create_referral_commission(payment)

    send_telegram_message(
        user.telegram_id,
        f"✅ Your Binance top-up was verified.\nAmount credited: {payment.amount} USDT",
    )
    notify_admins(
        "Binance top-up auto-approved\n\n"
        f"Payment: #{payment.pk}\n"
        f"User ID: {user.telegram_id}\n"
        f"Credit amount: {payment.amount} USDT\n"
        f"Paid amount: {deposit_amount} USDT\n"
        f"TXID: {txid}"
    )
    return verified


def fetch_binance_pay_by_order_id(*, order_id: str) -> dict | None:
    params: dict[str, str] = {}
    for _ in range(5):
        payload = signed_binance_request("/sapi/v1/pay/transactions", params)
        data = payload.get("data", [])
        if not isinstance(data, list):
            return None
        for row in data:
            if str(row.get("orderId", "")) == order_id:
                return row
        cursor = payload.get("cursor") or ""
        if not cursor:
            break
        params["cursor"] = cursor
    return None


def verify_pending_binance_pay_payment(*, payment_id: int) -> VerifiedDeposit:
    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise BinanceDepositError("Only pending payment requests can be verified.")
        if payment.method != PaymentRequest.Method.BINANCE_PAY:
            raise BinanceDepositError("Payment request is not a Binance Pay payment.")
        order_id = payment.proof_text.strip()
        if not order_id:
            raise BinanceDepositError("Payment request does not include an order ID.")
        if VerifiedDeposit.objects.select_for_update().filter(
            provider=VerifiedDeposit.Provider.BINANCE_PAY,
            txid=order_id,
        ).exists():
            raise BinanceDepositError("This order ID was already used.")
        requested_amount = payment.requested_amount or payment.amount

    pay_tx = fetch_binance_pay_by_order_id(order_id=order_id)
    if not pay_tx:
        raise BinanceDepositError("Binance Pay transaction was not found.")

    pay_currency = str(pay_tx.get("currency", "")).upper()
    if pay_currency != "USDT":
        raise BinanceDepositError(f"Binance Pay currency mismatch: expected USDT, got {pay_currency}.")

    pay_amount = Decimal(str(pay_tx.get("amount", "0")))
    if pay_amount <= 0:
        raise BinanceDepositError("Binance Pay transaction is not a received payment.")
    if pay_amount < requested_amount:
        raise BinanceDepositError(
            f"Binance Pay amount is too small: found {pay_amount}, expected at least {requested_amount}."
        )

    receiver_info = pay_tx.get("receiverInfo") or {}
    receiver_uid = str(receiver_info.get("binanceId", ""))
    if settings.BINANCE_PAY_UID and receiver_uid != settings.BINANCE_PAY_UID:
        raise BinanceDepositError(
            f"Binance Pay receiver UID mismatch: expected {settings.BINANCE_PAY_UID}, got {receiver_uid}."
        )

    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise BinanceDepositError("Only pending payment requests can be verified.")
        if VerifiedDeposit.objects.select_for_update().filter(
            provider=VerifiedDeposit.Provider.BINANCE_PAY,
            txid=order_id,
        ).exists():
            raise BinanceDepositError("This order ID was already used.")
        user = TelegramUser.objects.select_for_update().get(pk=payment.user_id)
        TelegramUser.objects.filter(pk=user.pk).update(balance=F("balance") + payment.amount)
        payment.status = PaymentRequest.Status.APPROVED
        payment.approved_at = timezone.now()
        payment.admin_note = "Auto-approved by Binance Pay order ID check."
        payment.save(update_fields=["status", "approved_at", "admin_note"])
        WalletTransaction.objects.create(
            user=user,
            amount=payment.amount,
            transaction_type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.COMPLETED,
            related_payment=payment,
            note=f"Auto-approved Binance Pay order {order_id}",
        )
        verified = VerifiedDeposit.objects.create(
            user=user,
            payment_request=payment,
            provider=VerifiedDeposit.Provider.BINANCE_PAY,
            txid=order_id,
            coin=pay_currency,
            network="BinancePay",
            amount=pay_amount,
            raw_payload=pay_tx,
        )
        create_referral_commission(payment)

    send_telegram_message(
        user.telegram_id,
        f"✅ Your Binance Pay top-up was verified.\nAmount credited: {payment.amount} USDT",
    )
    notify_admins(
        "Binance Pay top-up auto-approved\n\n"
        f"Payment: #{payment.pk}\n"
        f"User ID: {user.telegram_id}\n"
        f"Credit amount: {payment.amount} USDT\n"
        f"Paid amount: {pay_amount} USDT\n"
        f"Order ID: {order_id}"
    )
    return verified
