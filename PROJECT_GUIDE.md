# Telegram Digital Shop Bot - Django Project Guide

## Project Goal

Build a Telegram bot for selling digital products such as subscription accounts,
software accounts, license keys, and similar stock-based digital goods.

The bot should match the behavior observed in the reference video:

- Telegram storefront with inline menus.
- Product catalog with price, stock count, pagination, refresh, and sorting.
- User wallet balance in USDT.
- Manual top-up requests.
- Admin-managed stock delivery.
- User order history.
- Profile, language, support, and developer API screens.
- Django Admin as the main back-office interface.

The first version must prioritize speed, safety, and operational simplicity.
Use Django Admin instead of building a custom admin dashboard.

## Chosen Tech Stack

- Backend framework: Django
- Database: PostgreSQL
- Admin interface: Django Admin
- Telegram bot: `python-telegram-bot` or `aiogram`
- Environment config: `.env`
- Deployment target: VPS or Docker Compose
- Production process model:
  - Django web process for Admin/API
  - Separate bot worker process for Telegram long polling initially
  - PostgreSQL database

Recommended bot library for v1: `python-telegram-bot`.

Reason: it is straightforward to integrate with Django, can run as a Django
management command, and is enough for the first production version.

## Django Admin Decision

Django Admin is enough for v1.

Use Django Admin for:

- Products
- Stock items
- Users
- Orders
- Wallet transactions
- Payment requests
- Broadcasts
- Support tickets
- API keys

Do not build a custom admin dashboard at the start.

Only add small Django Admin custom actions or custom admin pages when needed,
especially for:

- Bulk stock upload
- Approving/rejecting top-ups
- Refunding orders
- Replacing sold stock
- Sending broadcasts

Build a custom admin panel later only if Django Admin becomes too slow or
unfriendly for daily operations.

## Required API Keys And Secrets

All secrets must be placed in a local `.env` file.
Never commit real secrets to git.

Create `.env.example` with placeholders only.

### Required For MVP

```env
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

DATABASE_URL=postgres://black16bot:black16bot@localhost:5432/black16bot

TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_IDS=

DEFAULT_LANGUAGE=en
DEFAULT_CURRENCY=USDT
```

### Recommended For Production

```env
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=your-domain.com,server-ip
CSRF_TRUSTED_ORIGINS=https://your-domain.com

SECURE_SSL_REDIRECT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

### Optional Payment Integrations For Later

```env
CRYPTOBOT_API_TOKEN=
BINANCE_PAY_API_KEY=
BINANCE_PAY_API_SECRET=
BYBIT_API_KEY=
BYBIT_API_SECRET=
TRON_API_KEY=
TON_API_KEY=
USDT_BEP20_WALLET_ADDRESS=
USDT_TRC20_WALLET_ADDRESS=
TON_WALLET_ADDRESS=
```

### Optional Support And Notifications

```env
SUPPORT_TELEGRAM_USERNAME=
SUPPORT_CHANNEL_URL=
PUBLIC_CHANNEL_URL=
ADMIN_NOTIFICATION_CHAT_ID=
```

### Optional Developer API

```env
PUBLIC_API_BASE_URL=
API_KEY_PEPPER=
WEBHOOK_SIGNING_SECRET=
```

### Optional Deployment

```env
POSTGRES_DB=black16bot
POSTGRES_USER=black16bot
POSTGRES_PASSWORD=
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

## Proposed Project Structure

```txt
black16bot/
  manage.py
  requirements.txt
  .env
  .env.example
  README.md
  PROJECT_GUIDE.md

  config/
    __init__.py
    settings.py
    urls.py
    asgi.py
    wsgi.py

  accounts/
    __init__.py
    models.py
    admin.py
    services.py
    tests.py

  catalog/
    __init__.py
    models.py
    admin.py
    services.py
    tests.py

  orders/
    __init__.py
    models.py
    admin.py
    services.py
    tests.py

  wallet/
    __init__.py
    models.py
    admin.py
    services.py
    tests.py

  payments/
    __init__.py
    models.py
    admin.py
    services.py
    tests.py

  support/
    __init__.py
    models.py
    admin.py
    services.py

  broadcasts/
    __init__.py
    models.py
    admin.py
    services.py

  api_access/
    __init__.py
    models.py
    admin.py
    services.py

  bot/
    __init__.py
    keyboards.py
    messages.py
    handlers.py
    services.py
    management/
      __init__.py
      commands/
        __init__.py
        runbot.py

  locale/
    en.json
    ar.json
    fr.json
    es.json
    ru.json
    vi.json
    zh.json
    id.json
```

## Core Data Model

### TelegramUser

Fields:

- `telegram_id`
- `username`
- `first_name`
- `last_name`
- `language`
- `balance`
- `is_blocked`
- `joined_at`
- `last_active_at`

Notes:

- Balance must use `DecimalField`.
- Never use float values for money.
- Search by Telegram ID and username in Django Admin.

### Product

Fields:

- `name`
- `description`
- `category`
- `price`
- `is_active`
- `sort_order`
- `created_at`
- `updated_at`

Computed/admin display:

- Available stock count
- Sold stock count

### StockItem

Fields:

- `product`
- `secret_content`
- `status`
- `sold_to`
- `sold_order`
- `added_by`
- `created_at`
- `reserved_at`
- `sold_at`

Statuses:

- `available`
- `reserved`
- `sold`
- `refunded`
- `replaced`
- `disabled`

Important:

- Stock must be delivered exactly once.
- Purchase must reserve stock inside a database transaction.
- Use row locking when selecting stock for sale.

### Order

Fields:

- `user`
- `product`
- `stock_item`
- `price_paid`
- `status`
- `created_at`
- `refunded_at`
- `replaced_at`
- `admin_note`

Statuses:

- `completed`
- `refunded`
- `replaced`
- `cancelled`

### WalletTransaction

Fields:

- `user`
- `amount`
- `transaction_type`
- `status`
- `related_order`
- `related_payment`
- `created_by`
- `note`
- `created_at`

Types:

- `topup`
- `purchase`
- `refund`
- `admin_adjustment`

### PaymentRequest

Fields:

- `user`
- `amount`
- `method`
- `status`
- `proof_text`
- `proof_file_id`
- `admin_note`
- `approved_by`
- `created_at`
- `approved_at`
- `rejected_at`

Statuses:

- `pending`
- `approved`
- `rejected`

### Broadcast

Fields:

- `message`
- `target_language`
- `status`
- `sent_count`
- `failed_count`
- `created_by`
- `created_at`
- `sent_at`

### SupportTicket

Fields:

- `user`
- `message`
- `status`
- `admin_note`
- `created_at`
- `closed_at`

### DeveloperApiKey

Fields:

- `user`
- `key_hash`
- `key_prefix`
- `webhook_url`
- `is_active`
- `total_orders`
- `total_spend`
- `created_at`
- `last_used_at`

Important:

- Store only hashed API keys.
- Show the raw key only once at creation.

## Telegram Bot Commands

Implement these commands:

- `/start` - show main menu
- `/shop` - show product catalog
- `/topup` - show top-up methods
- `/orders` - show user orders
- `/profile` - show profile and balance
- `/language` - show language selector
- `/support` - show support options
- `/api` - show developer API dashboard

## Main Bot Menus

### Home Menu

Show:

- Welcome message
- Balance in USDT
- Buttons:
  - Shop
  - Buy Telegram Account
  - Top-up Wallet
  - My Profile
  - Support
  - Shopee or external marketplace button if needed
  - Earn
  - Channel

For MVP, `Buy Telegram Account`, `Shopee`, `Earn`, and `Channel` can be buttons
that open placeholder messages or external URLs.

### Shop Menu

Show active products with:

- Product name
- Price
- Available stock count
- Pagination
- Refresh button
- Sort button
- Back button

When user selects a product:

- Show product details
- Show price
- Show stock availability
- Show confirm purchase button

### Purchase Flow

Steps:

1. User selects product.
2. Bot shows confirmation.
3. User confirms.
4. System checks user balance.
5. System checks available stock.
6. System starts a database transaction.
7. System locks one available stock item.
8. System deducts user balance.
9. System creates wallet transaction.
10. System marks stock item as sold.
11. System creates order.
12. Bot sends delivered stock content to user.
13. Bot shows order ID.

Failure cases:

- Not enough balance.
- Product disabled.
- Out of stock.
- Stock was bought by someone else at the same time.
- Telegram delivery failed.

### Top-up Flow MVP

Steps:

1. User selects `/topup`.
2. Bot shows payment methods.
3. User selects method.
4. Bot asks for amount.
5. Bot shows payment instructions.
6. User submits transaction ID, note, screenshot, or proof.
7. System creates `PaymentRequest`.
8. Admin approves/rejects in Django Admin.
9. If approved, user balance increases.
10. Bot notifies user.

Payment methods to list:

- Binance Pay
- Bybit Pay
- CryptoBot
- USDT BEP-20
- USDT TRC-20
- TON
- TRON
- Others

For MVP, all are manual approval methods.

### Profile

Show:

- Telegram ID
- Username
- Balance
- Language
- Join date
- Notifications status

Buttons:

- Notifications
- My Orders
- Developer API
- Language
- Back

### Orders

Show:

- Recent orders
- Order ID
- Product
- Price
- Status
- Created date

If there are no orders, show a clear empty state.

### Language

Supported languages:

- English
- Vietnamese
- Chinese
- Indonesian
- Spanish
- Russian
- Arabic

MVP can implement English only internally, but should store language selection
and make the structure ready for translations.

### Support

Show:

- Short support message
- Live Support button
- Contact Admin button
- Back button

Use URLs from `.env`.

### Developer API

MVP can show a basic placeholder dashboard.

Fields to support later:

- API status
- Active API key
- Webhook URL
- API orders
- API spend
- Revoke key
- Set webhook URL
- API documentation link

## Django Admin Requirements

### Global Admin Rules

- Add search fields where possible.
- Add list filters for status/date/product/language.
- Add read-only fields for generated IDs and timestamps.
- Add clear admin actions for common operations.
- Avoid exposing `secret_content` in list views.

### Product Admin

Features:

- List name, price, active status, available stock count.
- Filter active/inactive products.
- Search by name.
- Inline stock items or link to stock list.

### Stock Admin

Features:

- Add stock item manually.
- Bulk upload stock items.
- Filter by product and status.
- Search by content only if necessary.
- Hide full secret content from list page.

Bulk upload format:

```txt
email1@example.com:password1
email2@example.com:password2
email3@example.com:password3
```

### Payment Request Admin

Actions:

- Approve selected payment requests.
- Reject selected payment requests.

On approval:

- Create wallet transaction.
- Increase user balance.
- Mark payment approved.
- Notify user through Telegram if possible.

### Order Admin

Actions:

- Refund order.
- Mark order replaced.
- Send replacement stock.

On refund:

- Increase user balance by order price.
- Create wallet transaction.
- Mark order refunded.
- Do not automatically make sold stock available again unless admin chooses it.

### Broadcast Admin

Actions:

- Send broadcast to selected target.

Rules:

- MVP can send synchronously for small user counts.
- For larger user counts, use Celery later.
- Store sent and failed counts.

## Milestones And Tasks

## Milestone 1 - Project Foundation

Goal: Create a working Django project connected to PostgreSQL.

Tasks:

- Create Django project and apps.
- Add `.env` loading.
- Add `.env.example`.
- Configure PostgreSQL via `DATABASE_URL`.
- Add local development settings.
- Add Django Admin.
- Create initial superuser.
- Add basic README commands.

Acceptance checks:

- `python manage.py check` passes.
- `python manage.py migrate` works.
- Django Admin opens locally.
- Superuser can log in.

## Milestone 2 - Core Models

Goal: Add database structure for users, catalog, stock, orders, wallet, and payments.

Tasks:

- Implement `TelegramUser`.
- Implement `Product`.
- Implement `StockItem`.
- Implement `Order`.
- Implement `WalletTransaction`.
- Implement `PaymentRequest`.
- Add migrations.
- Register models in Django Admin.
- Add search, filters, and read-only fields.

Acceptance checks:

- Migrations apply cleanly.
- Admin can create products.
- Admin can create stock items.
- Admin can create/edit users.

## Milestone 3 - Bot Worker

Goal: Run Telegram bot as a Django management command.

Tasks:

- Create `bot/management/commands/runbot.py`.
- Load `TELEGRAM_BOT_TOKEN` from `.env`.
- Implement `/start`.
- Create reusable inline keyboards.
- Create or update `TelegramUser` on interaction.
- Add admin ID parser from `TELEGRAM_ADMIN_IDS`.

Acceptance checks:

- `python manage.py runbot` starts.
- Sending `/start` to the bot creates a user in the database.
- Bot shows the main menu.

## Milestone 4 - Profile, Language, And Support

Goal: Implement simple non-purchase user flows.

Tasks:

- Implement `/profile`.
- Implement `/language`.
- Save language selection.
- Implement `/support`.
- Add support URL buttons from `.env`.
- Implement back navigation.

Acceptance checks:

- User can open profile.
- User can change language.
- User can open support buttons.
- No crashes when optional support URLs are missing.

## Milestone 5 - Product Catalog

Goal: Implement the `/shop` product list.

Tasks:

- Query active products.
- Show name, price, and stock count.
- Add pagination.
- Add refresh button.
- Add sort button.
- Add product detail screen.
- Add back navigation.

Acceptance checks:

- Products created in Django Admin appear in Telegram.
- Inactive products do not appear.
- Stock count matches available stock items.
- Pagination works.

## Milestone 6 - Purchase And Stock Delivery

Goal: Allow users to buy products and receive stock safely.

Tasks:

- Add purchase confirmation screen.
- Check user balance.
- Check stock availability.
- Implement atomic purchase service.
- Lock stock row during purchase.
- Deduct balance.
- Create wallet transaction.
- Create order.
- Mark stock sold.
- Deliver stock content to user.
- Show clear errors for insufficient balance or out-of-stock.

Acceptance checks:

- User with enough balance can buy a product.
- User receives exactly one stock item.
- Balance decreases correctly.
- Order appears in Django Admin.
- Stock item becomes sold.
- Two users cannot buy the same stock item.

## Milestone 7 - Orders

Goal: Show users their order history.

Tasks:

- Implement `/orders`.
- Show recent orders.
- Add pagination if needed.
- Add empty state.

Acceptance checks:

- New orders appear in `/orders`.
- Empty users see a no-orders message.

## Milestone 8 - Manual Top-up

Goal: Let users request wallet balance top-ups.

Tasks:

- Implement `/topup`.
- Show payment methods.
- Ask for amount.
- Ask for payment proof.
- Create pending `PaymentRequest`.
- Add Django Admin approve/reject actions.
- On approval, create wallet transaction and increase balance.
- Notify user of approval/rejection.

Acceptance checks:

- User can create a pending payment request.
- Admin can approve it.
- User balance increases.
- User receives a notification.
- Rejected payment does not change balance.

## Milestone 9 - Admin Operations

Goal: Make the bot manageable from Django Admin.

Tasks:

- Add bulk stock upload.
- Add refund order action.
- Add replace stock action.
- Add payment approval action.
- Add broadcast action.
- Add admin notes on orders/payments.

Acceptance checks:

- Admin can bulk add stock.
- Admin can refund an order.
- Admin can approve/reject top-ups.
- Admin can send a broadcast.

## Milestone 10 - Developer API Placeholder

Goal: Prepare the developer API feature without overbuilding it.

Tasks:

- Add `DeveloperApiKey` model.
- Add `/api` Telegram screen.
- Show API status and placeholder stats.
- Add create/revoke key service.
- Store hashed keys only.

Acceptance checks:

- User can open `/api`.
- API key can be created/revoked.
- Raw key is not stored in the database.

## Milestone 11 - Security And Reliability

Goal: Harden the MVP before real usage.

Tasks:

- Add database transaction tests for purchase.
- Add admin permission checks.
- Add bot rate limiting.
- Add error logging.
- Add backup instructions.
- Add `ALLOWED_HOSTS` and production security settings.
- Ensure all secrets come from `.env`.

Acceptance checks:

- No tokens are committed.
- Purchases are atomic.
- Admin actions cannot be used by normal users.
- Production settings are documented.

## Milestone 12 - Deployment

Goal: Run the full app on a VPS.

Tasks:

- Add `Dockerfile`.
- Add `docker-compose.yml`.
- Add services:
  - `web`
  - `bot`
  - `db`
- Add volume for PostgreSQL data.
- Add static file handling.
- Configure domain and HTTPS.
- Run migrations in production.
- Create production superuser.

Acceptance checks:

- Django Admin is accessible over HTTPS.
- Bot responds to `/start`.
- Database persists after container restart.
- Admin can add product and stock.
- Test user can purchase a product.

## Later Improvements

Do these only after MVP works:

- Automatic CryptoBot payments.
- Binance Pay integration.
- Bybit Pay integration.
- USDT TRC-20/BEP-20 transaction verification.
- Referral/earn system.
- Full developer API ordering.
- Webhook delivery to API users.
- Celery + Redis for broadcasts and background jobs.
- Custom admin dashboard.
- Sales analytics and charts.

## Initial Build Order For AI Agent

When an AI agent starts implementation, follow this exact order:

1. Create Django project and app structure.
2. Add `.env.example`.
3. Add PostgreSQL settings.
4. Implement models and migrations.
5. Register Django Admin pages.
6. Implement bot management command.
7. Implement `/start`, `/profile`, `/shop`.
8. Implement purchase service with transactions.
9. Implement `/topup` and payment admin approval.
10. Add tests for purchase and payment approval.
11. Add Docker Compose.
12. Run full local verification.

## Definition Of Done For MVP

The MVP is done when:

- Admin can log into Django Admin.
- Admin can add products and stock.
- User can start the bot.
- User can see products.
- User can top up manually.
- Admin can approve top-up.
- User can buy a product.
- User receives the stock content.
- User can see order history.
- Admin can see users, orders, payments, and stock.
- Secrets are stored only in `.env`.
- PostgreSQL is used as the database.

