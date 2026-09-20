import logging
from typing import Optional, Tuple, Any
from aiogram import Bot

from aiogram.types import InlineKeyboardMarkup
from config import config
from database.settings import get_threads_config
from database.admins import get_all_admins

logger = logging.getLogger(__name__)

async def get_target_group_and_threads() -> Tuple[Optional[int], dict]:
    """Sozlangan admin guruh va threadlar lug'atini olish."""
    cfg = await get_threads_config()
    group_id = cfg.get("group_id")
    threads = cfg.get("threads", {})
    return group_id, threads

async def notify_system_status(bot: Bot, text: str) -> None:
    """Tizim statusi haqida xabar berish (Status thread ga)."""
    group_id, threads = await get_target_group_and_threads()
    thread_id = threads.get("status")
    if group_id and thread_id:
        try:
            await bot.send_message(
                chat_id=group_id,
                message_thread_id=thread_id,
                text=text,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Status threadga yuborishda xatolik: {e}")

async def notify_error_log(bot: Bot, error_text: str) -> None:
    """Xatolik yuz berganda xatoliklar threadiga yuborish."""
    group_id, threads = await get_target_group_and_threads()
    thread_id = threads.get("logs")
    if group_id and thread_id:
        try:
            await bot.send_message(
                chat_id=group_id,
                message_thread_id=thread_id,
                text=f"⚠️ **Tizim Xatoligi:**\n```\n{error_text[:3500]}\n```",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Logs threadga yuborishda xatolik: {e}")

async def forward_submission_for_review(
    bot: Bot,
    voice_file_id: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup
) -> None:
    """
    Yangi ovoz taklifini moderatsiya uchun yuborish:
    Agar guruhdagi 'requests' thread sozlangan bo'lsa, o'sha yerga tushadi.
    Aks holda shaxsiy adminlarga boradi.
    """
    group_id, threads = await get_target_group_and_threads()
    req_thread = threads.get("requests")

    if group_id and req_thread:
        try:
            await bot.send_voice(
                chat_id=group_id,
                message_thread_id=req_thread,
                voice=voice_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
            return
        except Exception as e:
            logger.error(f"Guruh requests threadiga yuborishda xatolik: {e}")

    # Guruh sozlanmagan bo'lsa shaxsiy adminlarga
    admin_ids = set()
    if config.SUPERADMIN_ID:
        admin_ids.add(config.SUPERADMIN_ID)
    try:
        db_admins = await get_all_admins()
        for adm in db_admins:
            if adm.get("user_id"):
                admin_ids.add(adm["user_id"])
    except Exception:
        pass

    for aid in admin_ids:
        try:
            await bot.send_voice(
                chat_id=aid,
                voice=voice_file_id,
                caption=caption,
                reply_markup=reply_markup,
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Adminga taklif yuborish xatosi (ID: {aid}): {e}")

async def upload_voice_to_storage(
    bot: Bot,
    voice_input: Any,
    caption: str
) -> Tuple[Optional[str], Optional[str], int, Optional[int]]:
    """
    Ovozni saqlash joyiga yuborish (guruhdagi storage thread yoki saqlash kanali).
    Qaytaradi: (file_id, file_unique_id, duration, message_id)
    """
    group_id, threads = await get_target_group_and_threads()
    storage_thread = threads.get("storage")

    # 1. Agar guruhda 'storage' thread mavjud bo'lsa, o'sha yerga yuboriladi
    if group_id and storage_thread:
        try:
            msg = await bot.send_voice(
                chat_id=group_id,
                message_thread_id=storage_thread,
                voice=voice_input,
                caption=caption
            )
            return msg.voice.file_id, msg.voice.file_unique_id, msg.voice.duration, msg.message_id
        except Exception as e:
            logger.error(f"Guruh storage threadiga yuborish xatosi: {e}")

    # 2. Agar kanal sozlangan bo'lsa, kanalga yuboriladi
    if config.STORAGE_CHANNEL_ID:
        try:
            msg = await bot.send_voice(
                chat_id=config.STORAGE_CHANNEL_ID,
                voice=voice_input,
                caption=caption
            )
            return msg.voice.file_id, msg.voice.file_unique_id, msg.voice.duration, msg.message_id
        except Exception as e:
            logger.error(f"Kanalga yuborish xatosi: {e}")

    return None, None, 0, None
