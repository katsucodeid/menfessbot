"""MenfessBot entry point."""
import logging
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from .config import load_settings
from .database import SubmissionStore
from .handlers import start, help_command, privacy_command, receive_submission, moderate


def main():
    settings = load_settings()
    logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO),
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    store = SubmissionStore(settings.database_path)
    removed = store.prune_reviewed(settings.retention_days)
    if removed:
        logging.getLogger(__name__).info("Pruned %s expired reviewed submissions", removed)
    app = Application.builder().token(settings.bot_token).build()
    app.bot_data.update({
        "store": store, "settings": settings,
        "admin_ids": settings.admin_ids, "channel_id": settings.channel_id,
    })
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("privacy", privacy_command))
    app.add_handler(CallbackQueryHandler(moderate, pattern=r"^(approve|reject):"))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, receive_submission))
    logging.getLogger(__name__).info("MenfessBot is starting")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
