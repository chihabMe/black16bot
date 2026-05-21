from decimal import Decimal

from django.core.management.base import BaseCommand

from accounts.models import TelegramUser
from catalog.models import Product
from catalog.services import bulk_create_stock


class Command(BaseCommand):
    help = "Seed demo products, stock, and one demo Telegram user."

    def handle(self, *args, **options):
        products = [
            {
                "name": "Gemini Pro 18 month 5TB",
                "price": Decimal("3.20"),
                "note_md": "Includes Gemini Pro access and 5TB storage. Warranty: 24 hours after delivery.",
            },
            {
                "name": "Nord VPN 3 MONTH shared",
                "price": Decimal("1.00"),
                "note_md": "Shared VPN account. Do not change password or account settings.",
            },
            {
                "name": "Office365 + 100GB OneDrive lifetime plan",
                "price": Decimal("0.80"),
                "note_md": "Office365 account with OneDrive storage. Replacement only if login fails on delivery.",
            },
            {
                "name": "ChatGPT Plus 1 month pre made account",
                "price": Decimal("3.50"),
                "note_md": "Pre-made account credentials. Use the delivered email/password only.",
            },
            {
                "name": "Canva Edu Pro 1 year",
                "price": Decimal("0.50"),
                "note_md": "Canva Edu invite/account. Warranty depends on account state at delivery.",
            },
            {
                "name": "Telegram Account - United States",
                "price": Decimal("2.00"),
                "product_type": Product.ProductType.TELEGRAM_ACCOUNT,
                "country_code": "US",
                "country_name": "United States",
                "note_md": "Telegram account stock by country. Confirm your target country before buying.",
                "warranty_note": "No warranty after changing login/session details.",
            },
        ]

        created_products = 0
        created_stock = 0
        for item in products:
            product, created = Product.objects.get_or_create(
                name=item["name"],
                defaults={
                    "price": item["price"],
                    "is_active": True,
                    "note_md": item.get("note_md", ""),
                    "product_type": item.get("product_type", Product.ProductType.DIGITAL),
                    "country_code": item.get("country_code", ""),
                    "country_name": item.get("country_name", ""),
                    "warranty_note": item.get("warranty_note", ""),
                },
            )
            if created:
                created_products += 1
            else:
                for field in ("note_md", "product_type", "country_code", "country_name", "warranty_note"):
                    if field in item:
                        setattr(product, field, item[field])
                product.save(update_fields=["note_md", "product_type", "country_code", "country_name", "warranty_note"])
            if not product.stock_items.exists():
                slug = item["name"].lower().replace(" ", "-")
                created_stock += bulk_create_stock(
                    product=product,
                    raw_lines="\n".join(
                        [
                            f"{slug}-demo-1:password",
                            f"{slug}-demo-2:password",
                            f"{slug}-demo-3:password",
                        ]
                    ),
                )

        TelegramUser.objects.get_or_create(
            telegram_id=100000001,
            defaults={
                "username": "demo_user",
                "first_name": "Demo",
                "balance": Decimal("25.00"),
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created_products} products and {created_stock} stock items."
            )
        )
