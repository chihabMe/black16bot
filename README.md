# Black16 Telegram Shop Bot

Django + PostgreSQL backend for a Telegram digital-products shop bot.

## Setup

1. Create `.env` from the example:

```bash
cp .env.example .env
```

2. Fill in at least:

```env
DJANGO_SECRET_KEY=
DATABASE_URL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_IDS=
STOCK_ENCRYPTION_KEY=
WEBHOOK_SIGNING_SECRET=
```

3. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

4. Run migrations:

```bash
python3 manage.py migrate
```

5. Create an admin user:

```bash
python3 manage.py createsuperuser
```

Optional: seed demo products, stock, and a demo user:

```bash
python3 manage.py seed_demo
```

6. Start Django Admin:

```bash
python3 manage.py runserver
```

7. Start the Telegram bot worker in another terminal:

```bash
python3 manage.py runbot
```

Useful bot commands:

```txt
/help
/shop
/telegram_accounts
/orders
/payments
/referral
/api
```

## Catalog And Checkout

Products support:

- notes/terms shown with `View Note`
- quantity buttons in Telegram checkout
- multi-item stock delivery in one order
- digital products and country-based Telegram account products

For Telegram account marketplace entries, set product type to
`Telegram account` in Django Admin and fill `country_code` / `country_name`.

## Telegram Top-up

Users can create a payment request with:

```txt
/topup_amount 10 binance_pay
```

After sending the exact payable amount, users submit the Binance Pay order ID or chain transaction ID with:

```txt
/topup_proof payment-id order-or-transaction-id
```

Supported method codes:

```txt
binance_pay
usdt_bep20
usdt_trc20
```

Screenshots are not accepted for top-ups. Active methods must be verifiable by
Binance Pay order ID or chain transaction ID.

Payment requests use a unique payable amount. If a user asks to top up
`10.00 USDT`, the bot may ask them to send `10.01 USDT`. The wallet still
credits the requested `10.00 USDT`; the unique payable amount is used to make
payment matching safer.

Users can view and cancel pending payment requests with:

```txt
/payments
```

Admins receive Telegram notifications for new top-up requests when
`TELEGRAM_ADMIN_IDS` or `ADMIN_NOTIFICATION_CHAT_ID` is configured.

## Automatic Top-up Verification

If `BINANCE_API_KEY`, `BINANCE_API_SECRET`, and `BINANCE_PAY_UID` are set,
Binance Pay top-ups can be verified automatically by order ID.

Rules:

- Only received Binance Pay transactions are credited.
- The coin must be `USDT`.
- The paid amount must be at least the requested top-up amount.
- The receiver UID must match `BINANCE_PAY_UID` when configured.
- Each order ID can be credited only once.

For safest operation, use a read-only Binance API key. Do not enable trading or
withdrawals for this bot.

For BEP-20 verification, configure:

```env
USDT_BEP20_WALLET_ADDRESS=
BSCSCAN_API_KEY=
BSC_USDT_CONTRACT_ADDRESS=0x55d398326f99059ff775485246999027b3197955
BSC_MIN_CONFIRMATIONS=15
```

For TRC-20 verification, configure:

```env
USDT_TRC20_WALLET_ADDRESS=
TRONGRID_API_KEY=
TRON_USDT_CONTRACT_ADDRESS=TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj
```

Legacy direct Binance deposit verification remains in the code only for old
pending payments created before Binance Pay became the user-facing method.

For pending payment requests where the user submitted proof, run this
periodically:

```bash
python3 manage.py verify_payments
```

This command checks pending Binance Pay, BEP-20, and TRC-20 requests and
auto-approves only when the payment is verified, uses USDT, has not been used
before, and matches the expected amount and receiver.

Expired top-up requests can be cleared by cron or a scheduler with:

```bash
python3 manage.py expire_payments
```

## Stock Management

Products are managed in Django Admin under `Products`.

To bulk upload stock:

1. Open a product in Django Admin.
2. Click `Upload stock`.
3. Paste one stock item per line.
4. Submit the form.

Each line becomes one deliverable stock item.

Stock secrets and delivered order payloads are encrypted before storage. If you
already imported plaintext stock before enabling this version, run:

```bash
python3 manage.py encrypt_existing_secrets
```

## Support And Admin Bot Commands

Users can create support tickets with:

```txt
/support_ticket describe the issue here
```

Admins can view quick bot stats with:

```txt
/admin_stats
```

The command is restricted to IDs in `TELEGRAM_ADMIN_IDS`.

## Referral System

Users can open their referral dashboard with:

```txt
/referral
```

When a referred user receives an approved top-up, a referral ledger entry is
created using `REFERRAL_COMMISSION_RATE` from `.env`. The default is `0.05`
for 5%.

Admins can settle referral earnings in Django Admin from `Referral ledger`:

- transfer available commissions to the referrer's wallet
- mark selected commissions as externally withdrawn
- reverse selected available commissions

## Developer API

Users can create or revoke a developer API key from `/api` in Telegram.

List products:

```bash
curl -H "Authorization: Bearer API_KEY" \
  http://127.0.0.1:8000/api/v1/products/
```

Create an order:

```bash
curl -X POST \
  -H "Authorization: Bearer API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"product_id": 1, "quantity": 1}' \
  http://127.0.0.1:8000/api/v1/orders/
```

API orders use the same transaction-safe purchase service as Telegram orders.
Each API key has admin-managed controls for order permission, max quantity per
order, daily spend limit, and per-minute order rate limit. API usage is logged
under `API usage logs`.

Set an API webhook from Telegram with:

```txt
/api_webhook https://example.com/webhook
```

Webhook payloads are signed with `X-Black16-Signature`. Webhook URLs must use
HTTPS and cannot resolve to private, loopback, link-local, reserved, or
multicast IP addresses.

## Docker Compose

```bash
docker compose up --build
```

Services:

- `web`: Django Admin/API
- `bot`: Telegram long-polling worker
- `db`: PostgreSQL

## Safety Notes

- Money values use `DecimalField`.
- Purchase logic lives in `orders.services.purchase_product`.
- Payment approval logic lives in `payments.services.approve_payment_request`.
- Both services use database transactions and row locks.
- Bot request throttling is stored in the database, so limits survive process
  restarts and multiple bot workers.
- Quantity checkout locks all selected stock rows before charging.
- One `Order item` row is stored per delivered stock item, so multi-quantity
  orders can be refunded or replaced consistently.
- Use a strong `STOCK_ENCRYPTION_KEY` and keep it stable. Changing it without a
  migration plan makes existing encrypted stock unreadable.
- Production should set `DJANGO_DEBUG=False`, a real `DJANGO_SECRET_KEY`, a
  separate `WEBHOOK_SIGNING_SECRET`, correct `DJANGO_ALLOWED_HOSTS`, and HTTPS
  cookie/redirect settings.
- Admin actions are recorded in `Admin audit logs`.
- Do not update user balances directly outside service functions unless it is a deliberate admin correction.
