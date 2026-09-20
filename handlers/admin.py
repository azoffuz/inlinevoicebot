import os
import asyncio
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
from database.submissions import get_submission, update_submission_status
from database.channels import get_required_channels, add_required_channel, remove_required_channel
from database.backup import create_database_backup
from services.audio_converter import convert_audio_to_voice
from utils.keyboards import get_admin_menu_kb, get_back_to_admin_kb


logger = logging.getLogger(__name__)

router = Router()

class AddVoiceState(StatesGroup):
    waiting_for_media = State()
    waiting_for_title = State()

class AddAdminState(StatesGroup):
    waiting_for_admin_id = State()

class AddChannelState(StatesGroup):
    waiting_for_channel_info = State()

class BroadcastState(StatesGroup):
    waiting_for_message = State()
    waiting_for_confirm = State()


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
            file_info = await bot.get_file(file_id)
            if not file_info.file_path:
                await msg.edit_text("❌ Faylni yuklab olishda xatolik yuz berdi.")
                return
            ext = os.path.splitext(file_info.file_path)[1] or ".mp3"
            input_path = os.path.join(temp_dir, f"add_in_{file_unique_id}{ext}")
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

# --- BROADCAST (REKLAMA VA XABAR TARQATISH) ---
@router.callback_query(F.data == "admin_broadcast")
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Broadcast boshlash."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    total_users = await get_total_users_count()
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.edit_text(
        f"📢 **Reklama va Xabar Tarqatish Bo'limi**\n\n"
        f"👥 Hozirda botda: **{total_users}** ta foydalanuvchi mavjud.\n\n"
        "Tarqatmoqchi bo'lgan xabaringizni menga yuboring:\n"
        "*(Matn, Rasm, Video, Audio, Havolali post yoki Forward qilingan xabar bo'lishi mumkin)*\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(BroadcastState.waiting_for_message)
async def process_broadcast_preview(message: Message, state: FSMContext, bot: Bot):
    """Admin yuborgan xabarni qabul qilish va oldindan ko'rsatish (Preview)."""
    user_ids = await get_all_user_ids()
    total_count = len(user_ids)

    if total_count == 0:
        await state.clear()
        return await message.reply("Foydalanuvchilar bazada mavjud emas.")

    # Xabar parametrlarini state ga saqlaymiz
    await state.update_data(
        from_chat_id=message.chat.id,
        broadcast_msg_id=message.message_id
    )
    await state.set_state(BroadcastState.waiting_for_confirm)

    # 1. Reklama xabarining o'zini adminga ko'rsatamiz (Preview)
    await message.reply("👁 **Reklama xabaringiz foydalanuvchilarga shunday ko'rinadi:**")
    await bot.copy_message(chat_id=message.chat.id, from_chat_id=message.chat.id, message_id=message.message_id)

    # 2. Tasdiqlash tugmalari
    confirm_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"🚀 Yuborishni boshlash ({total_count} ta)", callback_data="bcast_confirm")
        ],
        [
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="bcast_cancel")
        ]
    ])

    await message.answer(
        f"❓ **Xabarni barcha {total_count} ta foydalanuvchiga yuborishni tasdiqlaysizmi?**",
        reply_markup=confirm_kb,
        parse_mode="Markdown"
    )

@router.callback_query(BroadcastState.waiting_for_confirm, F.data == "bcast_confirm")
async def cb_broadcast_execute(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Admin tasdiqlagach, barcha foydalanuvchilarga xabarni tarqatish."""
    data = await state.get_data()
    await state.clear()

    from_chat_id = data.get("from_chat_id")
    broadcast_msg_id = data.get("broadcast_msg_id")

    if not from_chat_id or not broadcast_msg_id:
        return await callback.message.edit_text("❌ Xatolik: Xabar topilmadi.", reply_markup=get_back_to_admin_kb())

    user_ids = await get_all_user_ids()
    total = len(user_ids)

    progress_msg = await callback.message.edit_text(
        f"⏳ **Reklama tarqatish boshlandi...**\n\n"
        f"📊 Holat: 0 / {total} (0%)\n"
        f"✅ Yetkazildi: 0\n"
        f"❌ Xatolik / Blok: 0",
        parse_mode="Markdown"
    )

    sent = 0
    failed = 0

    for idx, uid in enumerate(user_ids, start=1):
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=broadcast_msg_id
            )
            sent += 1
        except Exception as e:
            logger.warning(f"Broadcast xatosi (user_id: {uid}): {e}")
            failed += 1


        # Har 25 ta xabarda progressni yangilash
        if idx % 25 == 0 or idx == total:
            percent = int((idx / total) * 100)
            try:
                await progress_msg.edit_text(
                    f"⏳ **Reklama tarqatilmoqda...**\n\n"
                    f"📊 Holat: {idx} / {total} ({percent}%)\n"
                    f"✅ Yetkazildi: {sent}\n"
                    f"❌ Xatolik / Blok: {failed}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        # Telegram Flood limitidan himoyalanish (sekundiga ~25-30 xabar)
        await asyncio.sleep(0.04)

    await progress_msg.edit_text(
        f"🎉 **Reklama tarqatish yakunlandi!**\n\n"
        f"👥 Jami foydalanuvchilar: **{total}** ta\n"
        f"✅ Muvaffaqiyatli yetkazildi: **{sent}** ta\n"
        f"❌ Bloklaganlar / Xatolik: **{failed}** ta",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="Markdown"
    )
    await callback.answer("Reklama muvaffaqiyatli tarqatildi!", show_alert=True)

@router.callback_query(BroadcastState.waiting_for_confirm, F.data == "bcast_cancel")
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    """Reklama tarqatishni bekor qilish."""
    await state.clear()
    await callback.message.edit_text(
        "❌ **Reklama tarqatish bekor qilindi.**",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="Markdown"
    )
    await callback.answer("Bekor qilindi.")


# --- MODERATSIYA (OVOZLARNI TASDIQLASH VA RAD ETISH) ---
@router.callback_query(F.data.startswith("appv:"))
async def cb_approve_submission(callback: CallbackQuery, bot: Bot):
    """Admin tomonidan foydalanuvchi taklifini tasdiqlash."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    sub_id = callback.data.split(":")[1]
    sub = await get_submission(sub_id)

    if not sub:
        return await callback.answer("Taklif topilmadi yoki eskirgan.", show_alert=True)

    if sub.get("status") != "pending":
        return await callback.answer(f"Ushbu taklif allaqachon ko'rib chiqilgan ({sub.get('status')})!", show_alert=True)

    await callback.answer("Tasdiqlanmoqda...")
    title = sub.get("title", "Voice")
    user_id = sub.get("user_id")
    file_id = sub.get("file_id")

    final_voice_id = file_id
    final_unique_id = None
    duration = sub.get("duration", 0)
    channel_msg_id = None

    try:
        from services.notifier import upload_voice_to_storage
        # Ovozni saqlash omboriga (guruhdagi storage thread yoki kanalga) yuborish
        caption = f"🎙 {title} (Yuboruvchi: {sub.get('user_name')})"
        f_id, f_uniq_id, dur, ch_msg_id = await upload_voice_to_storage(
            bot=bot,
            voice_input=file_id,
            caption=caption
        )

        final_voice_id = f_id or file_id
        final_unique_id = f_uniq_id
        duration = dur or duration
        channel_msg_id = ch_msg_id

        # Asosiy voices jadvaliga saqlash
        await add_voice(
            title=title,
            file_id=final_voice_id,
            file_unique_id=final_unique_id or f"sub_{sub_id[:12]}",
            duration=duration,
            channel_message_id=channel_msg_id,
            created_by=user_id
        )

        # Holatni yangilash
        await update_submission_status(sub_id, "approved")

        # Guruhdan so'rov xabarini o'chirish (agar guruhda bo'lsa)
        if callback.message.chat.type in ["group", "supergroup"]:
            try:
                await callback.message.delete()
            except Exception:
                pass
            await callback.answer("✅ Ovoz tasdiqlandi va omborga saqlandi! So'rov o'chirildi.", show_alert=True)
        else:
            current_caption = callback.message.caption or ""
            await callback.message.edit_caption(
                caption=f"{current_caption}\n\n✅ **TASDIQLANDI VA BAZAGA QO'SHILDI!**",
                reply_markup=None,
                parse_mode="Markdown"
            )
            await callback.answer("✅ Tasdiqlandi!")

        # Foydalanuvchiga xushxabar yuborish
        try:
            bot_me = await bot.get_me()
            await bot.send_message(
                chat_id=user_id,
                text=(
                    f"🎉 **Ajoyib xabar!**\n\n"
                    f"Siz taklif qilgan **\"{title}\"** ovozi adminlar tomonidan tasdiqlandi va umumiy bazaga qo'shildi!\n\n"
                    f"Endi uni istalgan chatda `@{bot_me.username}` orqali yuborishingiz mumkin! 🚀"
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Taklifni tasdiqlashda xatolik: {e}")
        await callback.message.reply(f"❌ Xatolik yuz berdi: {e}")

@router.callback_query(F.data.startswith("rjct:"))
async def cb_reject_submission(callback: CallbackQuery, bot: Bot):
    """Admin tomonidan foydalanuvchi taklifini rad etish."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    sub_id = callback.data.split(":")[1]
    sub = await get_submission(sub_id)

    if not sub:
        return await callback.answer("Taklif topilmadi.", show_alert=True)

    if sub.get("status") != "pending":
        return await callback.answer("Bu taklif allaqachon ko'rib chiqilgan!", show_alert=True)

    await update_submission_status(sub_id, "rejected")

    # Guruhdan so'rov xabarini o'chirish
    if callback.message.chat.type in ["group", "supergroup"]:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await callback.answer("❌ Ovoz rad etildi va guruhdan o'chirildi.", show_alert=True)
    else:
        current_caption = callback.message.caption or ""
        await callback.message.edit_caption(
            caption=f"{current_caption}\n\n❌ **RAD ETILDI.**",
            reply_markup=None,
            parse_mode="Markdown"
        )
        await callback.answer("Rad etildi.")

    # Foydalanuvchiga xabar berish
    user_id = sub.get("user_id")
    title = sub.get("title", "Voice")
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"Kechirasiz, siz taklif qilgan **\"{title}\"** ovozi moderatorlar tomonidan rad etildi.",
            parse_mode="Markdown"
        )
    except Exception:
        pass

# --- MAJBURIY OBUNA KANALLARI BOSHQARUVI ---
@router.callback_query(F.data == "admin_channels")
async def cb_admin_channels(callback: CallbackQuery):
    """Majburiy kanallar ro'yxatini ko'rsatish."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    channels = await get_required_channels()
    text = (
        "📢 **Majburiy Obuna Kanallari Boshqaruvi**\n\n"
        "Foydalanuvchilar botdan to'liq foydalanishlari uchun quyidagi kanallarga a'zo bo'lishlari so'raladi.\n\n"
    )
    if not channels:
        text += "*(Hozircha majburiy kanallar qo'shilmagan)*"
    else:
        text += f"Jami kanallar: **{len(channels)}** ta\n\n"
        for idx, ch in enumerate(channels, start=1):
            text += f"{idx}. **{ch.get('name')}** (`{ch.get('channel_id')}`)\n🔗 {ch.get('url')}\n\n"

    keyboard = []
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(text=f"🗑 O'chirish: {ch.get('name')}", callback_data=f"del_channel:{ch.get('channel_id')}")
        ])
    keyboard.append([
        InlineKeyboardButton(text="➕ Yangi kanal qo'shish", callback_data="add_channel")
    ])
    keyboard.append([
        InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_main_menu")
    ])

    await callback.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="Markdown",
        disable_web_page_preview=True
    )
    await callback.answer()

@router.callback_query(F.data == "add_channel")
async def cb_add_channel_prompt(callback: CallbackQuery, state: FSMContext):
    """Yangi kanal qo'shish uchun ma'lumot so'rash."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    await state.set_state(AddChannelState.waiting_for_channel_info)
    await callback.message.edit_text(
        "📢 **Yangi majburiy kanal qo'shish:**\n\n"
        "Kanal ma'lumotlarini quyidagi formatda yuboring:\n"
        "`KANAL_ID | KANAL_NOMI | KANAL_LINKI`\n\n"
        "Misol:\n"
        "`-100123456789 | Mening Kanalim | https://t.me/kanalim`\n\n"
        "*(Eslatma: Bot ushbu kanalda administrator bo'lishi kerak!)*\n\n"
        "Bekor qilish uchun: /cancel",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(AddChannelState.waiting_for_channel_info, F.text)
async def process_add_channel(message: Message, state: FSMContext, bot: Bot):
    """Kanal ma'lumotlarini qabul qilish va saqlash."""
    if not await is_admin(message.from_user.id):
        return

    text = message.text.strip()
    if "|" not in text:
        return await message.reply(
            "Iltimos, formatga rioya qiling!\n\n"
            "`KANAL_ID | KANAL_NOMI | KANAL_LINKI`\n"
            "Misol:\n`-100123456789 | Mening Kanalim | https://t.me/kanalim`",
            parse_mode="Markdown"
        )

    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 3:
        return await message.reply("Barcha 3 ta maydonni to'ldiring: KANAL_ID | KANAL_NOMI | KANAL_LINKI")

    channel_id, name, url = parts[0], parts[1], parts[2]

    # Botning kanaldagi huquqini tekshirish
    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=(await bot.get_me()).id)
        if member.status not in ["administrator", "creator"]:
            return await message.reply("⚠️ Bot ushbu kanalda administrator emas! Botga kanalda admin huquqini berib, qaytadan urinib ko'ring.")
    except Exception as e:
        logger.warning(f"Kanal huquqini tekshirishda ogohlantirish ({channel_id}): {e}")

    ok = await add_required_channel(channel_id=channel_id, name=name, url=url)
    await state.clear()

    if ok:
        await message.reply(
            f"✅ **Kanal muvaffaqiyatli qo'shildi!**\n\n"
            f"📢 Nomi: **{name}**\n"
            f"🆔 ID: `{channel_id}`\n"
            f"🔗 Havola: {url}",
            reply_markup=get_back_to_admin_kb(),
            parse_mode="Markdown"
        )
    else:
        await message.reply("❌ Kanalni saqlashda xatolik yuz berdi.", reply_markup=get_back_to_admin_kb())

@router.callback_query(F.data.startswith("del_channel:"))
async def cb_delete_channel(callback: CallbackQuery):
    """Kanalni ro'yxatdan o'chirish."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    channel_id = callback.data.split(":")[1]
    ok = await remove_required_channel(channel_id)
    if ok:
        await callback.answer("✅ Kanal olib tashlandi!", show_alert=True)
        await cb_admin_channels(callback)
    else:
        await callback.answer("❌ O'chirishda xatolik yuz berdi.", show_alert=True)

# --- DATABASE BACKUP EXPORT ---
@router.callback_query(F.data == "admin_backup")
async def cb_admin_backup(callback: CallbackQuery, bot: Bot):
    """Supabase bazasi to'liq zaxira nusxasini (JSON) eksport qilish va yuborish."""
    if not await is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q!", show_alert=True)

    await callback.answer("Zaxira nusxasi tayyorlanmoqda...")
    msg = await callback.message.reply("⏳ Baza ma'lumotlari to'planmoqda va eksport qilinmoqda...")

    backup_path = None
    try:
        backup_path, counts = await create_database_backup()
        doc = FSInputFile(backup_path)

        voices_cnt = counts.get("voices", 0)
        users_cnt = counts.get("bot_users", 0)
        admins_cnt = counts.get("bot_admins", 0)
        subs_cnt = counts.get("voice_submissions", 0)
        settings_cnt = counts.get("bot_settings", 0)

        caption = (
            "📦 <b>Baza to'liq zaxira nusxasi (Backup JSON)</b>\n\n"
            f"🎙 Ovozlar (voices): <b>{voices_cnt}</b> ta\n"
            f"👥 Foydalanuvchilar: <b>{users_cnt}</b> ta\n"
            f"👮‍♂️ Adminlar: <b>{admins_cnt}</b> ta\n"
            f"📥 Takliflar: <b>{subs_cnt}</b> ta\n"
            f"⚙️ Sozlamalar: <b>{settings_cnt}</b> ta\n\n"
            "✅ Ushbu faylni saqlab qo'yishingiz yoki qayta tiklashda foydalanishingiz mumkin."
        )

        await callback.message.reply_document(
            document=doc,
            caption=caption,
            parse_mode="HTML"
        )
        await msg.delete()

    except Exception as e:
        logger.error(f"Backup yaratishda xatolik: {e}")
        await msg.edit_text(f"❌ Backup olishda xatolik yuz berdi: {e}")
    finally:
        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except Exception:
                pass



