from catalog.models import Product, StockItem


def bulk_create_stock(*, product: Product, raw_lines: str, added_by=None) -> int:
    lines = [line.strip() for line in raw_lines.splitlines() if line.strip()]
    stock_items = [
        StockItem(product=product, secret_content=line, added_by=added_by)
        for line in lines
    ]
    StockItem.objects.bulk_create(stock_items)
    return len(stock_items)
