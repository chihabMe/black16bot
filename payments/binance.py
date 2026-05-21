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
