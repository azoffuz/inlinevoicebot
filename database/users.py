import logging
from typing import List
from database.client import supabase

logger = logging.getLogger(__name__)

async def upsert_user(user_id: int, first_name: str = "", username: str = "") -> None:
    """Foydalanuvchi ma'lumotlarini saqlash yoki yangilash."""
    if not supabase:
        return
    try:
        data = {
            "user_id": user_id,
            "first_name": first_name,
            "username": username
        }
        supabase.table("bot_users").upsert(data, on_conflict="user_id").execute()
    except Exception as e:
        logger.error(f"upsert_user xatosi: {e}")

async def get_total_users_count() -> int:
    """Jami bot foydalanuvchilari soni."""
    if not supabase:
        return 0
    try:
        res = supabase.table("bot_users").select("user_id", count="exact").execute()
        return res.count or 0
    except Exception as e:
        logger.error(f"get_total_users_count xatosi: {e}")
        return 0

async def get_all_user_ids() -> List[int]:
    """Barcha foydalanuvchilar ID lari (broadcast uchun)."""
    if not supabase:
        return []
    try:
        res = supabase.table("bot_users").select("user_id").execute()
        return [row["user_id"] for row in (res.data or [])]
    except Exception as e:
        logger.error(f"get_all_user_ids xatosi: {e}")
        return []
