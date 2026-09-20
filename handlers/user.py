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

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import config
from database.voices import get_top_voices
from database.admins import get_all_admins
from database.submissions import create_submission
from utils.keyboards import get_moderation_kb

class UserSubmitVoiceState(StatesGroup):
    waiting_for_media = State()
    waiting_for_title = State()

@router.message(Command("help"))
async def cmd_help(message: Message):
    """Yordam buyrug'i."""
    bot_user = await message.bot.get_me()
    text = (
        "📖 **Qo'llanma:**\n\n"
        f"1. Istalgan chatda `@{bot_user.username}` deb yozing.\n"
        "2. Ro'yxatdan eng mashhur ovozlardan birini tanlang va do'stlaringizga yuboring.\n"
        "3. `/top` — Eng ko'p eshitilgan trend ovozlar.\n"
        "4. `/effects` — Ovoz effektlari laboratoriyasi menyusi.\n"
        "5. `/addvoice` — O'zingiz ham yangi ovoz taklif qilishingiz mumkin (moderatsiyadan so'ng bazaga qo'shiladi!).\n"
        "6. Botga istalgan Voice (ovozli xabar) yoki MP3 musiqa yuboring, uni har xil effektlarda eshitib ko'rishingiz mumkin!"
    )
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("effects"))
async def cmd_effects(message: Message):
    """Ovoz effektlari menyusi va tushuntirish."""
    text = (
        "🎨 **Ovoz Effektlari Laboratoriyasi!**\n\n"
        "Menga shaxsiy chatda istalgan **Voice (ovozli xabar)** yoki **MP3 musiqa** yuboring, men uni quyidagi effektlarga aylantirib beraman:\n\n"
        "• 🎙 **Standart** — Toza ovozli xabar (.ogg Opus)\n"
        "• 🤖 **Robot** — Metallik robot ovozi\n"
        "• 🐿 **Chipmunk** — Kulgili multfilm qahramoni ovozi\n"
        "• 🔈 **Bas / Chuqur** — Maxluq / Yo'g'on ovoz\n"
        "• 🎈 **Geliy** — Geliy gazi yutgandek o'ta ingichka ovoz\n"
        "• 📻 **Ratsiya / Radio** — Harbiy ratsiya yoki eski radio effekti\n"
        "• 🌌 **Aks-sado** — Katta saroy yoki g'or aks-sadosi\n"
        "• ⚡️ **1.4x Tezlik** — Tezlashtirilgan ijro\n"
        "• 🐢 **0.75x Sekinlik** — Sekinlashtirilgan ijro\n\n"
        "🎙 *Hozirroq mikrofoni bosib biror narsa gapiring yoki musiqa tashlang!*"
    )
    await message.answer(text, parse_mode="Markdown")


@router.message(Command("top"))
async def cmd_top(message: Message):
    """Eng ko'p ishlatilgan trend ovozlarni ko'rsatish."""
    voices = await get_top_voices(limit=10)
    if not voices:
        return await message.answer("Hozircha ovozlar mavjud emas.")

    text = "🔥 **Eng ko'p jo'natilgan Top-10 ovozlar:**\n\n"
    for idx, v in enumerate(voices, start=1):
        text += f"{idx}. **{v.get('title')}** — 🚀 {v.get('usage_count', 0)} marta\n"
    text += "\nUlarni do'stlaringizga yuborish uchun istalgan chatda bot nomini yozing!"
    await message.answer(text, parse_mode="Markdown")

@router.message(Command("addvoice"))
async def cmd_addvoice(message: Message, state: FSMContext):
    """Foydalanuvchi tomonidan ovoz taklif qilish."""
    await state.set_state(UserSubmitVoiceState.waiting_for_media)
    await message.answer(
        "🎙 **Yangi ovoz taklif qilish:**\n\n"
        "Menga o'zingiz qo'shmoqchi bo'lgan **Voice (ovozli xabar)** yoki **Audio (MP3)** yuboring:\n\n"
        "(Bekor qilish uchun /cancel deb yozing)",
        parse_mode="Markdown"
    )

@router.message(UserSubmitVoiceState.waiting_for_media, F.voice | F.audio | (F.document & (
    F.document.mime_type.startswith("audio/") |
    F.document.file_name.ilike("%.mp3") |
    F.document.file_name.ilike("%.ogg") |
    F.document.file_name.ilike("%.wav") |
    F.document.file_name.ilike("%.m4a") |
    F.document.file_name.ilike("%.opus")
)))
async def process_user_voice_media(message: Message, state: FSMContext, bot: Bot):
    """Taklif qilinayotgan audio/voice qabul qilindi, endi nom so'raymiz."""
    media = message.voice or message.audio or message.document
    duration = getattr(media, "duration", 0)

    # Agar audio bo'lsa, uni avval voice qilib olamiz
    file_id = media.file_id
    if not message.voice:
        msg = await message.reply("⏳ Ovoz tayyorlanmoqda...")
        temp_dir = tempfile.gettempdir()
        input_path = None
        output_path = None
        try:
            file_info = await bot.get_file(file_id)
            ext = os.path.splitext(file_info.file_path)[1] or ".mp3"
            input_path = os.path.join(temp_dir, f"sub_{media.file_unique_id}{ext}")
            await bot.download_file(file_info.file_path, destination=input_path)
            output_path = await convert_audio_to_voice(input_path, effect="normal")
            
            # Adminga o'zimiz yuborishimiz uchun voice qilib yuboramiz
            voice_file = FSInputFile(output_path)
            sent_voice = await message.reply_voice(voice=voice_file, caption="🎙 Ovoz formati tayyorlandi!")
            file_id = sent_voice.voice.file_id
            duration = sent_voice.voice.duration
            await msg.delete()
        except Exception as e:
            logger.error(f"Taklif audio konvertatsiyasida xatolik: {e}")
            await msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
            return
        finally:
            if input_path and os.path.exists(input_path):
                try: os.remove(input_path)
                except Exception: pass
            if output_path and os.path.exists(output_path):
                try: os.remove(output_path)
                except Exception: pass

    await state.update_data(file_id=file_id, duration=duration)
    await state.set_state(UserSubmitVoiceState.waiting_for_title)
    await message.reply("Endi ushbu ovoz uchun nom (sarlavha) kiriting:")

@router.message(UserSubmitVoiceState.waiting_for_title, F.text)
async def process_user_voice_title(message: Message, state: FSMContext, bot: Bot):
    """Ovoz nomi kiritildi, moderatsiyaga yuborish."""
    title = message.text.strip()
    data = await state.get_data()
    await state.clear()

    file_id = data.get("file_id")
    duration = data.get("duration", 0)
    user = message.from_user

    user_name = user.full_name or user.username or str(user.id)
    if user.username:
        user_name += f" (@{user.username})"

    # 1. Supabase da taklif yaratish
    sub = await create_submission(
        user_id=user.id,
        user_name=user_name,
        title=title,
        file_id=file_id,
        duration=duration
    )

    if not sub:
        return await message.reply("❌ Xatolik: Taklifni saqlab bo'lmadi.")

    sub_id = str(sub.get("id"))

    await message.reply(
        f"✅ **Rahmat! Taklifingiz qabul qilindi.**\n\n"
        f"🎙 Nomi: **{title}**\n\n"
        f"⏳ Adminlar tomonidan tekshirilgach va tasdiqlangach, u darhol barcha uchun inline qidiruvga qo'shiladi va sizga xabar beramiz!",
        parse_mode="Markdown"
    )

    # 2. Moderatsiyaga yuborish (Guruhdagi 'Ovoz Takliflari' threadiga yoki adminlarga)
    from html import escape
    safe_name = escape(user_name)
    safe_title = escape(title)
    admin_caption = (
        f"📥 <b>Yangi ovoz taklifi!</b>\n\n"
        f"👤 Yuboruvchi: {safe_name} [ID: <code>{user.id}</code>]\n"
        f"🎙 Sarlavha: <b>{safe_title}</b>\n"
        f"🕒 Davomiyligi: {duration} sek"
    )

    from services.notifier import forward_submission_for_review
    delivered = await forward_submission_for_review(
        bot=bot,
        voice_file_id=file_id,
        caption=admin_caption,
        reply_markup=get_moderation_kb(sub_id)
    )

    if not delivered:
        logger.warning(f"Ovoz taklifi hech qaysi adminga yoki guruhga yetib bormadi! SUPERADMIN_ID: {config.SUPERADMIN_ID}, ADMIN_GROUP_ID: {config.ADMIN_GROUP_ID}")




@router.message(
    F.audio | F.voice | (F.document & (
        F.document.mime_type.startswith("audio/") |
        F.document.file_name.ilike("%.mp3") |
        F.document.file_name.ilike("%.ogg") |
        F.document.file_name.ilike("%.wav") |
        F.document.file_name.ilike("%.m4a") |
        F.document.file_name.ilike("%.opus")
    ))
)
async def handle_audio_message(message: Message, bot: Bot):
    """Foydalanuvchi MP3, Audio, Voice yoki OGG fayl yuborganda uni qabul qilish."""
    media = message.audio or message.voice or message.document
    if not media:
        return

    file_id = media.file_id
    user = message.from_user
    if user:
        try:
            await upsert_user(user.id, user.first_name or "", user.username or "")
        except Exception:
            pass

    is_adm = await is_admin(user.id) if user else False
    
    msg = await message.reply("⏳ Audio qayta ishlanmoqda...")

    
    temp_dir = tempfile.gettempdir()
    input_file_path = None
    output_voice_path = None
    
    try:
        # Faylni Telegramdan yuklab olish
        file_info = await bot.get_file(file_id)
        if not file_info.file_path:
            await msg.edit_text("❌ Telegramdan faylni yuklab olish imkoni bo'lmadi.")
            return

        # Fayl kengaytmasini aniqlash (.ogg, .mp3 va h.k.)
        ext = ""
        if hasattr(media, "file_name") and media.file_name:
            ext = os.path.splitext(media.file_name)[1]
        if not ext and file_info.file_path:
            ext = os.path.splitext(file_info.file_path)[1]
        if not ext:
            ext = ".ogg" if message.voice else ".mp3"

        input_file_path = os.path.join(temp_dir, f"input_{media.file_unique_id}{ext}")
        await bot.download_file(file_info.file_path, destination=input_file_path)

        # Standart normal ovozga aylantirish
        output_voice_path = await convert_audio_to_voice(input_file_path, effect="normal")

        # Ovozli xabar qilib jo'natish
        voice_file = FSInputFile(output_voice_path)
        caption = "🎙 Ovozli xabar tayyor!\nBoshqa effektlarda sinab ko'rish uchun quyidagi tugmalarni bosing:"
        
        await message.reply_voice(
            voice=voice_file,
            caption=caption,
            reply_markup=get_audio_convert_kb(is_adm=is_adm)
        )
        await msg.delete()

    except Exception as e:
        logger.error(f"Audio konvertatsiya xatosi: {e}")
        err_detail = str(e)
        if len(err_detail) > 300:
            err_detail = err_detail[-300:]
        await msg.edit_text(f"❌ Xatolik yuz berdi:\n`{err_detail}`", parse_mode="Markdown")
    finally:
        if input_file_path and os.path.exists(input_file_path):
            try:
                os.remove(input_file_path)
            except Exception:
                pass
        if output_voice_path and os.path.exists(output_voice_path):
            try:
                os.remove(output_voice_path)
            except Exception:
                pass


@router.callback_query(F.data.startswith("fx:"))
async def handle_convert_effects(callback: CallbackQuery, bot: Bot):
    """Tugma bosilganda effektlar bilan qayta konvertatsiya qilish."""
    effect = callback.data.split(":")[1]
    
    # Asl audio faylni topish
    media = None
    if callback.message.reply_to_message:
        orig = callback.message.reply_to_message
        media = orig.audio or orig.voice or orig.document
    if not media:
        media = callback.message.voice or callback.message.audio

    if not media:
        return await callback.answer("Audio fayl topilmadi.", show_alert=True)

    file_id = media.file_id
    await callback.answer(f"Effekt qo'llanmoqda: {effect}...")
    
    temp_dir = tempfile.gettempdir()
    input_path = None
    output_voice = None
    
    try:
        file_info = await bot.get_file(file_id)
        if not file_info.file_path:
            await callback.message.reply("❌ Fayl topilmadi.")
            return

        ext = os.path.splitext(file_info.file_path)[1] or ".ogg"
        input_path = os.path.join(temp_dir, f"fx_in_{media.file_unique_id}{ext}")

        await bot.download_file(file_info.file_path, destination=input_path)
        output_voice = await convert_audio_to_voice(input_path, effect=effect)

        voice_file = FSInputFile(output_voice)
        effect_names = {
            "normal": "🎙 Standart",
            "robot": "🤖 Robot ovoz",
            "chipmunk": "🐿 Chipmunk (Multfilm)",
            "deep": "🔈 Chuqur / Bas",
            "helium": "🎈 Geliy (Ingichka)",
            "radio": "📻 Ratsiya / Radio",
            "echo": "🌌 Aks-sado (Katta zal)",
            "fast": "⚡️ 1.4x Tezlik",
            "slow": "🐢 0.75x Sekinlik"
        }
        await callback.message.reply_voice(
            voice=voice_file,
            caption=f"✨ **Ovoz effekti:** {effect_names.get(effect, effect)}\nBoshqa effektlarni ham sinab ko'rishingiz mumkin:",
            reply_markup=get_audio_convert_kb(),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Effekt konvertatsiya xatosi: {e}")
        await callback.message.reply(f"❌ Xatolik: {e}")
    finally:
        if input_path and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass
        if output_voice and os.path.exists(output_voice):
            try:
                os.remove(output_voice)
            except Exception:
                pass


@router.callback_query(F.data == "suggest_voice")
async def cb_suggest_voice_from_audio(callback: CallbackQuery, state: FSMContext):
    """MP3 konvert qilingach 'Bazaga taklif qilish' tugmasi bosilganda."""
    media = callback.message.voice or callback.message.audio
    if not media and callback.message.reply_to_message:
        orig = callback.message.reply_to_message
        media = orig.voice or orig.audio or orig.document
    
    if not media:
        return await callback.answer("Audio topilmadi.", show_alert=True)
        
    await state.set_state(UserSubmitVoiceState.waiting_for_title)
    await state.update_data(file_id=media.file_id, duration=getattr(media, "duration", 0))
    await callback.message.reply("Ushbu ovoz uchun nom (sarlavha) yozing:\n\n(Masalan: Gap yo'q brat)")
    await callback.answer()


