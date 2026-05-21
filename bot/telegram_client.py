import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)


def send_telegram_message(chat_id: int | str, text: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or not chat_id:
        return False

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": str(chat_id),
            "text": text,
            "disable_web_page_preview": "true",
        }
    ).encode()

    try:
        with urllib.request.urlopen(url, data=data, timeout=15) as response:
            payload = json.load(response)
    except Exception:
        logger.exception("Failed to send Telegram message to %s", chat_id)
        return False

    ok = bool(payload.get("ok"))
    if not ok:
        logger.warning("Telegram sendMessage failed for %s: %s", chat_id, payload)
    return ok


def notify_admins(text: str) -> int:
    chat_ids = []
    if settings.ADMIN_NOTIFICATION_CHAT_ID:
        chat_ids.append(settings.ADMIN_NOTIFICATION_CHAT_ID)
    chat_ids.extend(settings.TELEGRAM_ADMIN_IDS)

    sent = 0
    for chat_id in dict.fromkeys(chat_ids):
        if send_telegram_message(chat_id, text):
            sent += 1
    return sent
