from django.test import TestCase, override_settings
from django.utils import timezone

from bot.keyboards import main_menu
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


class MainMenuFeatureFlagTests(TestCase):
    @override_settings(TELEGRAM_ACCOUNTS_ENABLED=False, REFERRAL_FEATURE_ENABLED=False, DEVELOPER_API_ENABLED=False)
    def test_menu_hides_disabled_telegram_accounts_and_earn(self):
        markup = main_menu()
        labels = [button.text for row in markup.inline_keyboard for button in row]

        self.assertNotIn("✈️ Buy Telegram Account", labels)
        self.assertNotIn("🎁 Earn", labels)
        self.assertNotIn("🔌 Developer API", labels)
