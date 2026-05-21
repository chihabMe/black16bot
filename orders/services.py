from dataclasses import dataclass
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from accounts.models import TelegramUser
from bot.telegram_client import send_telegram_message
from catalog.models import Product, StockItem
from orders.models import Order, OrderItem
from security.crypto import decrypt_text, encrypt_text
from wallet.models import WalletTransaction


class PurchaseError(Exception):
    """Base class for expected purchase failures."""


class ProductUnavailable(PurchaseError):
    pass


class InsufficientBalance(PurchaseError):
    pass


class OutOfStock(PurchaseError):
    pass


@dataclass(frozen=True)
class PurchaseResult:
    order: Order
    stock_item: StockItem
    stock_items: tuple[StockItem, ...] = ()


def purchase_product(*, user_id: int, product_id: int, quantity: int = 1) -> PurchaseResult:
    """Atomically buy one stock item for a user.

    The user row and selected stock row are locked until the transaction commits.
    This prevents double spending and double selling under concurrent requests.
    """

    with transaction.atomic():
        user = TelegramUser.objects.select_for_update().get(pk=user_id)
        product = Product.objects.select_for_update().get(pk=product_id)

        if quantity < 1:
            raise PurchaseError("Quantity must be at least 1.")

        if not product.is_active:
            raise ProductUnavailable("This product is currently unavailable.")

        total_price = product.price * Decimal(quantity)
        if user.balance < total_price:
            raise InsufficientBalance("Insufficient wallet balance.")

        stock_items = list(
            StockItem.objects.select_for_update(skip_locked=True)
            .filter(product=product, status=StockItem.Status.AVAILABLE)
            .order_by("created_at", "pk")
            [:quantity]
        )
        if len(stock_items) < quantity:
            raise OutOfStock("This product is out of stock.")

        sold_at = timezone.now()
        first_stock_item = stock_items[0]
        for stock_item in stock_items:
            stock_item.status = StockItem.Status.SOLD
            stock_item.sold_to = user
            stock_item.sold_at = sold_at
            stock_item.save(update_fields=["status", "sold_to", "sold_at"])

        TelegramUser.objects.filter(pk=user.pk).update(balance=F("balance") - total_price)
        user.refresh_from_db(fields=["balance"])

        delivered_payload = "\n\n".join(decrypt_text(item.secret_content) for item in stock_items)
        order = Order.objects.create(
            user=user,
            product=product,
            stock_item=first_stock_item,
            quantity=quantity,
            unit_price=product.price,
            price_paid=total_price,
            delivered_payload=encrypt_text(delivered_payload),
        )
        OrderItem.objects.bulk_create(
            [
                OrderItem(
                    order=order,
                    stock_item=item,
                    secret_snapshot=encrypt_text(decrypt_text(item.secret_content)),
                )
                for item in stock_items
            ]
        )

        WalletTransaction.objects.create(
            user=user,
            amount=-total_price,
            transaction_type=WalletTransaction.Type.PURCHASE,
            status=WalletTransaction.Status.COMPLETED,
            related_order=order,
            note=f"Purchase order #{order.pk}",
        )

        return PurchaseResult(order=order, stock_item=first_stock_item, stock_items=tuple(stock_items))


def refund_order(*, order_id: int, admin_user=None, note: str = "") -> Order:
    with transaction.atomic():
        order = Order.objects.select_for_update().select_related("user").get(pk=order_id)
        if order.status == Order.Status.REFUNDED:
            return order

        user = TelegramUser.objects.select_for_update().get(pk=order.user_id)
        TelegramUser.objects.filter(pk=user.pk).update(balance=F("balance") + order.price_paid)

        order.status = Order.Status.REFUNDED
        order.refunded_at = timezone.now()
        if note:
            order.admin_note = note
        order.save(update_fields=["status", "refunded_at", "admin_note"])
        order.items.select_related("stock_item").update(status=OrderItem.Status.REFUNDED)
        for item in order.items.select_related("stock_item"):
            item.stock_item.status = StockItem.Status.REFUNDED
            item.stock_item.save(update_fields=["status"])

        WalletTransaction.objects.create(
            user=user,
            amount=order.price_paid,
            transaction_type=WalletTransaction.Type.REFUND,
            status=WalletTransaction.Status.COMPLETED,
            related_order=order,
            created_by=admin_user,
            note=note or f"Refund order #{order.pk}",
        )
        send_telegram_message(
            user.telegram_id,
            f"Order #{order.pk} was refunded.\n"
            f"Amount credited: {order.price_paid} USDT",
        )
        return order


def replace_order_stock(*, order_id: int, admin_user=None, note: str = "") -> Order:
    with transaction.atomic():
        order = Order.objects.select_for_update().select_related("user", "product", "stock_item").get(pk=order_id)
        if order.status == Order.Status.REFUNDED:
            raise PurchaseError("Refunded orders cannot be replaced.")

        order_items = list(order.items.select_for_update().select_related("stock_item").order_by("created_at", "pk"))
        quantity = len(order_items) or 1
        replacements = list(
            StockItem.objects.select_for_update(skip_locked=True)
            .filter(product=order.product, status=StockItem.Status.AVAILABLE)
            .order_by("created_at", "pk")
            [:quantity]
        )
        if len(replacements) < quantity:
            raise OutOfStock("No available replacement stock for this product.")

        for order_item in order_items:
            old_stock = order_item.stock_item
            old_stock.status = StockItem.Status.REPLACED
            old_stock.save(update_fields=["status"])
            order_item.status = OrderItem.Status.REPLACED
            order_item.replaced_at = timezone.now()
            order_item.save(update_fields=["status", "replaced_at"])

        sold_at = timezone.now()
        delivered_payload = "\n\n".join(decrypt_text(item.secret_content) for item in replacements)
        for replacement in replacements:
            replacement.status = StockItem.Status.SOLD
            replacement.sold_to = order.user
            replacement.sold_at = sold_at
            replacement.save(update_fields=["status", "sold_to", "sold_at"])
            OrderItem.objects.create(
                order=order,
                stock_item=replacement,
                secret_snapshot=encrypt_text(decrypt_text(replacement.secret_content)),
            )

        order.stock_item = replacements[0]
        order.status = Order.Status.REPLACED
        order.replaced_at = timezone.now()
        order.delivered_payload = encrypt_text(delivered_payload)
        if note:
            order.admin_note = note
        order.save(update_fields=["stock_item", "status", "replaced_at", "delivered_payload", "admin_note"])

    send_telegram_message(
        order.user.telegram_id,
        f"Order #{order.pk} was replaced.\n\n"
        f"Product: {order.product.name}\n\n"
        f"New item:\n{decrypt_text(order.delivered_payload)}",
    )
    return order
