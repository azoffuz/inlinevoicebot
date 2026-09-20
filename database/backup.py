import os
import json
import logging
import tempfile
from datetime import datetime
from typing import Tuple, Dict, Any
from database.client import supabase

logger = logging.getLogger(__name__)

async def create_database_backup() -> Tuple[str, Dict[str, int]]:
    """
    Supabase bazasidagi barcha jadvallarni JSON formatida zaxira fayliga eksport qiladi.
    Qaytaradi: (fayl_yo'li, har bir jadvaldagi qatorlar soni)
    """
    if not supabase:
        raise ValueError("Supabase mijozi ulanmagan.")

    tables = ["voices", "bot_users", "bot_admins", "voice_submissions", "bot_settings"]
    backup_data: Dict[str, Any] = {
        "created_at": datetime.utcnow().isoformat(),
        "tables": {}
    }
    counts: Dict[str, int] = {}

    for table in tables:
        try:
            res = supabase.table(table).select("*").execute()
            rows = res.data or []
            backup_data["tables"][table] = rows
            counts[table] = len(rows)
        except Exception as e:
            logger.error(f"Backup olishda xatolik ({table}): {e}")
            backup_data["tables"][table] = []
            counts[table] = 0

    temp_dir = tempfile.gettempdir()
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"inlinebot_backup_{timestamp_str}.json"
    file_path = os.path.join(temp_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2, default=str)

    return file_path, counts
