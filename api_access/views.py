import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from api_access.services import authenticate_api_key
from api_access.webhooks import send_order_webhook
from catalog.models import Product
from orders.services import InsufficientBalance, OutOfStock, ProductUnavailable, purchase_product


def bearer_token(request) -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return ""
    return header.removeprefix("Bearer ").strip()


def require_api_key(request):
    api_key = authenticate_api_key(bearer_token(request))
    if api_key is None:
        return None, JsonResponse({"error": "invalid_api_key"}, status=401)
    return api_key, None


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
    api_key, error = require_api_key(request)
    if error:
        return error

    try:
        payload = json.loads(request.body.decode() or "{}")
        product_id = int(payload["product_id"])
        quantity = int(payload.get("quantity", 1))
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "invalid_payload"}, status=400)

    try:
        result = purchase_product(user_id=api_key.user_id, product_id=product_id, quantity=quantity)
    except Product.DoesNotExist:
        return JsonResponse({"error": "product_not_found"}, status=404)
    except ProductUnavailable:
        return JsonResponse({"error": "product_unavailable"}, status=409)
    except InsufficientBalance:
        return JsonResponse({"error": "insufficient_balance"}, status=402)
    except OutOfStock:
        return JsonResponse({"error": "out_of_stock"}, status=409)

    api_key.total_orders += 1
    api_key.total_spend += result.order.price_paid
    api_key.save(update_fields=["total_orders", "total_spend"])
    send_order_webhook(api_key=api_key, order=result.order, secret_content=result.order.delivered_payload)

    return JsonResponse(
        {
            "order": {
                "id": result.order.pk,
                "product_id": result.order.product_id,
                "product_name": result.order.product.name,
                "price_paid": str(result.order.price_paid),
                "quantity": result.order.quantity,
                "status": result.order.status,
                "secret_content": result.order.delivered_payload,
            }
        },
        status=201,
    )
