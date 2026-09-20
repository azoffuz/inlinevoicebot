import logging
from typing import List, Dict, Any, Optional
from database.client import supabase

logger = logging.getLogger(__name__)

async def add_voice(
    title: str,
    file_id: str,
    file_unique_id: str,
    duration: int = 0,
    channel_message_id: Optional[int] = None,
    created_by: Optional[int] = None,
    tags: Optional[List[str]] = None
) -> Optional[Dict[str, Any]]:
    """Yangi ovozni Supabase bazasiga qo'shish."""
    if not supabase:
        return None
    try:
        data = {
            "title": title,
            "file_id": file_id,
            "file_unique_id": file_unique_id,
            "duration": duration,
            "channel_message_id": channel_message_id,
            "created_by": created_by,
            "tags": tags or []
        }
        res = supabase.table("voices").upsert(data, on_conflict="file_unique_id").execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"add_voice xatosi: {e}")
        return None

async def get_top_voices(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Eng ko'p ishlatilgan (trend) ovozlarni ketma-ket chiqarish."""
    if not supabase:
        return []
    try:
        res = (
            supabase.table("voices")
            .select("*")
            .order("usage_count", desc=True)
            .order("created_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error(f"get_top_voices xatosi: {e}")
        return []

async def search_voices(query: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Ovozlarni nomi yoki teglari bo'yicha qidirish."""
    if not supabase:
        return []
    try:
        q = query.strip()
        if not q:
            return await get_top_voices(limit, offset)
        
        # Sarlavha bo'yicha ilike (katta-kichik harf farqisiz)
        res = (
            supabase.table("voices")
            .select("*")
            .ilike("title", f"%{q}%")
            .order("usage_count", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.error(f"search_voices xatosi: {e}")
        return []

async def increment_voice_usage(voice_id: str) -> None:
    """Ovoz tanlanganda uning foydalanish sonini oshirish."""
    if not supabase:
        return
    try:
        # RPC yoki oddiy update
        current = supabase.table("voices").select("usage_count").eq("id", voice_id).single().execute()
        if current.data:
            new_count = (current.data.get("usage_count") or 0) + 1
            supabase.table("voices").update({"usage_count": new_count}).eq("id", voice_id).execute()
    except Exception as e:
        logger.error(f"increment_voice_usage xatosi: {e}")

async def get_voice_by_file_unique_id(file_unique_id: str) -> Optional[Dict[str, Any]]:
    """file_unique_id orqali ovozni topish."""
    if not supabase:
        return None
    try:
        res = supabase.table("voices").select("*").eq("file_unique_id", file_unique_id).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        logger.error(f"get_voice_by_file_unique_id xatosi: {e}")
        return None

async def delete_voice(voice_id: str) -> bool:
    """Ovozni bazadan o'chirish."""
    if not supabase:
        return False
    try:
        supabase.table("voices").delete().eq("id", voice_id).execute()
        return True
    except Exception as e:
        logger.error(f"delete_voice xatosi: {e}")
        return False

async def get_total_voices_count() -> int:
    """Jami ovozlar sonini olish."""
    if not supabase:
        return 0
    try:
        res = supabase.table("voices").select("id", count="exact").execute()
        return res.count or 0
    except Exception as e:
        logger.error(f"get_total_voices_count xatosi: {e}")
        return 0
