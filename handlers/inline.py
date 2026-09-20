import logging
from aiogram import Router
from aiogram.types import InlineQuery, ChosenInlineResult, InlineQueryResultCachedVoice
from database.voices import get_top_voices, search_voices, increment_voice_usage

logger = logging.getLogger(__name__)

router = Router()

@router.inline_query()
async def inline_voices_handler(inline_query: InlineQuery):
    """
    Inline qidiruv handleri:
    - Hech narsa yozilmasa: Eng ko'p jo'natilgan ovozlar ketma-ket chiqadi.
    - Biror so'z yozilsa: Nom yoki teglar bo'yicha mos ovozlar chiqadi.
    """
    query = inline_query.query.strip()
    
    try:
        if not query:
            # Bo'sh bo'lsa: Eng ko'p ishlatilgan trend ovozlar
            voices = await get_top_voices(limit=50)
        else:
            # So'z yozilsa: Qidiruv
            voices = await search_voices(query=query, limit=50)

        results = []
        for voice in voices:
            # cached voice Telegram serveridagi mavjud file_id orqali lahzada yuboriladi
            voice_id = str(voice["id"])
            title = voice.get("title", "Voice")
            file_id = voice.get("file_id")
            
            if file_id:
                results.append(
                    InlineQueryResultCachedVoice(
                        id=voice_id,
                        voice_file_id=file_id,
                        title=title
                    )
                )

        # cache_time=1 (natijalar doim yangi va aktual bo'lishi uchun)
        await inline_query.answer(
            results=results,
            cache_time=1,
            is_personal=True
        )
    except Exception as e:
        logger.error(f"inline_query xatosi: {e}")

@router.chosen_inline_result()
async def chosen_inline_voice_handler(chosen_result: ChosenInlineResult):
    """
    Foydalanuvchi ovozni tanlab yuborganda chaqiriladi.
    O'sha ovozning usage_count sonini oshirib boradi!
    """
    voice_id = chosen_result.result_id
    if voice_id:
        try:
            await increment_voice_usage(voice_id)
            logger.info(f"Ovoz ishlatildi (ID: {voice_id})")
        except Exception as e:
            logger.error(f"chosen_inline_result xatosi: {e}")
