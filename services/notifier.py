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

from html import escape

async def forward_submission_for_review(
    bot: Bot,
    voice_file_id: str,
    caption: str,
    reply_markup: InlineKeyboardMarkup
) -> bool:
    """
    Yangi ovoz taklifini moderatsiya uchun yuborish:
    1. Agar guruhdagi 'requests' thread bo'lsa, o'sha yerga tushadi.
    2. Agar guruh bo'lmasa, shaxsiy adminlarga boradi.
    3. Agar send_voice xato bersa (masalan MP3 bo'lsa), send_audio yoki send_message ga o'tadi.
    """
    group_id, threads = await get_target_group_and_threads()
    req_thread = threads.get("requests")

    async def send_to_chat(chat_id: int, thread_id: Optional[int] = None) -> bool:
        kwargs = {
            "chat_id": chat_id,
            "caption": caption,
            "reply_markup": reply_markup,
            "parse_mode": "HTML"
        }
        if thread_id:
            kwargs["message_thread_id"] = thread_id

        # 1-urinish: send_voice
        try:
            await bot.send_voice(voice=voice_file_id, **kwargs)
            return True
        except Exception as e1:
            logger.warning(f"send_voice xatosi ({chat_id}): {e1}")

        # 2-urinish: send_audio
        try:
            await bot.send_audio(audio=voice_file_id, **kwargs)
            return True
        except Exception as e2:
            logger.warning(f"send_audio xatosi ({chat_id}): {e2}")

        # 3-urinish: send_message
        try:
            text_kwargs = {
                "chat_id": chat_id,
                "text": caption,
                "reply_markup": reply_markup,
                "parse_mode": "HTML"
            }
            if thread_id:
                text_kwargs["message_thread_id"] = thread_id
            await bot.send_message(**text_kwargs)
            return True
        except Exception as e3:
            logger.error(f"send_message ham xato berdi ({chat_id}): {e3}")
            return False

    delivered = False

    # 1. Guruhdagi requests threadiga yuborish
    if group_id and req_thread:
        ok = await send_to_chat(group_id, req_thread)
        if ok:
            return True

    # 2. Agar guruh bo'lmasa yoki yuborilmagan bo'lsa, shaxsiy adminlarga
    admin_ids = set()
    if config.SUPERADMIN_ID:
        admin_ids.add(config.SUPERADMIN_ID)
    try:
        db_admins = await get_all_admins()
        for adm in db_admins:
            if adm.get("user_id"):
                admin_ids.add(adm["user_id"])
    except Exception as e:
        logger.error(f"db_admins olishda xatolik: {e}")

    for aid in admin_ids:
        ok = await send_to_chat(aid)
        if ok:
            delivered = True

    if not delivered:
        logger.error(f"Taklif hech qayerga yetkazilmadi! Guruh: {group_id}, Adminlar: {admin_ids}")

    return delivered


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
