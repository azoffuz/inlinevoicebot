import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command
from config import config
from database.admins import is_admin
from database.settings import save_threads_config

logger = logging.getLogger(__name__)

router = Router()

@router.my_chat_member()
async def handle_bot_added_to_chat(event: ChatMemberUpdated, bot: Bot):
    """Agar bot ruxsat berilmagan begona guruhga qo'shilsa, avtomatik chiqib ketadi."""
    if event.chat.type in ["group", "supergroup"]:
        # Yangi qo'shilgan yoki a'zoligi tiklangan bo'lsa
        if event.new_chat_member.status in ["member", "administrator"]:
            if config.ADMIN_GROUP_ID and event.chat.id != config.ADMIN_GROUP_ID:
                try:
                    await bot.send_message(
                        chat_id=event.chat.id,
                        text="⛔️ Ushbu bot faqat rasmiy admin guruhida ishlashga mo'ljallangan. Ruxsatsiz foydalanish mumkin emas."
                    )
                    await bot.leave_chat(event.chat.id)
                    logger.warning(f"Ruxsatsiz begona guruhdan chiqib ketildi: {event.chat.id} ({event.chat.title})")
                except Exception as e:
                    logger.error(f"Guruhdan chiqishda xatolik: {e}")

@router.message(Command("setup_threads", "set_thread", "setthread"), F.chat.type.in_(["group", "supergroup"]))
async def cmd_setup_threads(message: Message, bot: Bot):
    """
    Guruhda admin threadlarini (Forum topics) avtomatik yaratish va sozlash.
    """
    # 1. Guruh ID si .env dagi ADMIN_GROUP_ID ga mos kelishini tekshirish
    if config.ADMIN_GROUP_ID and message.chat.id != config.ADMIN_GROUP_ID:
        return await message.reply("⛔️ Bu buyruq faqat .env da belgilangan rasmiy Admin guruhida ishlaydi!")

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
