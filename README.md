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

## Telegram Top-up MVP

The first version uses manual top-up review. A user can create a payment request
with:

```txt
/topup_amount 10 cryptobot transaction-id-or-note
```

Users can also attach a screenshot/photo and use the same command as the photo
caption:

```txt
/topup_amount 10 cryptobot transaction-id-or-note
```

Supported method codes:

```txt
binance_deposit
binance_pay
bybit_pay
cryptobot
usdt_bep20
usdt_trc20
ton
tron
other
```

Admin approval happens in Django Admin under `Payment requests`.

Users can view and cancel pending manual payment requests with:

```txt
/payments
```

Admins receive Telegram notifications for new top-up requests when
`TELEGRAM_ADMIN_IDS` or `ADMIN_NOTIFICATION_CHAT_ID` is configured.

## Binance Automatic Top-up

If `BINANCE_API_KEY` and `BINANCE_API_SECRET` are set, users can ask the bot to
verify a Binance deposit transaction ID automatically:

```txt
/binance_topup 10 txid [network]
```

Example:

```txt
/binance_topup 10 0xabc123 BSC
```

Rules:

- Only confirmed Binance deposits are credited.
- The coin must be `USDT`.
- The deposit amount must be at least the requested top-up amount.
- If a network is provided, it must match the Binance deposit network.
- Each TXID can be credited only once.

For safest operation, use a read-only Binance API key. Do not enable trading or
withdrawals for this bot.

## Stock Management

Products are managed in Django Admin under `Products`.

To bulk upload stock:

1. Open a product in Django Admin.
2. Click `Upload stock`.
3. Paste one stock item per line.
4. Submit the form.

Each line becomes one deliverable stock item.

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
Set an API webhook from Telegram with:

```txt
/api_webhook https://example.com/webhook
```

Webhook payloads are signed with `X-Black16-Signature`.

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
- Quantity checkout locks all selected stock rows before charging.
- Admin actions are recorded in `Admin audit logs`.
- Do not update user balances directly outside service functions unless it is a deliberate admin correction.
