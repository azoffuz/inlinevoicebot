import logging
from supabase import create_client, Client
from config import config

logger = logging.getLogger(__name__)

supabase: Client = None

if config.SUPABASE_URL and config.SUPABASE_KEY:
    try:
        supabase = create_client(config.SUPABASE_URL, config.SUPABASE_KEY)
        logger.info("Supabase ulanishi muvaffaqiyatli o'rnatildi.")
    except Exception as e:
        logger.error(f"Supabase ulanishida xatolik: {e}")
else:
    logger.warning("SUPABASE_URL yoki SUPABASE_KEY sozlanmagan! .env faylini tekshiring.")
