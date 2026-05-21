# Bun AI Store Bot — Feature Audit & Build Report

Prepared for: **mg**  
Goal: Recreate a Telegram bot with similar capabilities and cleaner architecture.

---

## 1) What I analyzed (live walkthrough)

I walked through the bot flows directly inside Telegram Web and tested these paths:

1. `/start`
2. `Shop` product listing
3. Product detail + quantity keypad + note view
4. `Top-up Wallet`
5. One payment method flow (`USDT BEP-20`)
6. `Buy Telegram Account` country picker + purchase confirmation step
7. `My Profile`
8. `Support`
9. `Developer API` dashboard (inside profile)
10. `Language` selector
11. `Earn` referral program
12. `Shopee` (automated support chat entry)
13. `Channel` (channel preview/join route)

I stopped before any irreversible action (no payment sent, no purchase confirmed).

---

## 2) Feature inventory (what the bot has)

## A. Core storefront
- Welcome screen with current wallet balance.
- Main menu buttons:
  - Shop
  - Buy Telegram Account
  - Top-up Wallet
  - My Profile
  - Support
  - Shopee
  - Earn
  - Channel
- Also supports command usage (`/start`, `/shop`, `/topup`, `/orders`, `/profile`, `/language`, `/support`, `/api`).

## B. Product catalog (`Shop`)
- Paginated catalog (example seen: page indicator like `1/3`).
- Sorting control (`Sort: All`).
- Refresh control.
- Product cards include:
  - Product name
  - Price (USDT)
  - Live stock count (including ∞ stock on some items)
- Mixed digital goods inventory (AI accounts, VPN, productivity tools, etc.).

## C. Product checkout UX
- Clicking a product opens purchase composition panel with:
  - Quantity field (`Qty: 0`)
  - Numeric keypad (0–9) + delete
  - `Top Up Wallet`
  - `Share Link`
  - `View Note`
  - `Back`
- `View Note` shows admin note/details for selected product (e.g., what account includes).

## D. Wallet top-up
- Multi-method top-up menu (observed):
  - Binance Pay
  - Bybit
  - CryptoBot
  - USDT (BEP-20)
  - TON
  - Tron
  - Others
- Method flow (observed on BEP-20):
  - Shows deposit address
  - Asks user to send funds
  - Requests TXID/transaction hash
  - Has cancel action
  - Includes rules for accepted precision and hash format guidance

## E. Telegram account market flow (`Buy Telegram Account`)
- Country-based product catalog with country + price.
- Large paginated list + search by country.
- Selecting country opens confirm screen with:
  - Country code
  - Stock available
  - Price
  - Product disclaimer/warranty note
  - Confirm / Cancel actions

## F. Orders/Profile
- `/orders`: shows empty state when no orders.
- `/profile`: shows
  - user ID
  - wallet balance
  - language
  - join date
- Profile sub-menu includes:
  - Notifications
  - My Orders
  - Developer API
  - Language
  - Back

## G. Language localization
- In-chat language selection with options observed:
  - English
  - Vietnamese
  - Chinese
  - Indonesian
  - Spanish
  - Russian
  - Arabic

## H. Support system
- Support panel text + action buttons:
  - Live Support
  - Contact Admin
- Separate `Shopee` entry appears to open a scripted support assistant chat (“automated support assistant”).

## I. Referral / affiliate (`Earn`)
- Referral dashboard with counters:
  - Referred (24h)
  - Referred (7d)
  - Referred (total)
  - Total earned
  - Available
  - Transferred
  - Withdrawn
- Includes unique referral link and copy button.
- Incentive text indicates percentage-based reward from referred user top-ups.

## J. Channel growth funnel (`Channel`)
- Channel promo panel with:
  - Channel title preview
  - Join button
  - Back action
- Used as marketing/announcement funnel.

## K. Operational broadcasting
- Bot posts frequent stock update messages (“X new stock added for Y”).
- Admin alert broadcasts observed (refund notices, urgent updates, support delays).

## L. API for developers (advanced differentiator)
- In-bot “Developer API Dashboard” visible in profile.
- Fields observed:
  - API status
  - Active API key (sensitive)
  - Webhook status
  - API order count
  - API spend
- Actions observed:
  - Set Webhook URL
  - Revoke API Key
  - View API Documentation

---

## 3) UX pattern summary (the design pattern you should copy)

1. **Main menu as navigation hub** (button-first UX).
2. **Stateful mini-flows** (shop → item → qty → pay).
3. **In-chat dashboards** (profile, referral, API metrics).
4. **Operational trust layer** (alerts, support shortcuts, channel, refund notices).
5. **Hybrid audience model**:
   - End customers
   - Power users/developers (API access)

---

## 4) Scenarios (ready to give your AI agent/dev team)

Use these as implementation scenarios (user stories + acceptance criteria).

## Scenario 1 — Onboarding & Home
**As a user**, I can start the bot and immediately see my wallet balance and key actions.
- Trigger: `/start`
- Output: welcome + menu buttons.
- Acceptance:
  - New and returning users get same consistent menu.
  - Balance fetched from DB in <300ms median.

## Scenario 2 — Browse products
**As a user**, I can browse products with stock and price.
- Trigger: Shop button or `/shop`
- Acceptance:
  - Pagination works.
  - Sort/filter options work.
  - Product stock updates in near real-time.

## Scenario 3 — Product details and quantity selection
**As a user**, I can pick quantity via inline keypad before checkout.
- Acceptance:
  - Qty cannot exceed stock.
  - Qty cannot be <1 when confirming purchase.
  - Unit price, subtotal, and fees (if any) shown clearly.

## Scenario 4 — Read product notes
**As a user**, I can view product-specific instructions/terms before buying.
- Acceptance:
  - Note supports markdown formatting.
  - Notes managed per product in admin panel.

## Scenario 5 — Top up wallet via crypto method
**As a user**, I can top up with multiple payment rails.
- Acceptance:
  - Bot generates or displays correct destination.
  - User submits TXID/hash.
  - Backend verifies chain + amount + confirmations.
  - Credit is idempotent (no double-credit).

## Scenario 6 — Buy Telegram account by country
**As a user**, I can select country and purchase account stock.
- Acceptance:
  - Country search + pagination.
  - Confirm modal with disclaimer.
  - Stock decremented atomically at purchase success.

## Scenario 7 — Orders and delivery retrieval
**As a user**, I can see my order history and delivered credentials/assets.
- Acceptance:
  - Orders list with status (pending/paid/delivered/refunded).
  - Secure reveal flow for sensitive delivery data.

## Scenario 8 — Profile and settings
**As a user**, I can view profile and change language/notification prefs.
- Acceptance:
  - Language switch applies immediately.
  - Notification flags persist in user settings.

## Scenario 9 — Support escalation
**As a user**, I can reach live support quickly.
- Acceptance:
  - Creates support ticket with user ID + context.
  - Admin receives ticket in dashboard/Telegram group.

## Scenario 10 — Referral program
**As a user**, I can share referral link and track earnings.
- Acceptance:
  - Unique referral code per user.
  - Attribution survives deep links and first purchase window rules.
  - Earnings ledger is auditable.

## Scenario 11 — Broadcast operations
**As admin**, I can push stock updates and urgent alerts.
- Acceptance:
  - Targeted broadcast segments (all users / active users / language segment).
  - Rate-limited sends + delivery stats.

## Scenario 12 — Developer API self-service
**As a power user**, I can get API key, set webhook, revoke key, and view usage.
- Acceptance:
  - API keys hashed at rest.
  - Key revocation immediate.
  - Signed webhook events with retry policy.

---

## 5) Recommended architecture to build your version

## Backend
- Node.js (NestJS or Fastify) or Python (FastAPI)
- PostgreSQL for core data
- Redis for session state + callback flow state
- Queue (BullMQ/RabbitMQ) for async jobs (verification, broadcasts)

## Telegram layer
- Telegraf (Node) or aiogram (Python)
- Strong callback data schema: `action:entity:id:page`
- Central flow/state manager for inline keyboards

## Payments
- Chain-specific verifiers (BSC/TRON/TON)
- Confirmation policy per chain
- Double-spend/duplicate TXID protection

## Admin panel
- Inventory manager
- Product notes editor
- Order management & refund panel
- Broadcast composer
- Support ticket console

## API platform
- API keys + scopes
- Usage meters
- Webhook subscriptions + signature validation
- Docs endpoint (OpenAPI)

---

## 6) Data model (minimum)

- `users(id, tg_id, language, created_at, referral_code, referred_by)`
- `wallets(user_id, balance)`
- `wallet_transactions(id, user_id, type, amount, status, tx_hash, chain, meta)`
- `products(id, category, name, price, stock, is_active, note_md)`
- `orders(id, user_id, product_id, qty, unit_price, total, status, delivered_payload_ref)`
- `support_tickets(id, user_id, status, subject, payload)`
- `referral_ledger(id, referrer_user_id, referee_user_id, source_txn_id, commission_amount)`
- `api_clients(id, user_id, api_key_hash, status, webhook_url, created_at)`
- `api_usage(id, api_client_id, endpoint, units, created_at)`

---

## 7) Guardrails you should add (important)

- Fraud checks on top-up and order bursts.
- Admin action audit log.
- Secure storage for delivered credentials/secrets.
- Auto-redaction in logs for sensitive fields.
- Rate limits per user for commands and purchase attempts.
- Refund workflow with immutable ledger entries.

---

## 8) What to improve vs original (to beat it)

1. Cleaner command help (`/help`) with clear command map.
2. Better failed-flow recovery (always show “Back to Home”).
3. Explicit pending-payment tracker with timeout state.
4. Structured support tickets instead of only free-text.
5. Better analytics dashboard (conversion, churn, top products, fraud signals).
6. Stronger privacy mode for delivered account data.

---

## 9) Build phases (practical roadmap)

## Phase 1 (MVP, 1–2 weeks)
- Start/menu/profile/language
- Product catalog + buy flow
- Manual top-up verification
- Orders + simple support

## Phase 2 (2–4 weeks)
- Automated chain verification
- Referral system
- Broadcast tools
- Country-based Telegram account marketplace

## Phase 3 (4–6 weeks)
- Developer API + webhook platform
- Full admin analytics
- Risk/fraud automation

---

## 10) Deliverable summary

You should build this as a **Telegram commerce OS** with:
- Wallet + payment rails
- Catalog + inventory + checkout
- Referral engine
- Support + broadcast operations
- Developer API self-service

That combination is the core differentiator of Bun AI Store.
