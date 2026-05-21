from django.conf import settings


def main_menu():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton("Shop", callback_data="shop")],
        [
            InlineKeyboardButton("Top-up Wallet", callback_data="topup"),
            InlineKeyboardButton("My Profile", callback_data="profile"),
        ],
        [
            InlineKeyboardButton("Support", callback_data="support"),
            InlineKeyboardButton("My Orders", callback_data="orders"),
        ],
        [
            InlineKeyboardButton("Language", callback_data="language"),
            InlineKeyboardButton("Developer API", callback_data="api"),
        ],
        [
            InlineKeyboardButton("Buy Telegram Account", callback_data="telegram_accounts"),
            InlineKeyboardButton("Earn", callback_data="earn"),
        ],
    ]
    if settings.PUBLIC_CHANNEL_URL:
        rows.append([InlineKeyboardButton("Channel", url=settings.PUBLIC_CHANNEL_URL)])
    return InlineKeyboardMarkup(rows)


def back_menu(target: str = "home"):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup([[InlineKeyboardButton("Back", callback_data=target)]])


def orders_menu(orders):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [InlineKeyboardButton(f"Order #{order.pk} - {order.product.name}", callback_data=f"order:{order.pk}")]
        for order in orders
    ]
    rows.append([InlineKeyboardButton("Back", callback_data="home")])
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

    nav = [InlineKeyboardButton("Refresh", callback_data=f"shop:{page}")]
    if page > 1:
        nav.append(InlineKeyboardButton("Prev", callback_data=f"shop:{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton("Next", callback_data=f"shop:{page + 1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def product_detail_menu(product_id: int):
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Qty 1", callback_data=f"buy:{product_id}:1"),
                InlineKeyboardButton("Qty 2", callback_data=f"buy:{product_id}:2"),
                InlineKeyboardButton("Qty 5", callback_data=f"buy:{product_id}:5"),
            ],
            [
                InlineKeyboardButton("Qty 10", callback_data=f"buy:{product_id}:10"),
                InlineKeyboardButton("View Note", callback_data=f"note:{product_id}"),
            ],
            [InlineKeyboardButton("Share Link", callback_data=f"share:{product_id}")],
            [InlineKeyboardButton("Back", callback_data="shop")],
        ]
    )


def topup_methods_menu():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    methods = [
        ("Binance Deposit", "binance_deposit"),
        ("Binance Pay", "binance_pay"),
        ("Bybit Pay", "bybit_pay"),
        ("CryptoBot", "cryptobot"),
        ("USDT BEP-20", "usdt_bep20"),
        ("USDT TRC-20", "usdt_trc20"),
        ("TON", "ton"),
        ("TRON", "tron"),
        ("Other", "other"),
    ]
    rows = [[InlineKeyboardButton(label, callback_data=f"topup_method:{value}")] for label, value in methods]
    rows.append([InlineKeyboardButton("Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def language_menu():
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    rows = [
        [
            InlineKeyboardButton("English", callback_data="lang:en"),
            InlineKeyboardButton("Tiếng Việt", callback_data="lang:vi"),
        ],
        [
            InlineKeyboardButton("中文", callback_data="lang:zh"),
            InlineKeyboardButton("Indonesia", callback_data="lang:id"),
        ],
        [
            InlineKeyboardButton("Español", callback_data="lang:es"),
            InlineKeyboardButton("Русский", callback_data="lang:ru"),
        ],
        [InlineKeyboardButton("العربية", callback_data="lang:ar")],
        [InlineKeyboardButton("Back", callback_data="home")],
    ]
    return InlineKeyboardMarkup(rows)


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
