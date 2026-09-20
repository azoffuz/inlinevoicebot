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
        ],
        [
            InlineKeyboardButton(text="📢 Majburiy obuna", callback_data="admin_channels"),
            InlineKeyboardButton(text="📥 Baza Backup", callback_data="admin_backup")
        ]
    ]
    if is_super:
        keyboard.append([
            InlineKeyboardButton(text="👥 Adminlar boshqaruvi", callback_data="admin_manage_admins")
        ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_audio_main_kb() -> InlineKeyboardMarkup:
    """Audio/Voice yuborilganda chiquvchi 2 ta asosiy tugma va qulay vositalar."""
    keyboard = [
        [
            InlineKeyboardButton(text="➕ Ovoz qo'shish", callback_data="suggest_voice"),
            InlineKeyboardButton(text="🎨 Ovoz effektlari", callback_data="open_effects")
        ],
        [
            InlineKeyboardButton(text="✂️ Audio kesish", callback_data="open_trim"),
            InlineKeyboardButton(text="🚀 Do'stlarga yuborish", switch_inline_query="")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_audio_effects_kb() -> InlineKeyboardMarkup:
    """Faqat 'Ovoz effektlari' bosilgandagina ochiluvchi effektlar menyusi."""
    keyboard = [
        [
            InlineKeyboardButton(text="🎙 Oddiy", callback_data="fx:normal"),
            InlineKeyboardButton(text="🤖 Robot", callback_data="fx:robot")
        ],
        [
            InlineKeyboardButton(text="🐿 Chipmunk", callback_data="fx:chipmunk"),
            InlineKeyboardButton(text="🔈 Bas / Chuqur", callback_data="fx:deep")
        ],
        [
            InlineKeyboardButton(text="🎈 Geliy (Ingichka)", callback_data="fx:helium"),
            InlineKeyboardButton(text="📻 Radio / Ratsiya", callback_data="fx:radio")
        ],
        [
            InlineKeyboardButton(text="🌌 Aks-sado", callback_data="fx:echo"),
            InlineKeyboardButton(text="⚡️ 1.4x Tez", callback_data="fx:fast"),
            InlineKeyboardButton(text="🐢 0.75x Sekin", callback_data="fx:slow")
        ],
        [
            InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_to_audio_main")
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

def get_subscription_check_kb(unsubscribed_channels: list) -> InlineKeyboardMarkup:
    """Majburiy obuna tekshiruvi uchun kanallar va tasdiqlash tugmalari."""
    keyboard = []
    for ch in unsubscribed_channels:
        keyboard.append([
            InlineKeyboardButton(text=f"📢 {ch.get('name', 'Kanal')}", url=ch.get("url", "https://t.me"))
        ])
    keyboard.append([
        InlineKeyboardButton(text="✅ A'zo bo'ldim / Tekshirish", callback_data="check_subscription")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

