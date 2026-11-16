"""MenfessBot entry point."""
import logging
from telegram.ext import Application,CallbackQueryHandler,CommandHandler,MessageHandler,filters
from .config import load_settings
from .database import SubmissionStore
from .handlers import start,help_command,privacy_command,balance_command,transactions_command,transfer_command,grant_command,receive_submission,moderate

def main():
    s=load_settings()
    logging.basicConfig(level=getattr(logging,s.log_level,logging.INFO),format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    store=SubmissionStore(s.database_path); store.prune_reviewed(s.retention_days)
    app=Application.builder().token(s.bot_token).build()
    app.bot_data.update({"store":store,"settings":s,"admin_ids":s.admin_ids,"channel_id":s.channel_id})
    for name,fn in [("start",start),("help",help_command),("privacy",privacy_command),("balance",balance_command),("transactions",transactions_command),("transfer",transfer_command),("grant",grant_command)]:
        app.add_handler(CommandHandler(name,fn))
    app.add_handler(CallbackQueryHandler(moderate,pattern=r"^(approve|reject):"))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE & ~filters.COMMAND,receive_submission))
    logging.getLogger(__name__).info("MenfessBot starting")
    app.run_polling(allowed_updates=["message","callback_query"])
if __name__=="__main__": main()
