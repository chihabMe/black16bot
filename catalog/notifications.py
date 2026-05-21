from accounts.models import TelegramUser
from bot.telegram_client import send_telegram_message
from catalog.models import Product


def product_notification_text(product: Product, *, event: str) -> str:
    stock = product.available_stock_count
    if event == "stock":
        title = "📦 Fresh stock added"
    else:
        title = "🆕 New product available"
    country = ""
    if product.product_type == Product.ProductType.TELEGRAM_ACCOUNT:
        country = f"\n🌍 Country: {product.country_name or product.country_code or '-'}"
    return (
        f"{title}\n\n"
        f"🛍️ {product.name}\n"
        f"💵 Price: {product.price} USDT\n"
        f"📦 Stock: {stock}{country}\n\n"
        "Open the bot and use /shop or /telegram_accounts to buy."
    )


def notify_users_about_product(*, product_id: int, event: str = "product") -> tuple[int, int]:
    product = Product.objects.with_stock_counts().get(pk=product_id)
    if not product.is_active:
        return 0, 0
    text = product_notification_text(product, event=event)
    users = TelegramUser.objects.filter(is_blocked=False, notifications_enabled=True).iterator()
    sent = 0
    failed = 0
    for user in users:
        if send_telegram_message(user.telegram_id, text):
            sent += 1
        else:
            failed += 1
    return sent, failed
