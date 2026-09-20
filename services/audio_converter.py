import asyncio
import os
import tempfile
import logging

logger = logging.getLogger(__name__)

async def convert_audio_to_voice(input_path: str, effect: str = "normal") -> str:
    """
    Har qanday audio faylni (MP3, WAV, M4A va h.k.) Telegram Voice (.ogg Opus) formatiga o'tkazadi.
    Effektlar: normal, chipmunk (ingichka/tez), deep (yo'g'on/bas), robot.
    """
    output_fd, output_path = tempfile.mkstemp(suffix=".ogg")
    os.close(output_fd)

    # Audio filtrlarini sozlash
    af_filters = []
    if effect == "chipmunk":
        af_filters.append("asetrate=48000*1.35,aresample=48000,atempo=1.05")
    elif effect == "deep":
        af_filters.append("asetrate=48000*0.75,aresample=48000,bass=g=10")
    elif effect == "robot":
        af_filters.append("flanger=delay=10:depth=5:regen=70:width=71:speed=0.5")
    elif effect == "helium":
        af_filters.append("asetrate=48000*1.6,aresample=48000,atempo=0.8")
    elif effect == "radio":
        af_filters.append("highpass=f=400,lowpass=f=2800,volume=1.8")
    elif effect == "echo":
        af_filters.append("aecho=0.8:0.88:400:0.4")
    elif effect == "fast":
        af_filters.append("atempo=1.4")
    elif effect == "slow":
        af_filters.append("atempo=0.75")


    cmd = [
        "ffmpeg", "-y",
        "-i", input_path
    ]

    if af_filters:
        cmd.extend(["-af", ",".join(af_filters)])

    cmd.extend([
        "-c:a", "libopus",
        "-b:a", "64k",
        "-vbr", "on",
        "-compression_level", "10",
        "-ar", "48000",
        "-ac", "1",
        output_path
    ])

    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        err_msg = stderr.decode(errors='ignore').strip()
        last_lines = "\n".join(err_msg.splitlines()[-3:]) if err_msg else "Noma'lum FFmpeg xatosi"
        logger.error(f"FFmpeg xatosi: {err_msg}")
        if os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        raise RuntimeError(f"{last_lines}")

    return output_path

