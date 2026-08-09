"""Telegram notifier for loker jobs. Reads token/chat_id from .env."""
import os
from typing import Optional
import requests

ENV_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")


def _load_env() -> dict:
    env = {}
    if os.path.exists(ENV_PATH):
        for line in open(ENV_PATH):
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


def get_me() -> dict:
    env = _load_env()
    r = requests.get(f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/getMe", timeout=15)
    return r.json()


def get_chat_id() -> Optional[str]:
    """Fetch latest chat id from bot updates (user must have messaged the bot)."""
    env = _load_env()
    r = requests.get(
        f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/getUpdates",
        timeout=15,
    )
    for u in r.json().get("result", []):
        msg = u.get("message") or u.get("edited_message") or {}
        chat = msg.get("chat") or {}
        if chat.get("id"):
            return str(chat["id"])
    return None


def send(text: str, chat_id: Optional[str] = None, parse_mode: str = "") -> bool:
    env = _load_env()
    cid_raw = chat_id or env.get("TELEGRAM_CHAT_ID", "")
    if not cid_raw:
        return False
    ids = [c.strip() for c in str(cid_raw).split(",") if c.strip()]
    if not ids:
        return False
    url = f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/sendMessage"
    payload = {"text": text[:4000]}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    ok = True
    for cid in ids:
        p = dict(payload, chat_id=int(cid))
        r = requests.post(url, json=p, timeout=15)
        ok = ok and r.status_code == 200
    return ok