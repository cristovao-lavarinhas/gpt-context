"""Chat history persistence — same JSON-on-disk approach as the Streamlit app."""

from __future__ import annotations

import json
import time
from pathlib import Path
from threading import Lock

CHAT_HISTORY_FILE = Path(__file__).parent / "chat_history.json"
MAX_HISTORY = 10

_lock = Lock()


def _load() -> list[dict]:
    if CHAT_HISTORY_FILE.exists():
        try:
            with open(CHAT_HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return []


def _save(history: list[dict]) -> None:
    try:
        with open(CHAT_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _title_from_messages(messages: list[dict]) -> str:
    for msg in messages:
        if msg["role"] == "user":
            text = msg["content"][:40]
            return text + ("..." if len(msg["content"]) > 40 else "")
    return "New Chat"


def list_history() -> list[dict]:
    with _lock:
        return _load()


def delete_chat(chat_id: int) -> list[dict]:
    with _lock:
        history = [c for c in _load() if c["id"] != chat_id]
        _save(history)
        return history


def upsert_chat(chat_id: int | None, messages: list[dict]) -> dict:
    """Create or update a chat entry from the full message list. Returns the saved chat."""
    if not messages:
        return {"id": chat_id, "title": "New Chat", "messages": []}

    with _lock:
        history = _load()

        if chat_id is not None:
            for chat in history:
                if chat["id"] == chat_id:
                    chat["messages"] = messages
                    chat["title"] = _title_from_messages(messages)
                    _save(history)
                    return chat

        new_id = int(time.time() * 1000)
        new_chat = {"id": new_id, "title": _title_from_messages(messages), "messages": messages}
        history.insert(0, new_chat)
        history = history[:MAX_HISTORY]
        _save(history)
        return new_chat
