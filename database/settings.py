import logging
from typing import Any, Optional, Dict
from database.client import supabase

logger = logging.getLogger(__name__)

async def get_setting(key: str, default: Any = None) -> Any:
    """Sozlamani Supabase bazasidan olish."""
    if not supabase:
        return default
    try:
        res = supabase.table("bot_settings").select("value").eq("key", key).execute()
        if res.data:
            return res.data[0].get("value", default)
        return default
    except Exception as e:
        logger.error(f"get_setting xatosi ({key}): {e}")
        return default

async def set_setting(key: str, value: Any) -> bool:
    """Sozlamani Supabase bazasiga yozish."""
    if not supabase:
        return False
    try:
        data = {
            "key": key,
            "value": value
        }
        supabase.table("bot_settings").upsert(data, on_conflict="key").execute()
        return True
    except Exception as e:
        logger.error(f"set_setting xatosi ({key}): {e}")
        return False

async def get_threads_config() -> Dict[str, Any]:
    """Guruh threadlari konfiguratsiyasini olish."""
    return await get_setting("threads_config", {})

async def save_threads_config(group_id: int, threads: Dict[str, int]) -> bool:
    """Guruh threadlari konfiguratsiyasini saqlash."""
    data = {
        "group_id": group_id,
        "threads": threads
    }
    return await set_setting("threads_config", data)
