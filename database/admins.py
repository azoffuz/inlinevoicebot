import logging
from typing import List, Dict, Any
from database.client import supabase
from config import config

logger = logging.getLogger(__name__)

async def is_admin(user_id: int) -> bool:
    """Foydalanuvchi admin yoki superadmin ekanligini tekshirish."""
    if user_id == config.SUPERADMIN_ID:
        return True
    if not supabase:
        return False
    try:
        res = supabase.table("bot_admins").select("user_id").eq("user_id", user_id).execute()
        return len(res.data) > 0
    except Exception as e:
        logger.error(f"is_admin xatosi: {e}")
        return False

async def is_superadmin(user_id: int) -> bool:
    """Superadmin ekanligini tekshirish."""
    return user_id == config.SUPERADMIN_ID

async def add_admin(user_id: int, username: str = "", full_name: str = "") -> bool:
    """Yangi admin qo'shish."""
    if not supabase:
        return False
    try:
        data = {
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "role": "admin"
        }
        supabase.table("bot_admins").upsert(data, on_conflict="user_id").execute()
        return True
    except Exception as e:
        logger.error(f"add_admin xatosi: {e}")
        return False

async def remove_admin(user_id: int) -> bool:
    """Adminni olib tashlash."""
    if not supabase:
        return False
    try:
        supabase.table("bot_admins").delete().eq("user_id", user_id).execute()
        return True
    except Exception as e:
        logger.error(f"remove_admin xatosi: {e}")
        return False

async def get_all_admins() -> List[Dict[str, Any]]:
    """Barcha adminlarni ro'yxatini olish."""
    if not supabase:
        return []
    try:
        res = supabase.table("bot_admins").select("*").order("added_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        logger.error(f"get_all_admins xatosi: {e}")
        return []
