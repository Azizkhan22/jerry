import asyncio
import subprocess

import edge_tts

# Natural-sounding female voice. Other options: "en-US-JennyNeural",
# "en-GB-SoniaNeural". Run `edge-tts --list-voices` to see all choices.
VOICE = "en-US-AriaNeural"


async def _generate_mp3(text: str, mp3_path: str):
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(mp3_path)


def synthesize_speech_mp3(text: str, output_mp3_path: str) -> str:
    """Convert text to an .mp3 file. Used by the web UI - browsers play
    mp3 natively via <audio>, no ffmpeg required."""
    asyncio.run(_generate_mp3(text, output_mp3_path))
    return output_mp3_path


def synthesize_speech_ogg(text: str, output_ogg_path: str) -> str:
    """Convert text to an .ogg/opus voice note. Used by the Telegram bot.
    Requires ffmpeg to be installed and on PATH."""
    mp3_path = output_ogg_path.rsplit(".", 1)[0] + ".mp3"
    asyncio.run(_generate_mp3(text, mp3_path))
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "32k", output_ogg_path],
        check=True, capture_output=True,
    )
    return output_ogg_path
