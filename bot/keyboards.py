from django.conf import settings


def main_menu():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton("🛒 Shop", callback_data="shop")],
        [
            InlineKeyboardButton("💳 Top-up", callback_data="topup"),
            InlineKeyboardButton("👤 Profile", callback_data="profile"),
        ],
        [
            InlineKeyboardButton("🛟 Support", callback_data="support"),
            InlineKeyboardButton("📦 Orders", callback_data="orders"),
        ],
        [
            InlineKeyboardButton("🔔 Notifications", callback_data="notifications"),
        ],
    ]
    if settings.DEVELOPER_API_ENABLED:
        rows.insert(4, [InlineKeyboardButton("🔌 Developer API", callback_data="api")])
    account_earn_row = []
    if settings.TELEGRAM_ACCOUNTS_ENABLED:
        account_earn_row.append(InlineKeyboardButton("✈️ Buy Telegram Account", callback_data="telegram_accounts"))
    if settings.REFERRAL_FEATURE_ENABLED:
        account_earn_row.append(InlineKeyboardButton("🎁 Earn", callback_data="earn"))
    if account_earn_row:
        rows.append(account_earn_row)
    if settings.PUBLIC_CHANNEL_URL:
        rows.append([InlineKeyboardButton("📣 Channel", url=settings.PUBLIC_CHANNEL_URL)])
    return InlineKeyboardMarkup(rows)


def back_menu(target: str = "home"):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=target)]])


def orders_menu(orders):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton(f"Order #{order.pk} - {order.product.name}", callback_data=f"order:{order.pk}")]
        for order in orders
    ]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def product_list_menu(products, page: int, has_next: bool):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    for product in products:
        stock = getattr(product, "available_stock_count", product.available_stock_count)
        rows.append(
            [
                InlineKeyboardButton(
                    f"{product.name} - {product.price} USDT (Stock: {stock})",
                    callback_data=f"product:{product.pk}",
                )
            ]
        )

    nav = [InlineKeyboardButton("🔄 Refresh", callback_data=f"shop:{page}")]
    if page > 1:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"shop:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"shop:{page + 1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def product_detail_menu(product_id: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Buy 1", callback_data=f"buy:{product_id}:1"),
                InlineKeyboardButton("Buy 2", callback_data=f"buy:{product_id}:2"),
                InlineKeyboardButton("Buy 5", callback_data=f"buy:{product_id}:5"),
            ],
            [
                InlineKeyboardButton("Buy 10", callback_data=f"buy:{product_id}:10"),
                InlineKeyboardButton("📝 Note", callback_data=f"note:{product_id}"),
            ],
            [InlineKeyboardButton("🔗 Share", callback_data=f"share:{product_id}")],
            [InlineKeyboardButton("⬅️ Back", callback_data="shop")],
        ]
    )


def topup_methods_menu():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from payments.methods import enabled_payment_method_choices

    rows = [[InlineKeyboardButton(label, callback_data=f"topup_method:{value}")] for value, label in enabled_payment_method_choices()]
    rows.append([InlineKeyboardButton("⬅️ Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def notifications_menu(enabled: bool):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    label = "🔕 Turn off notifications" if enabled else "🔔 Turn on notifications"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(label, callback_data="notifications_toggle")],
            [InlineKeyboardButton("⬅️ Back", callback_data="home")],
        ]
    )


def api_menu(has_key: bool):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = []
    if has_key:
        rows.append([InlineKeyboardButton("Revoke API Key", callback_data="api_revoke")])
    else:
        rows.append([InlineKeyboardButton("Create API Key", callback_data="api_create")])
    rows.append([InlineKeyboardButton("Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def pending_payments_menu(payments):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [
            InlineKeyboardButton(
                f"Cancel #{payment.pk} - {payment.amount} USDT",
                callback_data=f"pay_cancel:{payment.pk}",
            )
        ]
        for payment in payments
    ]
    rows.append([InlineKeyboardButton("Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)
