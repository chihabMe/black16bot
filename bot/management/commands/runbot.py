from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bot import handlers


class Command(BaseCommand):
    help = "Run the Telegram bot with long polling."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is missing. Add it to .env.")

        try:
            from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
        except ImportError as exc:
            raise CommandError("Install python-telegram-bot: pip install -r requirements.txt") from exc

        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", handlers.start))
        application.add_handler(CommandHandler("help", handlers.help_command))
        application.add_handler(CommandHandler("shop", handlers.show_shop))
        application.add_handler(CommandHandler("telegram_accounts", handlers.show_telegram_accounts))
        application.add_handler(CommandHandler("profile", handlers.show_profile))
        application.add_handler(CommandHandler("orders", handlers.show_orders))
        application.add_handler(CommandHandler("payments", handlers.show_payments))
        application.add_handler(CommandHandler("topup", handlers.show_topup))
        application.add_handler(CommandHandler("topup_amount", handlers.topup_amount))
        application.add_handler(CommandHandler("binance_topup", handlers.binance_topup))
        application.add_handler(CommandHandler("referral", handlers.show_referral))
        application.add_handler(CommandHandler("language", handlers.show_language))
        application.add_handler(CommandHandler("support", handlers.show_support))
        application.add_handler(CommandHandler("support_ticket", handlers.support_ticket))
        application.add_handler(CommandHandler("api", handlers.show_api))
        application.add_handler(CommandHandler("api_webhook", handlers.set_api_webhook))
        application.add_handler(CommandHandler("api_docs", handlers.api_docs))
        application.add_handler(CommandHandler("admin_stats", handlers.admin_stats))
        application.add_handler(MessageHandler(filters.PHOTO, handlers.topup_photo_proof))
        application.add_handler(CallbackQueryHandler(handlers.callback_router))

        self.stdout.write(self.style.SUCCESS("Telegram bot polling started."))
        application.run_polling()
