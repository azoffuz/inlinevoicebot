from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_menu_kb(is_super: bool = False) -> InlineKeyboardMarkup:
    """Admin panel asosiy menyusi."""
    keyboard = [
        [
            InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats"),
            InlineKeyboardButton(text="➕ Ovoz qo'shish", callback_data="admin_add_voice")
        ],
        [
            InlineKeyboardButton(text="📂 Ovozlar ro'yxati", callback_data="admin_list_voices_0"),
            InlineKeyboardButton(text="📢 Xabar tarqatish", callback_data="admin_broadcast")
        ]
    ]
    if is_super:
        keyboard.append([
            InlineKeyboardButton(text="👥 Adminlar boshqaruvi", callback_data="admin_manage_admins")
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_audio_convert_kb(is_adm: bool = False) -> InlineKeyboardMarkup:
    """MP3 yuborilganda effektlar va konvertatsiya tugmalari."""
    keyboard = [
        [
            InlineKeyboardButton(text="🎙 Oddiy Voice", callback_data="fx:normal"),
            InlineKeyboardButton(text="🤖 Robot", callback_data="fx:robot")
        ],
        [
            InlineKeyboardButton(text="🐿 Chipmunk (Tez)", callback_data="fx:chipmunk"),
            InlineKeyboardButton(text="🔈 Basoviy (Chuqur)", callback_data="fx:deep")
        ],
        [
            InlineKeyboardButton(text="💡 Bazaga ovoz taklif qilish", callback_data="suggest_voice")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_moderation_kb(sub_id: str) -> InlineKeyboardMarkup:
    """Adminlar uchun ovozni tasdiqlash yoki rad etish tugmalari."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"appv:{sub_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"rjct:{sub_id}")
        ]
    ])



def get_voice_action_kb(voice_id: str) -> InlineKeyboardMarkup:
    """Admin uchun bitta ovozni boshqarish (o'chirish) tugmasi."""
    keyboard = [
        [
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_voice:{voice_id}"),
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_list_voices_0")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_back_to_admin_kb() -> InlineKeyboardMarkup:
    """Admin menyusiga qaytish tugmasi."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Admin Menyusi", callback_data="admin_main_menu")]
    ])
