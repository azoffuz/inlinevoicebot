import logging
import os
import tempfile
from aiogram import Router, F, Bot
from aiogram.types import Message, FSInputFile
from config import config
from database.voices import add_voice
from services.audio_converter import convert_audio_to_voice

logger = logging.getLogger(__name__)

router = Router()

@router.channel_post()
async def handle_channel_post(message: Message, bot: Bot):
    """
    Storage kanalga yangi voice yoki audio tashlanganda avtomatik ushlab
    bazaga (Supabase) kiritish.
    """
    # Faqat belgilangan kanal bo'lsa ishlaydi
    if config.STORAGE_CHANNEL_ID and message.chat.id != config.STORAGE_CHANNEL_ID:
        return

    title = message.caption or (message.audio.title if message.audio else "")
    if not title:
        title = f"Ovoz #{message.message_id}"

    # 1. Agar xabar Voice bo'lsa
    if message.voice:
        voice = message.voice
        saved = await add_voice(
            title=title,
            file_id=voice.file_id,
            file_unique_id=voice.file_unique_id,
            duration=voice.duration,
            channel_message_id=message.message_id
        )
        if saved:
            logger.info(f"Yangi voice kanal orqali saqlandi: {title} (ID: {saved.get('id')})")
        return

    # 2. Agar xabar Audio (MP3) bo'lsa, uni voice ga aylantirib kanalga qayta yuborish
    if message.audio:
        audio = message.audio
        try:
            file_info = await bot.get_file(audio.file_id)
            if not file_info.file_path:
                return
            
            ext = os.path.splitext(file_info.file_path)[1] or ".mp3"
            input_path = os.path.join(temp_dir, f"ch_in_{audio.file_unique_id}{ext}")
            await bot.download_file(file_info.file_path, destination=input_path)
            output_voice = await convert_audio_to_voice(input_path, effect="normal")

            
            # Kanalga voice qilib yuboramiz
            voice_file = FSInputFile(output_voice)
            sent_msg = await bot.send_voice(
                chat_id=message.chat.id,
                voice=voice_file,
                caption=f"🎙 {title}"
            )
            
            # Yangi yuborilgan voice_file_id ni bazaga saqlaymiz
            if sent_msg.voice:
                await add_voice(
                    title=title,
                    file_id=sent_msg.voice.file_id,
                    file_unique_id=sent_msg.voice.file_unique_id,
                    duration=sent_msg.voice.duration,
                    channel_message_id=sent_msg.message_id
                )
                logger.info(f"Audio voice ga aylantirilib kanalga va bazaga saqlandi: {title}")
                
        except Exception as e:
            logger.error(f"Kanaldagi audio konvertatsiyasida xatolik: {e}")
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
