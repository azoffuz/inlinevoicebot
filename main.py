import asyncio
import logging
import sys
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import config
from handlers import user, inline, admin, channel

# Logging sozlash
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- RENDER.COM UCHUN HTTP HEALTH CHECK SERVER ---
async def health_check(request):
    """Render.com yoki Uptime monitoring uchun endpoint."""
    return web.Response(text="Bot is running! 🚀", status=200)

async def start_web_server():
    """Render.com da Web Service portini tinglash."""
    app = web.Application()
    app.router.add_get("/", health_check)
    app.router.add_get("/health", health_check)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    await site.start()
    logger.info(f"Render.com HTTP server 0.0.0.0:{config.PORT} portida ishga tushdi.")

# --- TELEGRAM BOT ---
async def start_bot():
    """Botni ishga tushirish."""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN aniqlanmadi! Iltimos, .env faylini to'ldiring.")
        return

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Handler routerlarini ro'yxatdan o'tkazish
    dp.include_router(admin.router)
    dp.include_router(inline.router)
    dp.include_router(channel.router)
    dp.include_router(user.router)

    # Bot buyruqlari menyusini o'rnatish
    from aiogram.types import BotCommand
    commands = [
        BotCommand(command="start", description="Botni qayta ishga tushirish 🔄"),
        BotCommand(command="addvoice", description="Yangi ovoz taklif qilish 🎙"),
        BotCommand(command="top", description="Eng ko'p jo'natilgan ovozlar 🔥"),
        BotCommand(command="help", description="Qo'llanma va yordam 📖"),
        BotCommand(command="admin", description="Admin paneli 🛠")
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception as e:
        logger.error(f"set_my_commands xatosi: {e}")

    # Eski kutilayotgan yangilanishlarni o'chirish
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot polling rejimida ishga tushirilmoqda...")
    
    await dp.start_polling(bot)


async def main():
    """Asosiy kirish nuqtasi: Bot va Web serverni parallel yurgizish."""
    await asyncio.gather(
        start_web_server(),
        start_bot()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
