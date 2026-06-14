import asyncio
import os
import uuid

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import config
from agent.jerry_agent import chat
from voice.stt import transcribe_audio
from voice.tts import synthesize_speech_ogg


def _authorized(update: Update) -> bool:
    if not config.ALLOWED_USER_ID:
        return True  # no restriction configured - anyone can use the bot
    return str(update.effective_user.id) == str(config.ALLOWED_USER_ID)


def _pop_attachment_note(context: ContextTypes.DEFAULT_TYPE) -> str:
    """If a file was uploaded just before this message, append its path
    so the agent can use it as an email attachment, then clear it."""
    path = context.user_data.pop("last_attachment", None)
    if not path:
        return ""
    return f"\n\n[Attached file available at: {path}]"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi, I'm Jerry - your personal assistant.\n\n"
        "I can read/summarize/send emails, check or update your calendar "
        "and tasks, mark your attendance, and chat by text or voice. "
        "Send a file before a message to email it as an attachment."
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    user_id = update.effective_user.id
    message = update.message.text + _pop_attachment_note(context)

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    reply = await asyncio.to_thread(chat, user_id, message)
    await update.message.reply_text(reply)


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    user_id = update.effective_user.id
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)

    voice_file = await update.message.voice.get_file()
    in_path = os.path.join(config.VOICE_DIR, f"{uuid.uuid4()}.ogg")
    await voice_file.download_to_drive(in_path)

    user_text = await asyncio.to_thread(transcribe_audio, in_path)
    message = user_text + _pop_attachment_note(context)

    reply_text = await asyncio.to_thread(chat, user_id, message)

    out_path = os.path.join(config.VOICE_DIR, f"{uuid.uuid4()}.ogg")
    await asyncio.to_thread(synthesize_speech_ogg, reply_text, out_path)

    await update.message.reply_text(f"You said: {user_text}\n\n{reply_text}")
    with open(out_path, "rb") as f:
        await update.message.reply_voice(voice=f)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _authorized(update):
        return

    doc = update.message.document
    file = await context.bot.get_file(doc.file_id)
    save_path = os.path.join(config.DOWNLOADS_DIR, doc.file_name)
    await file.download_to_drive(save_path)

    context.user_data["last_attachment"] = save_path
    await update.message.reply_text(
        f"Got '{doc.file_name}'. Tell me what to do with it, e.g. "
        f"\"email this to manager@company.com as a leave application for tomorrow\"."
    )


def main():
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Jerry is running. Talk to your bot on Telegram...")
    app.run_polling()


if __name__ == "__main__":
    main()
