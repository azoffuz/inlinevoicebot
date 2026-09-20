import os
import tempfile
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from config import config
from database.admins import is_admin, is_superadmin, add_admin, remove_admin, get_all_admins
from database.voices import add_voice, get_top_voices, delete_voice, get_total_voices_count
from database.users import get_total_users_count, get_all_user_ids
from services.audio_converter import convert_audio_to_voice
from utils.keyboards import get_admin_menu_kb, get_back_to_admin_kb

logger = logging.getLogger(__name__)

router = Router()

class AddVoiceState(StatesGroup):
    waiting_for_media = State()
    waiting_for_title = State()

class AddAdminState(StatesGroup):
    waiting_for_admin_id = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()

@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    """Admin panelga kirish."""
    await state.clear()
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.reply("⛔️ Kechirasiz, sizda adminlik huquqi yo'q.")
        return

    is_super = await is_superadmin(user_id)
    await message.answer(
        "🛠 **Admin Boshqaruv Paneli**\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=get_admin_menu_kb(is_super=is_super),
        parse_mode="Markdown"
    )

@router.callback_query(F.data == "admin_main_menu")
async def cb_admin_main_menu(callback: CallbackQuery, state: FSMContext):
    """Asosiy admin menyusiga qaytish."""
    await state.clear()
    user_id = callback.from_user.id
    if not await is_admin(user_id):
        return await callback.answer("Ruxsat berilmagan!", show_alert=True)

    is_super = await is_superadmin(user_id)
    await callback.message.edit_text(
        "🛠 **Admin Boshqaruv Paneli**\n\nQuyidagi bo'limlardan birini tanlang:",
        reply_markup=get_admin_menu_kb(is_super=is_super),
        parse_mode="Markdown"
    )
    await callback.answer()

# --- STATISTIKA ---
@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    """Bot statistikasini ko'rsatish."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    total_voices = await get_total_voices_count()
    total_users = await get_total_users_count()
    top_voices = await get_top_voices(limit=5)

    text = (
        "📊 **Bot Statistikasi:**\n\n"
        f"👥 Jami foydalanuvchilar: **{total_users}** ta\n"
        f"🎙 Jami ovozlar: **{total_voices}** ta\n\n"
        "🔥 **Top 5 eng ko'p jo'natilgan ovozlar:**\n"
    )

    if top_voices:
        for idx, v in enumerate(top_voices, start=1):
            text += f"{idx}. {v.get('title')} — 🚀 {v.get('usage_count', 0)} marta\n"
    else:
        text += "Hali ovozlar mavjud emas.\n"

    await callback.message.edit_text(text, reply_markup=get_back_to_admin_kb(), parse_mode="Markdown")
    await callback.answer()

# --- YANGI OVOZ QO'SHISH ---
@router.callback_query(F.data == "admin_add_voice")
async def cb_admin_add_voice(callback: CallbackQuery, state: FSMContext):
    """Ovoz qo'shish jarayonini boshlash."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    await state.set_state(AddVoiceState.waiting_for_media)
    await callback.message.edit_text(
        "🎙 Yangi ovozni qo'shish uchun menga **Voice** yoki **MP3 audio** yuboring:\n\n"
        "(Bekor qilish uchun /cancel deb yozing)",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer()

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Jarayonni bekor qilish."""
    current_state = await state.get_state()
    if current_state is None:
        return
    await state.clear()
    await message.reply("❌ Amal bekor qilindi.", reply_markup=get_admin_menu_kb(await is_superadmin(message.from_user.id)))

@router.message(AddVoiceState.waiting_for_media, F.voice | F.audio | (F.document & F.document.mime_type.startswith("audio/")))
async def process_voice_media(message: Message, state: FSMContext, bot: Bot):
    """Audio yoki Voice qabul qilindi, endi nom so'raymiz."""
    voice = message.voice
    audio = message.audio or message.document
    
    if voice:
        await state.update_data(file_id=voice.file_id, file_unique_id=voice.file_unique_id, duration=voice.duration, is_audio=False)
    elif audio:
        await state.update_data(file_id=audio.file_id, file_unique_id=audio.file_unique_id, duration=getattr(audio, "duration", 0), is_audio=True)
    
    await state.set_state(AddVoiceState.waiting_for_title)
    await message.reply("Endi ushbu ovoz uchun nom (sarlavha) kiriting:")

@router.message(AddVoiceState.waiting_for_title, F.text)
async def process_voice_title(message: Message, state: FSMContext, bot: Bot):
    """Ovoz nomi kiritildi, kanalga va bazaga saqlash."""
    title = message.text.strip()
    data = await state.get_data()
    await state.clear()

    file_id = data.get("file_id")
    file_unique_id = data.get("file_unique_id")
    duration = data.get("duration", 0)
    is_audio = data.get("is_audio", False)

    msg = await message.reply("⏳ Ovoz tayyorlanmoqda va kanalga yuklanmoqda...")

    final_voice_file_id = file_id
    final_unique_id = file_unique_id
    channel_msg_id = None

    temp_dir = tempfile.gettempdir()
    input_path = None
    output_path = None

    try:
        # Agar audio (MP3) bo'lsa, uni avval voice (.ogg) ga o'tkazish kerak
        if is_audio:
            input_path = os.path.join(temp_dir, f"add_in_{file_unique_id}")
            file_info = await bot.get_file(file_id)
            if not file_info.file_path:
                await msg.edit_text("❌ Faylni yuklab olishda xatolik yuz berdi.")
                return
            await bot.download_file(file_info.file_path, destination=input_path)
            output_path = await convert_audio_to_voice(input_path, effect="normal")
            voice_to_send = FSInputFile(output_path)
        else:
            voice_to_send = file_id

        # Telegram kanalga (storage) yuborish
        if config.STORAGE_CHANNEL_ID:
            sent_voice = await bot.send_voice(
                chat_id=config.STORAGE_CHANNEL_ID,
                voice=voice_to_send,
                caption=f"🎙 {title}"
            )
            final_voice_file_id = sent_voice.voice.file_id
            final_unique_id = sent_voice.voice.file_unique_id
            duration = sent_voice.voice.duration
            channel_msg_id = sent_voice.message_id
        elif is_audio and output_path:
            # Agar kanal bo'lmasa ham adminga o'ziga yuborib file_id olamiz
            sent_voice = await message.reply_voice(voice=voice_to_send, caption=f"🎙 {title}")
            final_voice_file_id = sent_voice.voice.file_id
            final_unique_id = sent_voice.voice.file_unique_id
            duration = sent_voice.voice.duration

        # Supabase bazasiga saqlash
        saved = await add_voice(
            title=title,
            file_id=final_voice_file_id,
            file_unique_id=final_unique_id,
            duration=duration,
            channel_message_id=channel_msg_id,
            created_by=message.from_user.id
        )

        if saved:
            await msg.edit_text(
                f"✅ **Muvaffaqiyatli saqlandi!**\n\n"
                f"🎙 Nomi: **{title}**\n"
                f"🕒 Davomiyligi: {duration} sek\n\n"
                f"Endi ushbu ovoz inline qidiruvda darhol chiqadi!",
                reply_markup=get_back_to_admin_kb(),
                parse_mode="Markdown"
            )
        else:
            await msg.edit_text("⚠️ Fayl saqlanmadi (Supabase ulanishini tekshiring).", reply_markup=get_back_to_admin_kb())

    except Exception as e:
        logger.error(f"Ovoz saqlash xatosi: {e}")
        await msg.edit_text(f"❌ Xatolik yuz berdi: {e}", reply_markup=get_back_to_admin_kb())
    finally:
        if input_path and os.path.exists(input_path):
            try:
                os.remove(input_path)
            except Exception:
                pass
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass

# --- OVOZLAR RO'YXATI VA O'CHIRISH ---
@router.callback_query(F.data.startswith("admin_list_voices_"))
async def cb_admin_list_voices(callback: CallbackQuery):
    """Mavjud ovozlarni sahifalab ko'rish va o'chirish."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    offset = int(callback.data.split("_")[-1])
    limit = 6
    voices = await get_top_voices(limit=limit, offset=offset)
    total = await get_total_voices_count()

    if not voices:
        await callback.message.edit_text(
            "📂 Hozircha ovozlar yo'q.",
            reply_markup=get_back_to_admin_kb()
        )
        return await callback.answer()

    keyboard = []
    for v in voices:
        keyboard.append([
            InlineKeyboardButton(text=f"🗑 {v.get('title')} ({v.get('usage_count', 0)}x)", callback_data=f"del_voice:{v['id']}")
        ])

    nav_row = []
    if offset > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"admin_list_voices_{max(0, offset - limit)}"))
    if offset + limit < total:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"admin_list_voices_{offset + limit}"))
    
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_main_menu")])

    await callback.message.edit_text(
        f"📂 **Ovozlar ro'yxati** (Jami: {total} ta):\nO'chirish uchun ovoz ustiga bosing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.callback_query(F.data.startswith("del_voice:"))
async def cb_delete_voice(callback: CallbackQuery):
    """Ovozni bazadan o'chirish."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    voice_id = callback.data.split(":")[1]
    success = await delete_voice(voice_id)
    if success:
        await callback.answer("✅ Ovoz o'chirildi!", show_alert=True)
        # Ro'yxatni yangilash
        await cb_admin_list_voices(callback)
    else:
        await callback.answer("❌ O'chirishda xatolik yuz berdi.", show_alert=True)

# --- ADMINLAR BOSHQARUVI (SUPERADMIN UCHUN) ---
@router.callback_query(F.data == "admin_manage_admins")
async def cb_manage_admins(callback: CallbackQuery):
    """Adminlar ro'yxati va yangi admin qo'shish."""
    if not await is_superadmin(callback.from_user.id):
        return await callback.answer("Faqat Superadmin uchun!", show_alert=True)

    admins = await get_all_admins()
    text = f"👥 **Adminlar Boshqaruvi**\n\n👑 Asosiy Superadmin ID: `{config.SUPERADMIN_ID}`\n\n**Qo'shimcha Adminlar:**\n"

    keyboard = [
        [InlineKeyboardButton(text="➕ Yangi Admin qo'shish", callback_data="admin_add_new_admin")]
    ]

    if admins:
        for adm in admins:
            u_id = adm.get("user_id")
            name = adm.get("full_name") or adm.get("username") or str(u_id)
            text += f"• {name} (ID: `{u_id}`)\n"
            keyboard.append([
                InlineKeyboardButton(text=f"❌ {name} ni o'chirish", callback_data=f"del_admin:{u_id}")
            ])
    else:
        text += "Qo'shimcha adminlar yo'q.\n"

    keyboard.append([InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_main_menu")])

    await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")
    await callback.answer()

@router.callback_query(F.data == "admin_add_new_admin")
async def cb_add_new_admin(callback: CallbackQuery, state: FSMContext):
    """Yangi admin qo'shish ID so'rash."""
    if not await is_superadmin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    await state.set_state(AddAdminState.waiting_for_admin_id)
    await callback.message.edit_text(
        "Yangi admin qilmoqchi bo'lgan foydalanuvchining **Telegram ID** sini yuboring:\n\n(Bekor qilish uchun /cancel)",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer()

@router.message(AddAdminState.waiting_for_admin_id, F.text)
async def process_new_admin_id(message: Message, state: FSMContext):
    """Admin ID qabul qilinishi va saqlanishi."""
    text = message.text.strip()
    if not text.isdigit():
        return await message.reply("Iltimos, faqat raqamlardan iborat Telegram ID yuboring!")

    new_admin_id = int(text)
    await state.clear()

    ok = await add_admin(user_id=new_admin_id, full_name=f"Admin {new_admin_id}")
    if ok:
        await message.reply(f"✅ Foydalanuvchi `{new_admin_id}` admin sifatida qo'shildi!", parse_mode="Markdown")
    else:
        await message.reply("❌ Admin qo'shishda xatolik yuz berdi.")

@router.callback_query(F.data.startswith("del_admin:"))
async def cb_del_admin(callback: CallbackQuery):
    """Adminni olib tashlash."""
    if not await is_superadmin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    admin_id = int(callback.data.split(":")[1])
    ok = await remove_admin(admin_id)
    if ok:
        await callback.answer("✅ Admin muvaffaqiyatli olib tashlandi!", show_alert=True)
        await cb_manage_admins(callback)
    else:
        await callback.answer("❌ O'chirishda xatolik yuz berdi.", show_alert=True)

# --- BROADCAST (XABAR TARQATISH) ---
@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast boshlash."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.edit_text(
        "📢 Barcha foydalanuvchilarga yuboriladigan xabarni kiriting:\n\n(Bekor qilish uchun /cancel)",
        reply_markup=get_back_to_admin_kb()
    )
    await callback.answer()

@router.message(BroadcastState.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    """Xabarni barcha foydalanuvchilarga yuborish."""
    await state.clear()
    user_ids = await get_all_user_ids()

    if not user_ids:
        return await message.reply("Foydalanuvchilar bazada mavjud emas.")

    msg = await message.reply(f"⏳ {len(user_ids)} ta foydalanuvchiga xabar yuborilmoqda...")
    sent = 0
    failed = 0

    for uid in user_ids:
        try:
            await message.copy_to(chat_id=uid)
            sent += 1
        except Exception:
            failed += 1

    await msg.edit_text(
        f"📢 **Xabar tarqatish yakunlandi!**\n\n"
        f"✅ Yuborildi: {sent}\n"
        f"❌ Xatolik: {failed}",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="Markdown"
    )
