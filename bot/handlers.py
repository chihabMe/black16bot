from decimal import Decimal, InvalidOperation

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.paginator import EmptyPage, Paginator
from django.db.models import Sum

from accounts.models import TelegramUser
from accounts.models import ReferralLedger
from accounts.services import apply_referral_code, upsert_telegram_user
from api_access.models import DeveloperApiKey
from api_access.services import revoke_user_api_keys
from api_access.webhooks import UnsafeWebhookUrl, validate_webhook_url
from bot.keyboards import (
    back_menu,
    api_menu,
    language_menu,
    main_menu,
    notifications_menu,
    orders_menu,
    pending_payments_menu,
    product_detail_menu,
    product_list_menu,
    topup_methods_menu,
)
from bot.rate_limit import is_rate_limited
from catalog.models import Product
from orders.models import Order
from orders.services import InsufficientBalance, OutOfStock, ProductUnavailable, purchase_product
from payments.models import PaymentRequest
from payments.binance import BinanceDepositError, verify_binance_deposit
from payments.services import PaymentApprovalError, PaymentRequestError, cancel_payment_request, create_payment_request
from support.services import create_support_ticket
from security.crypto import decrypt_text


PAGE_SIZE = 8


def get_user(update) -> TelegramUser:
    return upsert_telegram_user(update.effective_user, settings.DEFAULT_BOT_LANGUAGE)


async def start(update, context):
    user = await sync_to_async(get_user)(update)
    if update.message and getattr(context, "args", None):
        await sync_to_async(apply_referral_code)(user=user, referral_code=context.args[0])
    text = (
        "👋 Welcome to Black16 Store\n\n"
        f"💰 Balance: {user.balance} USDT\n"
        "🛒 Choose a product, top up your wallet, or check your orders."
    )
    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu())
    else:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu())


async def show_shop(update, context, page: int = 1, product_type: str = ""):
    if await limited(update, "shop"):
        return

    def load_products():
        queryset = Product.objects.filter(is_active=True).with_stock_counts().order_by("sort_order", "name")
        if product_type:
            queryset = queryset.filter(product_type=product_type)
        paginator = Paginator(queryset, PAGE_SIZE)
        try:
            product_page = paginator.page(page)
        except EmptyPage:
            product_page = paginator.page(1)
        return list(product_page.object_list), product_page.number, product_page.has_next()

    products, current_page, has_next = await sync_to_async(load_products)()
    text = "🛒 Available products" if products else "No products are available right now."
    await send_or_edit(update, text, product_list_menu(products, current_page, has_next))


async def show_product(update, context, product_id: int):
    def load_product():
        return Product.objects.with_stock_counts().get(pk=product_id, is_active=True)

    try:
        product = await sync_to_async(load_product)()
    except Product.DoesNotExist:
        await send_or_edit(update, "This product is not available.", back_menu("shop"))
        return

    stock = getattr(product, "available_stock_count", product.available_stock_count)
    text = (
        f"🛍️ {product.name}\n\n"
        f"{product.description or 'Digital product'}\n\n"
        f"💵 Price: {product.price} USDT\n"
        f"📦 Stock: {stock}"
    )
    if product.product_type == Product.ProductType.TELEGRAM_ACCOUNT:
        text += f"\n🌍 Country: {product.country_name or product.country_code or '-'}"
    await send_or_edit(update, text, product_detail_menu(product.pk))


async def show_product_note(update, context, product_id: int):
    def load_product():
        return Product.objects.get(pk=product_id, is_active=True)

    try:
        product = await sync_to_async(load_product)()
    except Product.DoesNotExist:
        await send_or_edit(update, "This product is not available.", back_menu("shop"))
        return
    note = product.note_md or product.warranty_note or "No note is available for this product."
    await send_or_edit(update, f"{product.name}\n\n{note}", product_detail_menu(product.pk))


async def share_product(update, context, product_id: int):
    bot_username = context.bot.username or "your_bot"
    await send_or_edit(
        update,
        f"🔗 Share this product:\nhttps://t.me/{bot_username}?start=product_{product_id}",
        product_detail_menu(product_id),
    )


async def buy_product(update, context, product_id: int, quantity: int = 1):
    if await limited(update, "buy", limit=5):
        return

    user = await sync_to_async(get_user)(update)

    def buy():
        return purchase_product(user_id=user.pk, product_id=product_id, quantity=quantity)

    try:
        result = await sync_to_async(buy)()
    except ProductUnavailable:
        await send_or_edit(update, "This product is currently unavailable.", back_menu("shop"))
        return
    except InsufficientBalance:
        await send_or_edit(update, "Insufficient balance. Please top up your wallet.", back_menu("topup"))
        return
    except OutOfStock:
        await send_or_edit(update, "This product is out of stock.", back_menu("shop"))
        return

    text = (
        f"✅ Order #{result.order.pk} completed\n\n"
        f"🛍️ Product: {result.order.product.name}\n"
        f"📦 Quantity: {result.order.quantity}\n"
        f"💵 Total: {result.order.price_paid} USDT\n\n"
        f"🔐 Your item(s):\n{decrypt_text(result.order.delivered_payload)}"
    )
    await send_or_edit(update, text, back_menu("orders"))


async def show_profile(update, context):
    user = await sync_to_async(get_user)(update)
    text = (
        "👤 Profile\n\n"
        f"ID: {user.telegram_id}\n"
        f"Username: @{user.username or '-'}\n"
        f"Balance: {user.balance} USDT\n"
        f"Notifications: {'on' if user.notifications_enabled else 'off'}\n"
        f"Language: {user.language}\n"
        f"Joined: {user.joined_at:%Y-%m-%d}"
    )
    await send_or_edit(update, text, back_menu("home"))


async def show_orders(update, context):
    user = await sync_to_async(get_user)(update)

    def load_orders():
        return list(Order.objects.filter(user=user).select_related("product").order_by("-created_at")[:10])

    orders = await sync_to_async(load_orders)()
    if not orders:
        await send_or_edit(update, "📭 You have no orders yet.", back_menu("home"))
        return
    await send_or_edit(update, "📦 Your recent orders:", orders_menu(orders))


async def show_order_detail(update, context, order_id: int):
    user = await sync_to_async(get_user)(update)

    def load_order():
        return (
            Order.objects.select_related("product", "stock_item")
            .filter(user=user, pk=order_id)
            .first()
        )

    order = await sync_to_async(load_order)()
    if not order:
        await send_or_edit(update, "Order not found.", back_menu("orders"))
        return

    text = (
        f"📦 Order #{order.pk}\n\n"
        f"🛍️ Product: {order.product.name}\n"
        f"💵 Price: {order.price_paid} USDT\n"
        f"📦 Quantity: {order.quantity}\n"
        f"Status: {order.status}\n"
        f"Created: {order.created_at:%Y-%m-%d %H:%M}\n\n"
        f"🔐 Delivered item:\n{decrypt_text(order.delivered_payload) if order.delivered_payload else decrypt_text(order.stock_item.secret_content)}"
    )
    await send_or_edit(update, text, back_menu("orders"))


async def show_payments(update, context):
    user = await sync_to_async(get_user)(update)

    def load_payments():
        return list(
            PaymentRequest.objects.filter(user=user, status=PaymentRequest.Status.PENDING).order_by("-created_at")[:10]
        )

    payments = await sync_to_async(load_payments)()
    if not payments:
        await send_or_edit(update, "You have no pending payment requests.", back_menu("home"))
        return
    lines = ["Pending payment requests:"]
    for payment in payments:
        expires = payment.expires_at.strftime("%Y-%m-%d %H:%M") if payment.expires_at else "-"
        lines.append(f"#{payment.pk} - {payment.amount} USDT - {payment.get_method_display()} - expires {expires}")
    await send_or_edit(update, "\n".join(lines), pending_payments_menu(payments))


async def cancel_payment(update, context, payment_id: int):
    user = await sync_to_async(get_user)(update)
    try:
        await sync_to_async(cancel_payment_request)(payment_id=payment_id, user_id=user.pk)
    except (PaymentApprovalError, PaymentRequest.DoesNotExist) as exc:
        await send_or_edit(update, f"Could not cancel payment request: {exc}", back_menu("payments"))
        return
    await send_or_edit(update, f"Payment request #{payment_id} cancelled.", back_menu("payments"))


async def show_topup(update, context):
    await send_or_edit(update, "💳 Top up wallet\n\nSelect a payment method:", topup_methods_menu())


async def create_topup_request(update, context, method: str):
    user = await sync_to_async(get_user)(update)
    amount_text = " ".join(context.args) if getattr(context, "args", None) else ""
    try:
        amount = Decimal(amount_text)
    except (InvalidOperation, ValueError):
        await send_or_edit(
            update,
            "Manual top-up selected.\n\nUse:\n/topup_amount 10 cryptobot transaction-id-or-note",
            back_menu("topup"),
        )
        return

    def create_payment():
        return create_payment_request(user_id=user.pk, amount=amount, method=method)

    try:
        payment = await sync_to_async(create_payment)()
    except PaymentRequestError as exc:
        await send_or_edit(update, str(exc), back_menu("topup"))
        return
    await send_or_edit(update, f"Payment request #{payment.pk} created. Admin will review it.", back_menu("home"))


async def topup_amount(update, context):
    if await limited(update, "topup", limit=6):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Use:\n/topup_amount 10 cryptobot transaction-id-or-note\n\n"
            "Methods: binance_pay, bybit_pay, cryptobot, usdt_bep20, usdt_trc20, ton, tron, other"
        )
        return

    await create_topup_from_parts(update, context.args[0], context.args[1], " ".join(context.args[2:]).strip())


async def binance_topup(update, context):
    if await limited(update, "binance_topup", limit=6):
        return

    if len(context.args) < 2:
        await update.message.reply_text(
            "Use:\n/binance_topup 10 txid [network]\n\n"
            "Example:\n/binance_topup 10 0xabc123 BSC"
        )
        return

    user = await sync_to_async(get_user)(update)
    try:
        amount = Decimal(context.args[0])
    except InvalidOperation:
        await update.message.reply_text("Amount must be a number, for example: 10")
        return

    txid = context.args[1].strip()
    network = context.args[2].strip() if len(context.args) >= 3 else ""

    def verify():
        return verify_binance_deposit(
            user_id=user.pk,
            amount=amount,
            txid=txid,
            coin="USDT",
            network=network,
        )

    try:
        verified = await sync_to_async(verify)()
    except BinanceDepositError as exc:
        await update.message.reply_text(f"Binance top-up was not verified: {exc}")
        return

    await update.message.reply_text(
        f"Binance top-up verified.\n"
        f"Credited: {verified.payment_request.amount} USDT\n"
        f"Deposit amount found: {verified.amount} {verified.coin}"
    )


async def topup_photo_proof(update, context):
    caption = update.message.caption or ""
    if not caption.startswith("/topup_amount"):
        return
    parts = caption.split()
    if len(parts) < 3:
        await update.message.reply_text(
            "Use the photo caption:\n/topup_amount 10 cryptobot transaction-id-or-note"
        )
        return
    file_id = update.message.photo[-1].file_id if update.message.photo else ""
    proof = " ".join(parts[3:]).strip()
    await create_topup_from_parts(update, parts[1], parts[2], proof, proof_file_id=file_id)


async def create_topup_from_parts(update, amount_text: str, method: str, proof: str, proof_file_id: str = ""):
    user = await sync_to_async(get_user)(update)
    try:
        amount = Decimal(amount_text)
    except InvalidOperation:
        await update.message.reply_text("Amount must be a number, for example: 10")
        return

    method = method.strip().lower()

    def create_payment():
        return create_payment_request(
            user_id=user.pk,
            amount=amount,
            method=method,
            proof_text=proof,
            proof_file_id=proof_file_id,
        )

    try:
        payment = await sync_to_async(create_payment)()
    except PaymentRequestError as exc:
        await update.message.reply_text(str(exc))
        return

    await update.message.reply_text(
        f"Payment request #{payment.pk} created for {payment.amount} USDT.\n"
        "An admin will approve it after checking your payment."
    )


async def admin_stats(update, context):
    if update.effective_user.id not in settings.TELEGRAM_ADMIN_IDS:
        await update.message.reply_text("This command is admin-only.")
        return

    def load_stats():
        return {
            "users": TelegramUser.objects.count(),
            "products": Product.objects.count(),
            "orders": Order.objects.count(),
            "pending_payments": PaymentRequest.objects.filter(status=PaymentRequest.Status.PENDING).count(),
        }

    stats = await sync_to_async(load_stats)()
    await update.message.reply_text(
        "📊 Admin stats\n\n"
        f"Users: {stats['users']}\n"
        f"Products: {stats['products']}\n"
        f"Orders: {stats['orders']}\n"
        f"Pending payments: {stats['pending_payments']}"
    )


async def show_language(update, context):
    await send_or_edit(update, "🌐 Please select your language:", language_menu())


async def set_language(update, context, language: str):
    user = await sync_to_async(get_user)(update)
    user.language = language
    await sync_to_async(user.save)(update_fields=["language"])
    await send_or_edit(update, "Language updated.", back_menu("home"))


async def show_notifications(update, context):
    user = await sync_to_async(get_user)(update)
    status = "on" if user.notifications_enabled else "off"
    text = (
        "🔔 Notifications\n\n"
        f"Status: {status}\n\n"
        "When enabled, you will receive updates for new products and fresh stock."
    )
    await send_or_edit(update, text, notifications_menu(user.notifications_enabled))


async def toggle_notifications(update, context):
    user = await sync_to_async(get_user)(update)
    user.notifications_enabled = not user.notifications_enabled
    await sync_to_async(user.save)(update_fields=["notifications_enabled"])
    status = "enabled" if user.notifications_enabled else "disabled"
    await send_or_edit(update, f"🔔 Notifications {status}.", notifications_menu(user.notifications_enabled))


async def show_support(update, context):
    text = (
        "🛟 Support\n\n"
        "If you have an issue, use:\n"
        "/support_ticket your message here"
    )
    await send_or_edit(update, text, back_menu("home"))


async def show_referral(update, context):
    user = await sync_to_async(get_user)(update)

    def load_stats():
        earnings = ReferralLedger.objects.filter(referrer=user)
        return {
            "total_referred": user.referrals.count(),
            "total_earned": earnings.aggregate(total=Sum("commission_amount"))["total"] or 0,
            "available": earnings.filter(status=ReferralLedger.Status.AVAILABLE).aggregate(total=Sum("commission_amount"))["total"] or 0,
        }

    stats = await sync_to_async(load_stats)()
    bot_username = context.bot.username or "your_bot"
    link = f"https://t.me/{bot_username}?start={user.referral_code}"
    text = (
        "🎁 Earn / Referral\n\n"
        f"Referred total: {stats['total_referred']}\n"
        f"Total earned: {stats['total_earned']} USDT\n"
        f"Available: {stats['available']} USDT\n\n"
        f"Your referral link:\n{link}"
    )
    await send_or_edit(update, text, back_menu("home"))


async def show_telegram_accounts(update, context):
    await show_shop(update, context, product_type=Product.ProductType.TELEGRAM_ACCOUNT)


async def help_command(update, context):
    await update.message.reply_text(
        "🤖 Commands\n\n"
        "/start - main menu\n"
        "/shop - product catalog\n"
        "/telegram_accounts - country account marketplace\n"
        "/orders - order history\n"
        "/payments - pending top-ups\n"
        "/topup - top-up methods\n"
        "/topup_amount 10 method proof - manual top-up request\n"
        "/binance_topup 10 txid [network] - auto Binance deposit check\n"
        "/referral - referral dashboard\n"
        "/notifications - product and stock alerts\n"
        "/support_ticket message - create support ticket\n"
        "/language - change language"
    )


async def support_ticket(update, context):
    user = await sync_to_async(get_user)(update)
    message = " ".join(context.args).strip()
    if not message:
        await update.message.reply_text("Use:\n/support_ticket describe your issue")
        return

    ticket = await sync_to_async(create_support_ticket)(user_id=user.pk, message=message)
    await update.message.reply_text(f"Support ticket #{ticket.pk} created. Admin will review it.")


async def show_api(update, context):
    if not settings.DEVELOPER_API_ENABLED:
        await send_or_edit(update, "🔌 Developer API is disabled for now.", back_menu("home"))
        return
    user = await sync_to_async(get_user)(update)

    def load_key():
        return DeveloperApiKey.objects.filter(user=user, is_active=True).first()

    api_key = await sync_to_async(load_key)()
    status = "Online"
    key = api_key.key_prefix + "..." if api_key else "Not created"
    webhook = api_key.webhook_url if api_key and api_key.webhook_url else "Not configured"
    api_orders = api_key.total_orders if api_key else 0
    api_spend = api_key.total_spend if api_key else 0
    text = (
        "Developer API Dashboard\n\n"
        f"API Status: {status}\n"
        f"Active API Key: {key}\n"
        f"Webhook: {webhook}\n"
        f"API Orders: {api_orders}\n"
        f"API Spend: {api_spend} USDT\n\n"
        "Use /api_webhook URL to set a webhook.\n"
        "Use /api_docs for API docs."
    )
    await send_or_edit(update, text, api_menu(bool(api_key)))


async def create_api_key(update, context):
    if not settings.DEVELOPER_API_ENABLED:
        await send_or_edit(update, "🔌 Developer API is disabled for now.", back_menu("home"))
        return
    user = await sync_to_async(get_user)(update)

    def create_key():
        raw_key, _ = DeveloperApiKey.create_for_user(user)
        return raw_key

    raw_key = await sync_to_async(create_key)()
    await send_or_edit(
        update,
        "Your API key was created. Save it now; it will not be shown again.\n\n"
        f"{raw_key}",
        api_menu(True),
    )


async def revoke_api_key(update, context):
    if not settings.DEVELOPER_API_ENABLED:
        await send_or_edit(update, "🔌 Developer API is disabled for now.", back_menu("home"))
        return
    user = await sync_to_async(get_user)(update)
    count = await sync_to_async(revoke_user_api_keys)(user_id=user.pk)
    await send_or_edit(update, f"Revoked {count} active API key(s).", api_menu(False))


async def set_api_webhook(update, context):
    if not settings.DEVELOPER_API_ENABLED:
        await update.message.reply_text("Developer API is disabled for now.")
        return
    user = await sync_to_async(get_user)(update)
    if not context.args:
        await update.message.reply_text("Use:\n/api_webhook https://example.com/webhook")
        return
    webhook_url = context.args[0].strip()
    try:
        await sync_to_async(validate_webhook_url)(webhook_url)
    except UnsafeWebhookUrl as exc:
        await update.message.reply_text(f"Invalid webhook URL: {exc}")
        return

    def update_key():
        api_key = DeveloperApiKey.objects.filter(user=user, is_active=True).first()
        if api_key is None:
            _, api_key = DeveloperApiKey.create_for_user(user)
        api_key.webhook_url = webhook_url
        api_key.save(update_fields=["webhook_url"])
        return api_key

    await sync_to_async(update_key)()
    await update.message.reply_text("API webhook URL saved.")


async def api_docs(update, context):
    if not settings.DEVELOPER_API_ENABLED:
        await update.message.reply_text("Developer API is disabled for now.")
        return
    await update.message.reply_text(
        "Developer API\n\n"
        "Auth: Authorization: Bearer API_KEY\n\n"
        "GET /api/v1/products/\n"
        "POST /api/v1/orders/ JSON: {\"product_id\": 1, \"quantity\": 1}\n\n"
        "Webhook events are signed with X-Black16-Signature."
    )


async def callback_router(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data or ""

    if data == "home":
        await start(update, context)
    elif data == "shop":
        await show_shop(update, context)
    elif data == "telegram_accounts":
        await show_telegram_accounts(update, context)
    elif data.startswith("shop:"):
        await show_shop(update, context, int(data.split(":", 1)[1]))
    elif data.startswith("product:"):
        await show_product(update, context, int(data.split(":", 1)[1]))
    elif data.startswith("buy:"):
        _, product_id, quantity = data.split(":")
        await buy_product(update, context, int(product_id), int(quantity))
    elif data.startswith("note:"):
        await show_product_note(update, context, int(data.split(":", 1)[1]))
    elif data.startswith("share:"):
        await share_product(update, context, int(data.split(":", 1)[1]))
    elif data == "profile":
        await show_profile(update, context)
    elif data == "orders":
        await show_orders(update, context)
    elif data.startswith("order:"):
        await show_order_detail(update, context, int(data.split(":", 1)[1]))
    elif data == "topup":
        await show_topup(update, context)
    elif data == "payments":
        await show_payments(update, context)
    elif data.startswith("pay_cancel:"):
        await cancel_payment(update, context, int(data.split(":", 1)[1]))
    elif data.startswith("topup_method:"):
        await create_topup_request(update, context, data.split(":", 1)[1])
    elif data == "language":
        await show_language(update, context)
    elif data == "notifications":
        await show_notifications(update, context)
    elif data == "notifications_toggle":
        await toggle_notifications(update, context)
    elif data.startswith("lang:"):
        await set_language(update, context, data.split(":", 1)[1])
    elif data == "support":
        await show_support(update, context)
    elif data == "earn":
        await show_referral(update, context)
    elif data == "api":
        await show_api(update, context)
    elif data == "api_create":
        await create_api_key(update, context)
    elif data == "api_revoke":
        await revoke_api_key(update, context)


async def send_or_edit(update, text: str, reply_markup=None):
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(text, reply_markup=reply_markup)


async def limited(update, action: str, *, limit: int = 12) -> bool:
    user = update.effective_user
    is_limited = await sync_to_async(is_rate_limited)(user.id, action, limit=limit) if user else False
    if is_limited:
        await send_or_edit(update, "Too many requests. Please wait a minute and try again.")
        return True
    return False
