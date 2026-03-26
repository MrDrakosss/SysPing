"""
Kliensoldali cache kezelés JSON fájlban.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


APP_DIR_NAME = "SysPing"
PROGRAM_DATA_DIR = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / APP_DIR_NAME
CACHE_PATH = PROGRAM_DATA_DIR / "cache.json"


def ensure_cache_file() -> None:
    """
    Létrehozza az üres cache fájlt, ha még nem létezik.
    """
    PROGRAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not CACHE_PATH.exists():
        CACHE_PATH.write_text(
            json.dumps({"last_message_id": 0, "messages": []}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )


def load_cache() -> dict:
    """
    Betölti a cache tartalmát.
    """
    ensure_cache_file()
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"last_message_id": 0, "messages": []}


def save_cache(data: dict) -> None:
    """
    Elmenti a cache tartalmát.
    """
    PROGRAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_last_message_id() -> int:
    """
    Visszaadja az utoljára eltárolt legnagyobb message ID-t.
    """
    cache = load_cache()
    return int(cache.get("last_message_id", 0) or 0)


def update_message_cache(messages: list[dict]) -> None:
    """
    Összefésüli a cache-ben lévő és az új üzeneteket.
    Csak az új message_id-jű elemek kerülnek be.
    """
    cache = load_cache()

    existing = cache.get("messages", [])
    existing_ids = {int(m.get("id", 0)) for m in existing if m.get("id") is not None}

    merged = list(existing)
    max_id = int(cache.get("last_message_id", 0) or 0)

    for msg in messages:
        msg_id = int(msg.get("id", 0) or 0)
        if msg_id and msg_id not in existing_ids:
            merged.append(msg)
            existing_ids.add(msg_id)
            if msg_id > max_id:
                max_id = msg_id

    merged = sorted(merged, key=lambda x: int(x.get("id", 0) or 0))
    merged = merged[-200:]  # helyi cache limit

    cache["messages"] = merged
    cache["last_message_id"] = max_id
    save_cache(cache)


def get_cached_messages() -> list[dict]:
    """
    Visszaadja a cache-ben lévő üzeneteket.
    """
    return load_cache().get("messages", [])