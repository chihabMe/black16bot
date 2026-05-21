from django.test import TestCase
from django.utils import timezone

from bot.models import BotRateLimit
from bot.rate_limit import is_rate_limited


class BotRateLimitTests(TestCase):
    def test_rate_limit_is_database_backed(self):
        self.assertFalse(is_rate_limited(123, "buy", limit=2))
        self.assertFalse(is_rate_limited(123, "buy", limit=2))
        self.assertTrue(is_rate_limited(123, "buy", limit=2))
        self.assertEqual(BotRateLimit.objects.get(user_id=123, action="buy").count, 2)

    def test_rate_limit_resets_after_window(self):
        self.assertFalse(is_rate_limited(123, "shop", limit=1))
        bucket = BotRateLimit.objects.get(user_id=123, action="shop")
        bucket.window_start = timezone.now() - timezone.timedelta(seconds=61)
        bucket.save(update_fields=["window_start"])

        self.assertFalse(is_rate_limited(123, "shop", limit=1, window_seconds=60))
        bucket.refresh_from_db()
        self.assertEqual(bucket.count, 1)
