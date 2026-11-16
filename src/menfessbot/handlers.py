"""Private submissions, join verification, roles, moderation and coin economy."""
import html,logging,re
from telegram import InlineKeyboardButton,InlineKeyboardMarkup
from telegram.constants import ChatMemberStatus
from .database import SubmissionStore
logger=logging.getLogger(__name__)

def valid_submission_hashtag(content, allowed_hashtags):
    """Require exactly one configured hashtag as a standalone token."""
    found = re.findall(r"(?<![\\w])#[A-Za-z0-9_]+", content or "")
    allowed = {tag.lower() for tag in allowed_hashtags}
    selected = [tag.lower() for tag in found if tag.lower() in allowed]
    return len(selected) == 1 and len(found) == 1

def role_for(uid,settings):
    if uid in settings.developer_ids: return "Developer"
    if uid in settings.admin_ids: return "Admin"
    return "Member"

async def is_member(bot,chat_id,uid):
    try:
        member=await bot.get_chat_member(chat_id,uid)
        return member.status not in {ChatMemberStatus.LEFT,ChatMemberStatus.BANNED} and not (member.status == ChatMemberStatus.RESTRICTED and not getattr(member, "is_member", False))
    except Exception:
        logger.exception("Membership lookup failed for chat %s",chat_id); return False

async def membership_gate(update,context):
    s=context.application.bot_data["settings"]; uid=update.effective_user.id
    group_ok=await is_member(context.bot,s.required_group_id,uid)
    channel_ok=await is_member(context.bot,s.required_channel_id,uid)
    if group_ok and channel_ok: return True
    lines=["Wajib bergabung ke grup dan channel berikut sebelum mengirim menfess:"]
    buttons=[]
    if not group_ok:
        lines.append("• Grup wajib")
        if s.group_join_url: buttons.append([InlineKeyboardButton("Gabung Grup",url=s.group_join_url)])
    if not channel_ok:
        lines.append("• Channel wajib")
        if s.channel_join_url: buttons.append([InlineKeyboardButton("Gabung Channel",url=s.channel_join_url)])
    lines.append("Setelah bergabung, kirim /start lagi.")
    await update.effective_message.reply_text("\n".join(lines),reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)
    return False

async def start(update,context):
    await update.effective_message.reply_text("Selamat datang! Kirim teks atau media di chat pribadi ini dengan tepat satu hashtag kategori: #katsuboy, #katsugirl, atau #katsuask. Gunakan /balance untuk saldo dan /help untuk panduan.")
async def help_command(update,context):
    await update.effective_message.reply_text("/start · /privacy · /balance · /transactions · /transfer ID JUMLAH · /grant ID JUMLAH (Admin/Developer)\nSetiap menfess wajib menyertakan tepat satu hashtag kategori yang diizinkan.")
async def privacy_command(update,context):
    await update.effective_message.reply_text("Data yang dicatat: Telegram ID, username, nama tampilan, waktu kirim, metadata moderasi dan transaksi koin. Owner dapat melihat identitas dan waktu melalui channel audit privat. Moderator melihat isi kiriman sebelum publikasi.")
async def balance_command(update,context):
    if role_for(update.effective_user.id,context.application.bot_data["settings"])=="Developer":
        await update.effective_message.reply_text("Saldo: ∞ (Developer memiliki koin unlimited)."); return
    await update.effective_message.reply_text(f"Saldo koin: {context.application.bot_data['store'].balance(update.effective_user.id)}")
async def transactions_command(update,context):
    rows=context.application.bot_data["store"].transactions(update.effective_user.id)
    await update.effective_message.reply_text("\n".join([f"{r['amount']:+} · {r['transaction_type']} · {r['description']}" for r in rows]) or "Belum ada transaksi.")
async def transfer_command(update,context):
    if len(context.args)!=2:
        await update.effective_message.reply_text("Format: /transfer ID_PENERIMA JUMLAH"); return
    try: ok=context.application.bot_data["store"].transfer_coins(update.effective_user.id,int(context.args[0]),int(context.args[1]))
    except ValueError:
        await update.effective_message.reply_text("ID dan jumlah tidak valid."); return
    await update.effective_message.reply_text("Transfer berhasil." if ok else "Saldo tidak cukup.")
async def grant_command(update,context):
    s=context.application.bot_data["settings"]
    if role_for(update.effective_user.id,s) not in {"Developer","Admin"}:
        await update.effective_message.reply_text("Khusus Admin/Developer."); return
    if len(context.args)<2:
        await update.effective_message.reply_text("Format: /grant ID JUMLAH [alasan]"); return
    try:
        uid,amount=int(context.args[0]),int(context.args[1])
        if amount<1: raise ValueError
        ok=context.application.bot_data["store"].change_coins(uid,amount,update.effective_user.id," ".join(context.args[2:]) or "Pemberian pengelola","grant")
    except ValueError:
        await update.effective_message.reply_text("ID dan jumlah harus angka positif."); return
    await update.effective_message.reply_text("Koin diberikan." if ok else "Gagal.")
async def receive_submission(update,context):
    m=update.effective_message; u=update.effective_user
    if m.chat.type!="private" or not await membership_gate(update,context): return
    s=context.application.bot_data["settings"]
    content=m.text or m.caption or ""
    if not valid_submission_hashtag(content,s.allowed_hashtags):
        choices=" ".join(s.allowed_hashtags)
        await m.reply_text(f"Menfess wajib menyertakan tepat satu hashtag kategori dari daftar ini: {choices}\\nContoh: {s.allowed_hashtags[0]} Isi menfess kamu.")
        return
    role=role_for(u.id,s); unlimited=role=="Developer"; store=context.application.bot_data["store"]
    try:
        sid,error=store.create_submission(m.chat_id,m.message_id,u.id,cooldown_seconds=s.submission_cooldown_seconds,
            hourly_limit=s.submission_hourly_limit,coin_cost=s.submission_coin_cost,unlimited=unlimited,
            username=u.username,display_name=u.full_name)
    except Exception:
        logger.exception("Submission save failed"); await m.reply_text("Gagal menyimpan kiriman."); return
    if error=="rate_limit": await m.reply_text("Batas pengiriman tercapai. Coba lagi nanti."); return
    if error=="insufficient_coins": await m.reply_text(f"Koin tidak cukup. Biaya menfess {s.submission_coin_cost} koin. Gunakan /balance."); return
    if s.audit_channel_id:
        audit=(f"🧾 MENFESS MASUK · #{sid}\nNama: {html.escape(u.full_name)}\nUsername: @{html.escape(u.username or 'tidak ada')}\n"
               f"Telegram ID: {u.id}\nPeran: {role}\nWaktu UTC: {store.get(sid)['created_at']}\n"
               f"Biaya: {'Unlimited' if unlimited else str(s.submission_coin_cost)+' koin'}")
        try: await context.bot.send_message(s.audit_channel_id,audit)
        except Exception: logger.exception("Audit channel send failed")
    keyboard=InlineKeyboardMarkup([[InlineKeyboardButton("Terbitkan",callback_data=f"approve:{sid}"),InlineKeyboardButton("Tolak",callback_data=f"reject:{sid}")]])
    notified=False
    for admin in s.admin_ids|s.developer_ids:
        try:
            await context.bot.send_message(admin,f"Menfess #{sid} menunggu moderasi.",reply_markup=keyboard)
            await context.bot.copy_message(admin,m.chat_id,m.message_id); notified=True
        except Exception: logger.exception("Moderator notification failed: %s",admin)
    await m.reply_text(f"Menfess #{sid} diterima. Biaya: {'unlimited' if unlimited else str(s.submission_coin_cost)+' koin'}. "+("Menunggu moderasi." if notified else "Tersimpan; moderator belum terjangkau."))
async def moderate(update,context):
    q=update.callback_query;s=context.application.bot_data["settings"]
    if role_for(q.from_user.id,s) not in {"Developer","Admin"}: await q.answer("Akses ditolak.",show_alert=True); return
    await q.answer()
    try: action,raw=q.data.split(":",1); sid=int(raw)
    except (ValueError,AttributeError): await q.edit_message_text("Callback tidak valid."); return
    if action not in {"approve","reject"}: await q.edit_message_text("Aksi tidak dikenal."); return
    store=context.application.bot_data["store"]
    if not store.claim(sid): await q.edit_message_text("Sudah diproses atau sedang ditinjau."); return
    try:
        row=store.get(sid)
        if not row: await q.edit_message_text("Kiriman tidak ditemukan."); return
        if action=="approve":
            try: await context.bot.copy_message(s.channel_id,row["source_chat_id"],row["source_message_id"])
            except Exception:
                logger.exception("Publish failed"); await q.edit_message_text("Gagal publikasi. Periksa izin bot di channel."); return
            status="approved"
        else: status="rejected"
        store.set_status(sid,status); await q.edit_message_text(f"Menfess #{sid}: {status}.")
    finally: store.release_claim(sid)
