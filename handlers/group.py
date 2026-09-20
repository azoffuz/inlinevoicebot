import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from database.admins import is_admin
from database.settings import save_threads_config

logger = logging.getLogger(__name__)

router = Router()

@router.message(Command("setup_threads", "set_thread", "setthread"), F.chat.type.in_(["group", "supergroup"]))
async def cmd_setup_threads(message: Message, bot: Bot):
    """
    Guruhda admin threadlarini (Forum topics) avtomatik yaratish va sozlash.
    """
    user_id = message.from_user.id
    if not await is_admin(user_id):
        return await message.reply("⛔️ Bu buyruq faqat bot adminlari uchun!")

    chat = await bot.get_chat(message.chat.id)
    if not chat.is_forum:
        return await message.reply(
            "⚠️ **Xatolik:** Ushbu guruhda **Topics (Mavzular)** yoqilmagan!\n\n"
            "Iltimos, guruh sozlamalariga kiring (Edit Group -> Topics) va uni yoqing."
        )

    # Bot huquqini tekshirish
    bot_member = await bot.get_chat_member(chat_id=message.chat.id, user_id=bot.id)
    if not getattr(bot_member, "can_manage_topics", False) and bot_member.status != "creator":
        return await message.reply(
            "⚠️ Botga guruhda **Manage Topics (Mavzularni boshqarish)** admin huquqini berishingiz kerak!"
        )

    wait_msg = await message.reply("⏳ Mavzular (threadlar) avtomatik ochilmoqda...")

    try:
        # 1. 🟢 Tizim & Status
        status_top = await bot.create_forum_topic(
            chat_id=message.chat.id,
            name="🟢 Tizim & Status",
            icon_color=0x8EEE98
        )
        
        # 2. 📥 Ovoz Takliflari (Moderatsiya)
        requests_top = await bot.create_forum_topic(
            chat_id=message.chat.id,
            name="📥 Ovoz Takliflari",
            icon_color=0x6FB9F0
        )

        # 3. 🎙 Ovozlar Ombori
        storage_top = await bot.create_forum_topic(
            chat_id=message.chat.id,
            name="🎙 Ovozlar Ombori",
            icon_color=0xFFD67E
        )

        # 4. 📊 Statistika & Trendlar
        stats_top = await bot.create_forum_topic(
            chat_id=message.chat.id,
            name="📊 Statistika & Trendlar",
            icon_color=0xFF93B2
        )

        # 5. ⚠️ Xatoliklar & Audit
        logs_top = await bot.create_forum_topic(
            chat_id=message.chat.id,
            name="⚠️ Xatoliklar & Audit",
            icon_color=0xFB6F5F
        )

        # Bazaga saqlash
        threads_map = {
            "status": status_top.message_thread_id,
            "requests": requests_top.message_thread_id,
            "storage": storage_top.message_thread_id,
            "stats": stats_top.message_thread_id,
            "logs": logs_top.message_thread_id
        }

        await save_threads_config(message.chat.id, threads_map)

        # Har bir threadga xush kelibsiz xabari
        await bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=status_top.message_thread_id,
            text="🟢 **Tizim & Status monitoringi faollashdi!**\nServer va bot holati haqida ma'lumotlar shu yerga keladi.",
            parse_mode="Markdown"
        )
        await bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=requests_top.message_thread_id,
            text="📥 **Ovoz Takliflari moderatsiyasi!**\nFoydalanuvchilar taklif qilgan ovozlar shu yerga keladi. Tasdiqlanganida bu yerdan o'chib, 'Ovozlar Ombori'ga o'tadi.",
            parse_mode="Markdown"
        )
        await bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=storage_top.message_thread_id,
            text="🎙 **Ovozlar Ombori (Voice Storage)!**\nTasdiqlangan barcha yangi ovozlar shu yerda saqlanadi.",
            parse_mode="Markdown"
        )
        await bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=stats_top.message_thread_id,
            text="📊 **Statistika & Trendlar!**\nEng mashhur ovozlar va faollik shu yerda yoritiladi.",
            parse_mode="Markdown"
        )
        await bot.send_message(
            chat_id=message.chat.id,
            message_thread_id=logs_top.message_thread_id,
            text="⚠️ **Xatoliklar & Audit!**\nTizimdagi xatoliklar avtomatik shu yerga yuboriladi.",
            parse_mode="Markdown"
        )

        await wait_msg.edit_text(
            "✅ **Ajoyib! Barcha 5 ta thread muvaffaqiyatli yaratildi va sozlandi:**\n\n"
            "1. 🟢 Tizim & Status\n"
            "2. 📥 Ovoz Takliflari (Moderatsiya)\n"
            "3. 🎙 Ovozlar Ombori\n"
            "4. 📊 Statistika & Trendlar\n"
            "5. ⚠️ Xatoliklar & Audit\n\n"
            "Endi barcha tizim ushbu guruh bilan integratsiya qilingan holda ishlaydi!",
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Thread yaratishda xatolik: {e}")
        await wait_msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
