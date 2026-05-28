import json
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


class ChainDepositError(Exception):
    pass


def get_json(url: str, headers: dict[str, str] | None = None) -> dict:
    request_headers = {"User-Agent": "black16bot/1.0", **(headers or {})}
    request = urllib.request.Request(url, headers=request_headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except Exception as exc:
        raise ChainDepositError(f"Could not query chain API: {exc}") from exc


def decimal_token_amount(value: str, decimals: int) -> Decimal:
    return (Decimal(str(value)) / (Decimal(10) ** decimals)).quantize(Decimal("0.01"))


def verify_pending_bep20_payment(*, payment_id: int) -> VerifiedDeposit:
    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise ChainDepositError("Only pending payment requests can be verified.")
        if payment.method != PaymentRequest.Method.USDT_BEP20:
            raise ChainDepositError("Payment request is not a BEP-20 payment.")
        if not settings.USDT_BEP20_WALLET_ADDRESS:
            raise ChainDepositError("USDT_BEP20_WALLET_ADDRESS is not configured.")
        txid = payment.proof_text.strip()
        if not txid:
            raise ChainDepositError("Payment request does not include a transaction ID.")
        if VerifiedDeposit.objects.select_for_update().filter(txid=txid).exists():
            raise ChainDepositError("This transaction ID was already used.")
        expected_amount = payment.payable_amount or payment.amount

    if settings.MORALIS_API_KEY:
        transfer = fetch_moralis_bep20_transfer(txid=txid)
        deposit_amount = Decimal(str(transfer.get("value_decimal", "0"))).quantize(Decimal("0.01"))
        if deposit_amount != expected_amount:
            raise ChainDepositError(f"Deposit amount mismatch: found {deposit_amount}, expected {expected_amount}.")

        return approve_verified_chain_payment(
            payment_id=payment_id,
            provider=VerifiedDeposit.Provider.MORALIS,
            txid=txid,
            coin="USDT",
            network="BEP20",
            deposit_amount=deposit_amount,
            raw_payload=transfer,
        )

    params = {
        "chainid": settings.BSC_CHAIN_ID,
        "module": "account",
        "action": "tokentx",
        "contractaddress": settings.BSC_USDT_CONTRACT_ADDRESS,
        "address": settings.USDT_BEP20_WALLET_ADDRESS,
        "startblock": "0",
        "endblock": "99999999",
        "sort": "desc",
        "apikey": settings.BSCSCAN_API_KEY,
    }
    url = f"{settings.BSCSCAN_API_BASE_URL}?{urllib.parse.urlencode(params)}"
    payload = get_json(url)
    transfers = payload.get("result", [])
    if not isinstance(transfers, list):
        raise ChainDepositError(str(payload.get("message") or "Invalid BscScan response."))

    transfer = next((row for row in transfers if str(row.get("hash", "")).lower() == txid.lower()), None)
    if not transfer:
        raise ChainDepositError("BEP-20 transaction was not found for the configured wallet.")
    if str(transfer.get("to", "")).lower() != settings.USDT_BEP20_WALLET_ADDRESS.lower():
        raise ChainDepositError("BEP-20 transaction recipient does not match the configured wallet.")
    if str(transfer.get("contractAddress", "")).lower() != settings.BSC_USDT_CONTRACT_ADDRESS.lower():
        raise ChainDepositError("BEP-20 transaction is not USDT.")
    confirmations = int(transfer.get("confirmations") or 0)
    if confirmations < settings.BSC_MIN_CONFIRMATIONS:
        raise ChainDepositError(f"BEP-20 transaction has {confirmations} confirmation(s).")
    deposit_amount = decimal_token_amount(transfer.get("value", "0"), int(transfer.get("tokenDecimal") or 18))
    if deposit_amount != expected_amount:
        raise ChainDepositError(f"Deposit amount mismatch: found {deposit_amount}, expected {expected_amount}.")

    return approve_verified_chain_payment(
        payment_id=payment_id,
        provider=VerifiedDeposit.Provider.BSCSCAN,
        txid=txid,
        coin="USDT",
        network="BEP20",
        deposit_amount=deposit_amount,
        raw_payload=transfer,
    )


def fetch_moralis_bep20_transfer(*, txid: str) -> dict:
    if not settings.MORALIS_API_KEY:
        raise ChainDepositError("MORALIS_API_KEY is not configured.")

    cursor = ""
    for _ in range(5):
        params = [
            ("chain", "bsc"),
            ("limit", "100"),
            ("contract_addresses", settings.BSC_USDT_CONTRACT_ADDRESS),
        ]
        if cursor:
            params.append(("cursor", cursor))
        url = (
            f"{settings.MORALIS_API_BASE_URL.rstrip('/')}/"
            f"{urllib.parse.quote(settings.USDT_BEP20_WALLET_ADDRESS)}/erc20/transfers?"
            f"{urllib.parse.urlencode(params)}"
        )
        payload = get_json(
            url,
            {
                "accept": "application/json",
                "X-API-Key": settings.MORALIS_API_KEY,
            },
        )
        transfers = payload.get("result", [])
        if not isinstance(transfers, list):
            raise ChainDepositError("Invalid Moralis response.")
        transfer = next(
            (
                row
                for row in transfers
                if str(row.get("transaction_hash", "")).lower() == txid.lower()
            ),
            None,
        )
        if transfer:
            if str(transfer.get("to_address", "")).lower() != settings.USDT_BEP20_WALLET_ADDRESS.lower():
                raise ChainDepositError("BEP-20 transaction recipient does not match the configured wallet.")
            if str(transfer.get("address", "")).lower() != settings.BSC_USDT_CONTRACT_ADDRESS.lower():
                raise ChainDepositError("BEP-20 transaction is not USDT.")
            return transfer
        cursor = payload.get("cursor") or ""
        if not cursor:
            break
    raise ChainDepositError("BEP-20 transaction was not found for the configured wallet.")


def verify_pending_trc20_payment(*, payment_id: int) -> VerifiedDeposit:
    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise ChainDepositError("Only pending payment requests can be verified.")
        if payment.method != PaymentRequest.Method.USDT_TRC20:
            raise ChainDepositError("Payment request is not a TRC-20 payment.")
        if not settings.USDT_TRC20_WALLET_ADDRESS:
            raise ChainDepositError("USDT_TRC20_WALLET_ADDRESS is not configured.")
        txid = payment.proof_text.strip()
        if not txid:
            raise ChainDepositError("Payment request does not include a transaction ID.")
        if VerifiedDeposit.objects.select_for_update().filter(txid=txid).exists():
            raise ChainDepositError("This transaction ID was already used.")
        expected_amount = payment.payable_amount or payment.amount

    params = {
        "only_confirmed": "true",
        "limit": "200",
        "contract_address": settings.TRON_USDT_CONTRACT_ADDRESS,
    }
    url = (
        f"{settings.TRONGRID_API_BASE_URL.rstrip('/')}/v1/accounts/"
        f"{urllib.parse.quote(settings.USDT_TRC20_WALLET_ADDRESS)}/transactions/trc20?"
        f"{urllib.parse.urlencode(params)}"
    )
    headers = {"TRON-PRO-API-KEY": settings.TRONGRID_API_KEY} if settings.TRONGRID_API_KEY else {}
    payload = get_json(url, headers=headers)
    transfers = payload.get("data", [])
    if not isinstance(transfers, list):
        raise ChainDepositError("Invalid TronGrid response.")

    transfer = next((row for row in transfers if str(row.get("transaction_id", "")).lower() == txid.lower()), None)
    if not transfer:
        raise ChainDepositError("TRC-20 transaction was not found for the configured wallet.")
    if str(transfer.get("to", "")) != settings.USDT_TRC20_WALLET_ADDRESS:
        raise ChainDepositError("TRC-20 transaction recipient does not match the configured wallet.")
    token_info = transfer.get("token_info") or {}
    if str(token_info.get("address", "")) != settings.TRON_USDT_CONTRACT_ADDRESS:
        raise ChainDepositError("TRC-20 transaction is not USDT.")
    deposit_amount = decimal_token_amount(transfer.get("value", "0"), int(token_info.get("decimals") or 6))
    if deposit_amount != expected_amount:
        raise ChainDepositError(f"Deposit amount mismatch: found {deposit_amount}, expected {expected_amount}.")

    return approve_verified_chain_payment(
        payment_id=payment_id,
        provider=VerifiedDeposit.Provider.TRONGRID,
        txid=txid,
        coin="USDT",
        network="TRC20",
        deposit_amount=deposit_amount,
        raw_payload=transfer,
    )


def approve_verified_chain_payment(
    *,
    payment_id: int,
    provider: str,
    txid: str,
    coin: str,
    network: str,
    deposit_amount: Decimal,
    raw_payload: dict,
) -> VerifiedDeposit:
    with transaction.atomic():
        payment = PaymentRequest.objects.select_for_update().select_related("user").get(pk=payment_id)
        if payment.status != PaymentRequest.Status.PENDING:
            raise ChainDepositError("Only pending payment requests can be verified.")
        if VerifiedDeposit.objects.select_for_update().filter(txid=txid).exists():
            raise ChainDepositError("This transaction ID was already used.")

        user = TelegramUser.objects.select_for_update().get(pk=payment.user_id)
        TelegramUser.objects.filter(pk=user.pk).update(balance=F("balance") + payment.amount)
        payment.status = PaymentRequest.Status.APPROVED
        payment.approved_at = timezone.now()
        payment.admin_note = f"Auto-approved by {network} TXID check."
        payment.save(update_fields=["status", "approved_at", "admin_note"])
        WalletTransaction.objects.create(
            user=user,
            amount=payment.amount,
            transaction_type=WalletTransaction.Type.TOPUP,
            status=WalletTransaction.Status.COMPLETED,
            related_payment=payment,
            note=f"Auto-approved {network} deposit {txid}",
        )
        verified = VerifiedDeposit.objects.create(
            user=user,
            payment_request=payment,
            provider=provider,
            txid=txid,
            coin=coin,
            network=network,
            amount=deposit_amount,
            raw_payload=raw_payload,
        )
        create_referral_commission(payment)

    send_telegram_message(
        user.telegram_id,
        f"Your {network} top-up was verified automatically.\nAmount credited: {payment.amount} USDT",
    )
    notify_admins(
        f"{network} top-up auto-approved\n\n"
        f"Payment: #{payment.pk}\n"
        f"User ID: {user.telegram_id}\n"
        f"Credit amount: {payment.amount} USDT\n"
        f"Paid amount: {deposit_amount} USDT\n"
        f"TXID: {txid}"
    )
    return verified
