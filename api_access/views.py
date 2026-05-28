import json
from decimal import Decimal

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from api_access.services import authenticate_api_key, daily_spend_used, log_api_usage, order_rate_limit_exceeded
from api_access.webhooks import send_order_webhook
from catalog.models import Product
from orders.services import InsufficientBalance, OutOfStock, ProductUnavailable, purchase_product
from security.crypto import decrypt_text


def bearer_token(request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return ""
    return header.removeprefix("Bearer ").strip()


def require_api_key(request):
    if not settings.DEVELOPER_API_ENABLED:
        return None, JsonResponse({"error": "developer_api_disabled"}, status=403)
    api_key = authenticate_api_key(bearer_token(request))
    if api_key is None:
        return None, JsonResponse({"error": "invalid_api_key"}, status=401)
    api_key.last_used_at = timezone.now()
    api_key.save(update_fields=["last_used_at"])
    return api_key, None


def api_error(api_key, request, endpoint: str, error_code: str, status: int):
    log_api_usage(api_key=api_key, request=request, endpoint=endpoint, status_code=status, error_code=error_code)
    return JsonResponse({"error": error_code}, status=status)


@csrf_exempt
@require_GET
def products(request):
    api_key, error = require_api_key(request)
    if error:
        return error

    rows = []
    for product in Product.objects.filter(is_active=True).with_stock_counts().order_by("sort_order", "name"):
        rows.append(
            {
                "id": product.pk,
                "name": product.name,
                "description": product.description,
                "category": product.category,
                "price": str(product.price),
                "stock": product.available_stock_count,
            }
        )
    return JsonResponse({"products": rows})


@csrf_exempt
@require_POST
def create_order(request):
    endpoint = "orders.create"
    api_key, error = require_api_key(request)
    if error:
        return error

    if not api_key.can_create_orders:
        return api_error(api_key, request, endpoint, "orders_disabled", 403)
    if order_rate_limit_exceeded(api_key, endpoint=endpoint):
        return api_error(api_key, request, endpoint, "rate_limited", 429)

    try:
        payload = json.loads(request.body.decode() or "{}")
        product_id = int(payload["product_id"])
        quantity = int(payload.get("quantity", 1))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return api_error(api_key, request, endpoint, "invalid_payload", 400)

    if quantity < 1:
        return api_error(api_key, request, endpoint, "invalid_quantity", 400)
    if quantity > api_key.max_order_quantity:
        return api_error(api_key, request, endpoint, "quantity_limit_exceeded", 403)

    try:
        product = Product.objects.only("id", "price").get(pk=product_id)
    except Product.DoesNotExist:
        return api_error(api_key, request, endpoint, "product_not_found", 404)

    estimated_cost = product.price * Decimal(quantity)
    if api_key.daily_spend_limit > 0 and daily_spend_used(api_key) + estimated_cost > api_key.daily_spend_limit:
        return api_error(api_key, request, endpoint, "daily_spend_limit_exceeded", 403)

    try:
        result = purchase_product(user_id=api_key.user_id, product_id=product_id, quantity=quantity)
    except Product.DoesNotExist:
        return api_error(api_key, request, endpoint, "product_not_found", 404)
    except ProductUnavailable:
        return api_error(api_key, request, endpoint, "product_unavailable", 409)
    except InsufficientBalance:
        return api_error(api_key, request, endpoint, "insufficient_balance", 402)
    except OutOfStock:
        return api_error(api_key, request, endpoint, "out_of_stock", 409)

    api_key.total_orders += 1
    api_key.total_spend += result.order.price_paid
    api_key.save(update_fields=["total_orders", "total_spend"])
    log_api_usage(
        api_key=api_key,
        request=request,
        endpoint=endpoint,
        status_code=201,
        cost=result.order.price_paid,
    )
    delivered_payload = decrypt_text(result.order.delivered_payload)
    send_order_webhook(api_key=api_key, order=result.order, secret_content=delivered_payload)

    return JsonResponse(
        {
            "order": {
                "id": result.order.pk,
                "product_id": result.order.product_id,
                "product_name": result.order.product.name,
                "price_paid": str(result.order.price_paid),
                "quantity": result.order.quantity,
                "status": result.order.status,
                "secret_content": delivered_payload,
            }
        },
        status=201,
    )
