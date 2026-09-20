import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
    STORAGE_CHANNEL_ID: int = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
    ADMIN_GROUP_ID: int = int(os.getenv("ADMIN_GROUP_ID", "0"))
    SUPERADMIN_ID: int = int(os.getenv("SUPERADMIN_ID", "0"))
    PORT: int = int(os.getenv("PORT", "8080"))

config = Config()

