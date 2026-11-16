"""Telegram commands and moderation callbacks."""
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from .database import SubmissionStore

logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Halo! Kirim pesan atau media untuk diajukan sebagai menfess. "
        "Kiriman akan ditinjau moderator sebelum diterbitkan. Jangan kirim data pribadi.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_text(
        "Kirim pesan atau media ke bot. Semua kiriman menunggu persetujuan moderator.")


async def receive_submission(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message
    user = update.effective_user
    store: SubmissionStore = context.application.bot_data["store"]
    try:
        sid = store.add(message.chat_id, message.message_id, user.id if user else None)
    except Exception:
        logger.exception("Unable to save submission")
        await message.reply_text("Maaf, kiriman belum dapat disimpan. Coba lagi nanti.")
        return
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("Terbitkan", callback_data=f"approve:{sid}"),
        InlineKeyboardButton("Tolak", callback_data=f"reject:{sid}")
    ]])
    notified = False
    for admin_id in context.application.bot_data["admin_ids"]:
        try:
            await context.bot.send_message(admin_id, f"Kiriman baru menunggu moderasi. ID: #{sid}", reply_markup=keyboard)
            await context.bot.copy_message(admin_id, message.chat_id, message.message_id)
            notified = True
        except Exception:
            logger.exception("Moderator notification failed: %s", admin_id)
    await message.reply_text("Kiriman diterima dan masuk antrean moderasi." if notified
                             else "Kiriman tersimpan, tetapi moderator belum dapat diberi tahu.")


async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.from_user.id not in context.application.bot_data["admin_ids"]:
        await query.answer("Akses ditolak.", show_alert=True)
        return
    await query.answer()
    try:
        action, raw_id = query.data.split(":", 1)
        sid = int(raw_id)
    except (ValueError, AttributeError):
        await query.edit_message_text("Permintaan moderasi tidak valid.")
        return
    if action not in {"approve", "reject"}:
        await query.edit_message_text("Aksi tidak dikenal.")
        return

    store: SubmissionStore = context.application.bot_data["store"]
    if not store.claim(sid):
        await query.edit_message_text("Kiriman sedang diproses moderator lain, sudah ditinjau, atau tidak ditemukan.")
        return

    try:
        submission = store.get(sid)
        if not submission or submission["status"] != "pending":
            await query.edit_message_text("Kiriman tidak ditemukan atau sudah ditinjau.")
            return

        if action == "approve":
            try:
                await context.bot.copy_message(
                    context.application.bot_data["channel_id"],
                    submission["source_chat_id"], submission["source_message_id"])
            except Exception:
                logger.exception("Publishing failed for submission %s", sid)
                await query.edit_message_text("Gagal menerbitkan. Periksa izin bot di kanal; kiriman tetap menunggu.")
                return
            status = "approved"
        else:
            status = "rejected"

        if not store.set_status(sid, status):
            await query.edit_message_text("Status kiriman berubah sebelum proses selesai. Periksa antrean moderator.")
            return
        await query.edit_message_text(f"Kiriman #{sid}: {status}.")
    finally:
        # Safe after set_status (which removes the claim) and on every failure path.
        store.release_claim(sid)
