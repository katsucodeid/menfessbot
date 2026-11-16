"""MenfessBot entry point."""
import asyncio
import logging
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
from .config import load_settings
from .database import SubmissionStore
from .handlers import (
    start, help_command, privacy_command, balance_command, transactions_command,
    transfer_command, grant_command, receive_submission, moderate,
)


async def retention_maintenance(application):
    """Periodically remove expired reviewed submissions without touching pending rows."""
    logger = logging.getLogger(__name__)
    while True:
        await asyncio.sleep(6 * 60 * 60)
        settings = application.bot_data["settings"]
        removed = application.bot_data["store"].prune_reviewed(settings.retention_days)
        if removed:
            logger.info("Periodic retention cleanup removed %s reviewed submissions", removed)


async def post_init(application):
    application.create_task(retention_maintenance(application), name="retention-maintenance")


def main():
    settings = load_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    store = SubmissionStore(settings.database_path)
    removed = store.prune_reviewed(settings.retention_days)
    if removed:
        logging.getLogger(__name__).info("Pruned %s expired reviewed submissions", removed)

    app = Application.builder().token(settings.bot_token).post_init(post_init).build()
    app.bot_data.update({
        "store": store,
        "settings": settings,
        "admin_ids": settings.admin_ids,
        "channel_id": settings.channel_id,
    })
    for name, handler in [
        ("start", start), ("help", help_command), ("privacy", privacy_command),
        ("balance", balance_command), ("transactions", transactions_command),
        ("transfer", transfer_command), ("grant", grant_command),
    ]:
        app.add_handler(CommandHandler(name, handler))
    app.add_handler(CallbackQueryHandler(moderate, pattern=r"^(approve|reject):"))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND, receive_submission))
    logging.getLogger(__name__).info("MenfessBot is starting")
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
