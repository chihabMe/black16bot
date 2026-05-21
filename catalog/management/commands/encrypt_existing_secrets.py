from django.core.management.base import BaseCommand

from catalog.models import StockItem
from orders.models import Order, OrderItem
from security.crypto import encrypt_text, is_encrypted


class Command(BaseCommand):
    help = "Encrypt existing plaintext stock and delivered order secrets in place."

    def handle(self, *args, **options):
        stock_count = 0
        for stock in StockItem.objects.iterator():
            if stock.secret_content and not is_encrypted(stock.secret_content):
                stock.secret_content = encrypt_text(stock.secret_content)
                stock.save(update_fields=["secret_content"])
                stock_count += 1

        order_count = 0
        for order in Order.objects.exclude(delivered_payload="").iterator():
            if not is_encrypted(order.delivered_payload):
                order.delivered_payload = encrypt_text(order.delivered_payload)
                order.save(update_fields=["delivered_payload"])
                order_count += 1

        item_count = 0
        for item in OrderItem.objects.exclude(secret_snapshot="").iterator():
            if not is_encrypted(item.secret_snapshot):
                item.secret_snapshot = encrypt_text(item.secret_snapshot)
                item.save(update_fields=["secret_snapshot"])
                item_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Encrypted {stock_count} stock items, {order_count} orders, {item_count} order items."
            )
        )
