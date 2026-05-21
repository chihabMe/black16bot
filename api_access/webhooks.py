import hashlib
import hmac
import ipaddress
import json
import logging
import socket
from urllib.parse import urlparse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


class UnsafeWebhookUrl(ValueError):
    pass


def validate_webhook_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise UnsafeWebhookUrl("Webhook URL must use https://")
    if not parsed.hostname:
        raise UnsafeWebhookUrl("Webhook URL must include a hostname.")

    try:
        addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise UnsafeWebhookUrl("Webhook hostname could not be resolved.") from exc

    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
            raise UnsafeWebhookUrl("Webhook URL cannot resolve to a private or reserved address.")


def sign_payload(payload: dict) -> str:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hmac.new(settings.WEBHOOK_SIGNING_SECRET.encode(), body, hashlib.sha256).hexdigest()


def send_order_webhook(*, api_key, order, secret_content: str) -> bool:
    if not api_key.webhook_url:
        return False
    try:
        validate_webhook_url(api_key.webhook_url)
    except UnsafeWebhookUrl:
        logger.warning("Blocked unsafe API webhook URL for key %s", api_key.pk)
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
