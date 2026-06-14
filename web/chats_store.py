import json
import os
import threading
import uuid
from datetime import datetime, timezone

import config
from agent.jerry_agent import get_history, reset_thread

_LOCK = threading.Lock()

# Legacy single-thread id used before multi-chat support existed.
_LEGACY_THREAD_ID = "web_user"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict:
    if not os.path.exists(config.CHATS_PATH):
        return {"chats": []}
    try:
        with open(config.CHATS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"chats": []}


def _save(data: dict) -> None:
    with open(config.CHATS_PATH, "w") as f:
        json.dump(data, f, indent=2)


def _make_title(text: str, fallback: str = "New chat") -> str:
    title = " ".join(text.strip().splitlines()).strip()
    if not title:
        return fallback
    return title[:47] + "..." if len(title) > 50 else title


def _migrate_legacy_thread() -> dict | None:
    """One-time: surface a pre-multi-chat conversation (thread_id
    'web_user') as a real chat instead of silently losing access to it."""
    history = get_history(_LEGACY_THREAD_ID)
    if not history:
        return None
    first_user = next((m["content"] for m in history if m["role"] == "user"), "")
    now = _now()
    return {
        "id": _LEGACY_THREAD_ID,
        "title": _make_title(first_user, fallback="Previous chat"),
        "created_at": now,
        "updated_at": now,
    }


def list_chats() -> list[dict]:
    with _LOCK:
        data = _load()
        if not data["chats"]:
            migrated = _migrate_legacy_thread()
            if migrated:
                data["chats"].append(migrated)
                _save(data)
        return sorted(data["chats"], key=lambda c: c["updated_at"], reverse=True)


def create_chat() -> dict:
    with _LOCK:
        data = _load()
        chat = {
            "id": str(uuid.uuid4()),
            "title": "New chat",
            "created_at": _now(),
            "updated_at": _now(),
        }
        data["chats"].append(chat)
        _save(data)
        return chat


def rename_chat(chat_id: str, title: str) -> dict | None:
    with _LOCK:
        data = _load()
        for c in data["chats"]:
            if c["id"] == chat_id:
                c["title"] = _make_title(title, fallback=c["title"])
                c["updated_at"] = _now()
                _save(data)
                return c
        return None


def touch_chat(chat_id: str, auto_title_from: str | None = None) -> dict | None:
    """Bump updated_at after an exchange, and auto-title the chat from the
    first user message if it's still using the default title."""
    with _LOCK:
        data = _load()
        for c in data["chats"]:
            if c["id"] == chat_id:
                c["updated_at"] = _now()
                if c["title"] == "New chat" and auto_title_from:
                    c["title"] = _make_title(auto_title_from)
                _save(data)
                return c
        return None


def delete_chat(chat_id: str) -> None:
    with _LOCK:
        data = _load()
        data["chats"] = [c for c in data["chats"] if c["id"] != chat_id]
        _save(data)
    reset_thread(chat_id)
