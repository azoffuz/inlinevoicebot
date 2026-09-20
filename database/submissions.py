import logging
from typing import Optional, Dict, Any
from database.client import supabase

logger = logging.getLogger(__name__)

async def create_submission(
    user_id: int,
    user_name: str,
    title: str,
    file_id: str,
    duration: int = 0
) -> Optional[Dict[str, Any]]:
    """Foydalanuvchi tomonidan yangi ovoz taklifi yaratish."""
    if not supabase:
        return None
    try:
        data = {
            "user_id": user_id,
            "user_name": user_name,
            "title": title,
            "file_id": file_id,
            "duration": duration,
            "status": "pending"
        }
        res = supabase.table("voice_submissions").insert(data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"create_submission xatosi: {e}")
        return None

async def get_submission(sub_id: str) -> Optional[Dict[str, Any]]:
    """Taklifni ID bo'yicha olish."""
    if not supabase:
        return None
    try:
        res = supabase.table("voice_submissions").select("*").eq("id", sub_id).single().execute()
        return res.data
    except Exception as e:
        logger.error(f"get_submission xatosi: {e}")
        return None

async def update_submission_status(sub_id: str, status: str) -> bool:
    """Taklif holatini yangilash ('approved' yoki 'rejected')."""
    if not supabase:
        return False
    try:
        supabase.table("voice_submissions").update({"status": status}).eq("id", sub_id).execute()
        return True
    except Exception as e:
        logger.error(f"update_submission_status xatosi: {e}")
        return False
