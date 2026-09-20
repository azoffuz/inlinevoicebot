import os
import tempfile
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from database.users import upsert_user
from database.admins import is_admin
from services.audio_converter import convert_audio_to_voice
from utils.keyboards import get_audio_convert_kb, get_admin_menu_kb

logger = logging.getLogger(__name__)

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Start buyrug'i."""
    user = message.from_user
    if user:
        await upsert_user(
            user_id=user.id,
            first_name=user.first_name or "",
            username=user.username or ""
        )
    
    bot_user = await message.bot.get_me()
    is_adm = await is_admin(user.id) if user else False
    
    text = (
        f"Assalomu alaykum, {user.first_name if user else 'foydalanuvchi'}! 🎙\n\n"
        f"Men **Inline Voice Bot**man.\n\n"
        f"⚡️ **Qanday ishlatiladi?**\n"
        f"Istalgan chatga boring va shunchaki yozing:\n"
        f"`@{bot_user.username}`\n"
        f"Hech narsa yozish shart emas — eng ko'p jo'natilgan ovozlar darhol chiqadi!\n\n"
        f"🎵 **MP3 -> Voice Konverter:**\n"
        f"Menga istalgan musiqa yoki audio yuboring, men uni Telegram ovozli xabari (Voice) qilib beraman!"
    )
    
    if is_adm:
        text += "\n\n🛠 Siz adminsiz! Admin panel uchun /admin buyrug'ini bosing."
        
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Yordam buyrug'i."""
    bot_user = await message.bot.get_me()
    text = (
        "📖 **Qo'llanma:**\n\n"
        f"1. Istalgan chatda `@{bot_user.username}` deb yozing.\n"
        "2. Ro'yxatdan eng mashhur ovozlardan birini tanlang va do'stlaringizga yuboring.\n"
        "3. Agar muayyan ovozni qidirmoqchi bo'lsangiz, nomini yozishingiz ham mumkin.\n"
        "4. Botga MP3 audio yuborsangiz, uni voice qilib beradi."
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(F.audio | (F.document & F.document.mime_type.startswith("audio/")))
async def handle_audio_message(message: Message, bot: Bot):
    """Foydalanuvchi MP3/Audio fayl yuborganda uni qabul qilish."""
    audio = message.audio or message.document
    if not audio:
        return

    file_id = audio.file_id
    user = message.from_user
    is_adm = await is_admin(user.id) if user else False
    
    msg = await message.reply("⏳ Audio qayta ishlanmoqda...")
    
    # Vaqtinchalik fayllar
    temp_dir = tempfile.gettempdir()
    input_file_path = os.path.join(temp_dir, f"input_{audio.file_unique_id}")
    output_voice_path = None
    
    try:
        # Faylni Telegramdan yuklab olish
        file_info = await bot.get_file(file_id)
        if not file_info.file_path:
            await msg.edit_text("❌ Faylni yuklab olishda xatolik yuz berdi.")
            return

        await bot.download_file(file_info.file_path, destination=input_file_path)

        # Standart normal ovozga aylantirish
        output_voice_path = await convert_audio_to_voice(input_file_path, effect="normal")

        # Ovozli xabar qilib jo'natish
        voice_file = FSInputFile(output_voice_path)
        caption = "🎙 Ovozli xabar tayyor!\nBoshqa effektlarda sinab ko'rish uchun quyidagi tugmalarni bosing:"
        
        await message.reply_voice(
            voice=voice_file,
            caption=caption,
            reply_markup=get_audio_convert_kb(file_id, is_adm=is_adm)
        )
        await msg.delete()

    except Exception as e:
        logger.error(f"Audio konvertatsiya xatosi: {e}")
        await msg.edit_text(f"❌ Xatolik yuz berdi: Audio faylni qayta ishlab bo'lmadi.")
    finally:
        # Fayllarni tozalash
        if os.path.exists(input_file_path):
            try:
                os.remove(input_file_path)
            except Exception:
                pass
        if output_voice_path and os.path.exists(output_voice_path):
            try:
                os.remove(output_voice_path)
            except Exception:
                pass

@router.callback_query(F.data.startswith("conv:"))
async def handle_convert_effects(callback: CallbackQuery, bot: Bot):
    """Tugma bosilganda effektlar bilan qayta konvertatsiya qilish."""
    parts = callback.data.split(":")
    if len(parts) < 3:
        return
    
    effect = parts[1]
    file_id = parts[2]
    
    await callback.answer(f"Effekt qo'llanmoqda: {effect}...")
    
    temp_dir = tempfile.gettempdir()
    input_path = os.path.join(temp_dir, f"fx_in_{file_id[-10:]}")
    output_voice = None
    
    try:
        file_info = await bot.get_file(file_id)
        if not file_info.file_path:
            await callback.message.reply("❌ Fayl topilmadi.")
            return

        await bot.download_file(file_info.file_path, destination=input_path)
        output_voice = await convert_audio_to_voice(input_path, effect=effect)

        voice_file = FSInputFile(output_voice)
        effect_names = {
            "normal": "🎙 Standart",
            "robot": "🤖 Robot",
            "chipmunk": "🐿 Chipmunk (Tez)",
            "deep": "🔈 Chuqur / Bas"
        }
        await callback.message.reply_voice(
            voice=voice_file,
            caption=f"Ovoz effekti: {effect_names.get(effect, effect)}"
        )
    except Exception as e:
        logger.error(f"Effekt konvertatsiya xatosi: {e}")
        await callback.message.reply("❌ Ovoz effektini qo'llashda xatolik yuz berdi.")
    finally:
        if os.path.exists(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass
        if output_voice and os.path.exists(output_voice):
            try:
                os.remove(output_voice)
            except Exception:
                pass
