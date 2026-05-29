from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from bot import handlers


async def configure_bot_menu(application):
    from telegram import BotCommand, MenuButtonCommands

    await application.bot.set_my_commands(
        [
            BotCommand("start", "Open main menu"),
            BotCommand("shop", "Browse products"),
            BotCommand("topup", "Add wallet balance"),
            BotCommand("payments", "View pending top-ups"),
            BotCommand("orders", "View order history"),
            BotCommand("profile", "View your profile"),
            BotCommand("referral", "Open referral dashboard"),
            BotCommand("support", "Contact support"),
            BotCommand("help", "Show help"),
        ]
    )
    await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())


class Command(BaseCommand):
    help = "Run the Telegram bot with long polling."

    def handle(self, *args, **options):
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is missing. Add it to .env.")

        try:
            from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
        except ImportError as exc:
            raise CommandError("Install python-telegram-bot: pip install -r requirements.txt") from exc

        application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).post_init(configure_bot_menu).build()
        application.add_handler(CommandHandler("start", handlers.start))
        application.add_handler(CommandHandler("help", handlers.help_command))
        application.add_handler(CommandHandler("shop", handlers.show_shop))
        application.add_handler(CommandHandler("telegram_accounts", handlers.show_telegram_accounts))
        application.add_handler(CommandHandler("profile", handlers.show_profile))
        application.add_handler(CommandHandler("orders", handlers.show_orders))
        application.add_handler(CommandHandler("payments", handlers.show_payments))
        application.add_handler(CommandHandler("topup", handlers.show_topup))
        application.add_handler(CommandHandler("topup_amount", handlers.topup_amount))
        application.add_handler(CommandHandler("topup_proof", handlers.topup_proof))
        application.add_handler(CommandHandler("binance_topup", handlers.binance_topup))
        application.add_handler(CommandHandler("referral", handlers.show_referral))
        application.add_handler(CommandHandler("notifications", handlers.show_notifications))
        application.add_handler(CommandHandler("support", handlers.show_support))
        application.add_handler(CommandHandler("support_ticket", handlers.support_ticket))
        application.add_handler(CommandHandler("api", handlers.show_api))
        application.add_handler(CommandHandler("api_webhook", handlers.set_api_webhook))
        application.add_handler(CommandHandler("api_docs", handlers.api_docs))
        application.add_handler(CommandHandler("admin_stats", handlers.admin_stats))
        application.add_handler(MessageHandler(filters.PHOTO, handlers.topup_photo_proof))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.text_message))
        application.add_handler(CallbackQueryHandler(handlers.callback_router))
        application.add_error_handler(handlers.error_handler)

        self.stdout.write(self.style.SUCCESS("Telegram bot polling started."))
        application.run_polling()
