import hashlib
import hmac
import json
import logging
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def sign_payload(payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hmac.new(settings.WEBHOOK_SIGNING_SECRET.encode(), body, hashlib.sha256).hexdigest()


def send_order_webhook(*, api_key, order, secret_content: str) -> bool:
    if not api_key.webhook_url:
        return False

    payload = {
        "event": "order.completed",
        "order": {
            "id": order.pk,
            "product_id": order.product_id,
            "product_name": order.product.name,
            "quantity": order.quantity,
            "price_paid": str(order.price_paid),
            "status": order.status,
            "secret_content": secret_content,
        },
    }
    body = json.dumps(payload).encode()
    request = urllib.request.Request(
        api_key.webhook_url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Black16-Signature": sign_payload(payload),
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return 200 <= response.status < 300
    except Exception:
        logger.exception("Failed to send API webhook for order %s", order.pk)
        return False
