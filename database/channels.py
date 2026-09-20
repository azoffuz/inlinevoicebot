import logging
from typing import List, Dict, Tuple
from aiogram import Bot
from database.settings import get_setting, set_setting

logger = logging.getLogger(__name__)

async def get_required_channels() -> List[Dict[str, str]]:
    """Majburiy obuna kanallari ro'yxatini olish."""
    channels = await get_setting("required_channels", [])
    return channels or []

async def add_required_channel(channel_id: str, name: str, url: str) -> bool:
    """Yangi majburiy kanal qo'shish."""
    channels = await get_required_channels()
    # Dublikat bo'lmasligi uchun
    channels = [c for c in channels if str(c.get("channel_id")) != str(channel_id)]
    channels.append({
        "channel_id": str(channel_id),
        "name": name,
        "url": url
    })
    return await set_setting("required_channels", channels)

async def remove_required_channel(channel_id: str) -> bool:
    """Kanalni ro'yxatdan o'chirish."""
    channels = await get_required_channels()
    channels = [c for c in channels if str(c.get("channel_id")) != str(channel_id)]
    return await set_setting("required_channels", channels)

async def check_user_subscriptions(bot: Bot, user_id: int) -> Tuple[bool, List[Dict[str, str]]]:
    """
    Foydalanuvchining majburiy kanallarga a'zoligini tekshirish.
    Qaytaradi: (barchasiga_azo_bo'lganmi, a'zo_bo'linmagan_kanallar)
    """
    channels = await get_required_channels()
    if not channels:
        return True, []

    unsubscribed = []
    for ch in channels:
        ch_id = ch.get("channel_id")
        try:
            member = await bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status not in ["creator", "administrator", "member", "restricted"]:
                unsubscribed.append(ch)
        except Exception as e:
            logger.warning(f"Kanal a'zoligini tekshirishda xatolik ({ch_id}): {e}")
            # Agar bot kanal admini bo'lmasa yoki xato bersa foydalanuvchini to'xtatmaymiz
            pass

    return len(unsubscribed) == 0, unsubscribed
