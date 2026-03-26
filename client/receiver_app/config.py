"""
Konfigurációs és branding segédfüggvények.
"""

from receiver_app.config_store import read_config
from common import fetch_branding, http_get_json


_RUNTIME_CONFIG = read_config()

SERVER_HTTP = _RUNTIME_CONFIG["http_url"]
SERVER_WS = _RUNTIME_CONFIG["ws_url"]
MACHINE_NAME = _RUNTIME_CONFIG["machine_name"]
AUTO_START = _RUNTIME_CONFIG["auto_start"]
START_MINIMIZED = _RUNTIME_CONFIG["start_minimized"]

APP_BRANDING = fetch_branding(SERVER_HTTP)
APP_NAME = APP_BRANDING.get("app_name") or "SysPing"

RECENT_MESSAGES_LIMIT = 20
IMPORTANT_REMINDER_MINUTES = 10
HEARTBEAT_SECONDS = 30

__all__ = [
    "MACHINE_NAME",
    "SERVER_HTTP",
    "SERVER_WS",
    "APP_BRANDING",
    "APP_NAME",
    "AUTO_START",
    "START_MINIMIZED",
    "RECENT_MESSAGES_LIMIT",
    "IMPORTANT_REMINDER_MINUTES",
    "HEARTBEAT_SECONDS",
    "fetch_branding",
    "http_get_json",
]