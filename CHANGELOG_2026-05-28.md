# Binance Pay Integration & Top-up Flow Overhaul

**Date**: 2026-05-28  
**Branch**: master  
**Status**: Deployed and verified on production

---

## Summary

Added full **Binance Pay** support with automatic verification via the Binance Pay transactions API. Users can now top up via Binance Pay and submit the **order ID** (not a blockchain TXID) for instant auto-verification. Also overhauled the top-up UX to a guided multi-step flow and added BEP-20/TRC-20 chain verification.

---

## Changes

### Binance Pay Verification (new)

| File | Change |
|---|---|
| `payments/binance.py` | Added `fetch_binance_pay_by_order_id()` — queries `/sapi/v1/pay/transactions` with pagination, matches by `orderId` |
| `payments/binance.py` | Added `verify_pending_binance_pay_payment()` — validates currency, amount (>= requested), receiver UID, then credits user atomically |
| `payments/models.py` | Added `BINANCE_PAY` to `VerifiedDeposit.Provider` choices |
| `payments/methods.py` | Enabled `binance_pay` as first option in `ENABLED_PAYMENT_METHODS`; removed `bybit_pay` (not yet verifiable) |
| `payments/instructions.py` | Added Binance Pay instruction text telling users to submit the order ID |
| `payments/verification.py` | Added `BINANCE_PAY` dispatch to `verify_pending_payment()` |
| `config/settings.py` | Added `BINANCE_PAY_UID` setting for receiver UID validation |
| `.env.example` | Added `BINANCE_PAY_UID`, `BINANCE_PAY_ID`, chain API keys |
| `payments/migrations/0007_add_binance_pay_provider.py` | Migration for new provider choice |

### Top-up Flow Overhaul

| File | Change |
|---|---|
| `bot/handlers.py` | Replaced single-command top-up with guided flow: select method → enter amount → receive instructions → submit proof |
| `bot/handlers.py` | Added `topup_proof` command (`/topup_proof payment_id txid`) for resubmitting corrected IDs |
| `bot/handlers.py` | Added `text_message` handler for conversational top-up flow via `context.user_data` |
| `bot/handlers.py` | Added `attach_topup_proof()` — submits proof, attempts immediate verification, shows resubmit instructions on failure |
| `bot/handlers.py` | Rejected screenshots with clear message: "Screenshots are not accepted for top-ups" |
| `bot/handlers.py` | Updated `/topup_amount` help text to list all enabled methods |
| `bot/management/commands/runbot.py` | Registered `topup_proof` command, `text_message` handler, and bot menu commands |
| `payments/services.py` | Added `submit_payment_proof()` — updates `proof_text` on pending requests, notifies admins |
| `payments/instructions.py` | New file — generates per-method instruction text with destination and payable amount |

### BEP-20 / TRC-20 Chain Verification (new)

| File | Change |
|---|---|
| `payments/chain.py` | New file — `verify_pending_bep20_payment()` via BscScan or Moralis API |
| `payments/chain.py` | `verify_pending_trc20_payment()` via TronGrid API |
| `payments/chain.py` | `approve_verified_chain_payment()` — shared atomic approval logic |
| `payments/verification.py` | Added `USDT_BEP20` and `USDT_TRC20` dispatch branches |
| `config/settings.py` | Added BscScan, Moralis, TronGrid, chain contract address settings |

### Tests

| File | Change |
|---|---|
| `payments/tests.py` | Added tests for `submit_payment_proof` (success + rejection of non-pending) |
| `payments/tests.py` | Added tests for BEP-20 verification (Moralis path) and TRC-20 verification |
| `payments/tests.py` | Added test for disabled `bybit_pay` method rejection |
| `bot/tests.py` | Updated top-up menu test to expect Binance Pay, not Bybit |

---

## How Binance Pay Verification Works

```
User selects "Binance Pay" → enters amount → bot shows Pay ID + payable amount
    → user sends USDT via Binance Pay app → gets an order ID from Binance
    → user submits: /topup_proof <payment_id> <order_id>
    → bot calls /sapi/v1/pay/transactions, matches orderId
    → validates: currency=USDT, amount>=requested, receiver UID matches
    → credits balance, creates VerifiedDeposit, notifies user + admins
```

**Key difference from on-chain deposits**: Binance Pay only gives users a numeric `orderId`, not a blockchain hash. The deposit history API (`/sapi/v1/capital/deposit/hisrec`) does not return Pay transfers — they live exclusively in `/sapi/v1/pay/transactions`.

---

## Verification Results

| Payment | Method | Order ID | Status | Balance Impact |
|---|---|---|---|---|
| #9 | binance_pay | `434140106808442880` | approved | +1.00 USDT |
| #10 | binance_pay | `434143115547811840` | approved | +1.00 USDT |

Duplicate order ID reuse is correctly blocked.

---

## New Environment Variables

```env
BINANCE_PAY_ID=          # Binance Pay ID shown to users as destination
BINANCE_PAY_UID=         # Binance user ID (binanceId) for receiver validation
BINANCE_PAY_API_KEY=     # Binance API key with Pay read access
BINANCE_PAY_API_SECRET=  # Binance API secret
BSCSCAN_API_KEY=         # BscScan API key for BEP-20 verification
TRONGRID_API_KEY=        # TronGrid API key for TRC-20 verification
MORALIS_API_KEY=         # Optional: Moralis API key (alternative BEP-20 source)
```
