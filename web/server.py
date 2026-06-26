import asyncio
import json
import os
import queue
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
from agent.jerry_agent import chat, get_history, stream_chat
from voice.stt import transcribe_audio
from voice.tts import synthesize_speech_mp3
from web.chats_store import create_chat, delete_chat, list_chats, rename_chat, touch_chat


async def _voice_cleanup_loop():
    """Periodically delete generated TTS replies older than the configured
    TTL. Recorded input clips are deleted immediately after transcription
    in api_voice, independent of this loop."""
    while True:
        try:
            cutoff = time.time() - config.VOICE_FILE_TTL_SECONDS
            for name in os.listdir(config.VOICE_DIR):
                path = os.path.join(config.VOICE_DIR, name)
                if os.path.isfile(path) and os.path.getmtime(path) < cutoff:
                    os.remove(path)
        except OSError:
            pass
        await asyncio.sleep(config.VOICE_CLEANUP_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_voice_cleanup_loop())
    yield
    task.cancel()


app = FastAPI(title="Jerry", lifespan=lifespan)

# Tracks the most recently uploaded file per chat, to be used as the next
# email attachment in that chat. Single-user app, so a module-level dict
# (keyed by chat_id) is fine.
_last_attachment: dict[str, str] = {}


def _with_attachment_note(chat_id: str, message: str) -> str:
    path = _last_attachment.pop(chat_id, None)
    if path:
        return f"{message}\n\n[Attached file available at: {path}]"
    return message


class ChatRequest(BaseModel):
    chat_id: str
    message: str


class ChatIdRequest(BaseModel):
    chat_id: str


class RenameRequest(BaseModel):
    title: str


# --- Chat list management ---

@app.get("/api/chats")
async def api_list_chats():
    return {"chats": list_chats()}


@app.post("/api/chats")
async def api_create_chat():
    return create_chat()


@app.patch("/api/chats/{chat_id}")
async def api_rename_chat(chat_id: str, payload: RenameRequest):
    chat_meta = rename_chat(chat_id, payload.title)
    if chat_meta is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat_meta


@app.delete("/api/chats/{chat_id}")
async def api_delete_chat(chat_id: str):
    delete_chat(chat_id)
    _last_attachment.pop(chat_id, None)
    return {"ok": True}


@app.get("/api/history")
async def api_history(chat_id: str):
    return {"messages": get_history(chat_id)}


# --- Messaging ---

@app.post("/api/chat")
async def api_chat(payload: ChatRequest):
    message = _with_attachment_note(payload.chat_id, payload.message)
    reply = await asyncio.to_thread(chat, payload.chat_id, message)
    touch_chat(payload.chat_id, auto_title_from=payload.message)
    return {"reply": reply}


@app.post("/api/chat/stream")
async def api_chat_stream(payload: ChatRequest):
    message = _with_attachment_note(payload.chat_id, payload.message)
    touch_chat(payload.chat_id, auto_title_from=payload.message)

    q: queue.Queue = queue.Queue()

    def run():
        stream_chat(payload.chat_id, message, q)
        q.put(None)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    async def generate():
        while True:
            try:
                event = q.get(timeout=0.2)
            except queue.Empty:
                await asyncio.sleep(0.05)
                continue
            if event is None:
                break
            yield f"data: {json.dumps(event)}\n\n"
        yield 'data: {"type":"done"}\n\n'

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/voice")
async def api_voice(chat_id: str = Form(...), audio: UploadFile = File(...)):
    ext = audio.filename.rsplit(".", 1)[-1] if audio.filename and "." in audio.filename else "webm"
    in_path = os.path.join(config.VOICE_DIR, f"{uuid.uuid4()}.{ext}")
    with open(in_path, "wb") as f:
        f.write(await audio.read())

    try:
        transcript = await asyncio.to_thread(transcribe_audio, in_path)
    finally:
        # The recording itself is only needed for this one transcription.
        if os.path.exists(in_path):
            os.remove(in_path)

    message = _with_attachment_note(chat_id, transcript)
    reply = await asyncio.to_thread(chat, chat_id, message)
    touch_chat(chat_id, auto_title_from=transcript)

    out_name = f"{uuid.uuid4()}.mp3"
    out_path = os.path.join(config.VOICE_DIR, out_name)
    await asyncio.to_thread(synthesize_speech_mp3, reply, out_path)

    return {"transcript": transcript, "reply": reply, "audio_url": f"/audio/{out_name}"}


# --- Attachments ---

@app.post("/api/upload")
async def api_upload(chat_id: str = Form(...), file: UploadFile = File(...)):
    save_path = os.path.join(config.DOWNLOADS_DIR, file.filename)
    with open(save_path, "wb") as f:
        f.write(await file.read())
    _last_attachment[chat_id] = save_path
    return {"filename": file.filename}


@app.post("/api/clear-attachment")
async def api_clear_attachment(payload: ChatIdRequest):
    _last_attachment.pop(payload.chat_id, None)
    return {"ok": True}


@app.get("/audio/{filename}")
async def get_audio(filename: str):
    path = os.path.join(config.VOICE_DIR, filename)
    return FileResponse(path, media_type="audio/mpeg")


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/", StaticFiles(directory=_STATIC_DIR, html=True), name="static")
