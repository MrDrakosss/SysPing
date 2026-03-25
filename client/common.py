import json
import socket
import urllib.request
from pathlib import Path

SERVER_HTTP = "http://192.168.1.10:8080"
SERVER_WS = "ws://192.168.1.10:8080/ws/client"
MACHINE_NAME = socket.gethostname()
TOKEN_FILE = Path.home() / ".sysping_admin_token.json"


def http_get_json(path: str, token: str | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{SERVER_HTTP}{path}", headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_patch_json(path: str, payload: dict, token: str | None = None):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        f"{SERVER_HTTP}{path}",
        data=data,
        headers=headers,
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_post_json(path: str, payload: dict, token: str | None = None):
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        f"{SERVER_HTTP}{path}",
        data=data,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_delete(path: str, token: str | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(f"{SERVER_HTTP}{path}", headers=headers, method="DELETE")
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_branding() -> dict:
    try:
        return http_get_json("/public/branding")
    except Exception:
        return {
            "app_name": "SysPing",
            "company_name": "",
            "app_icon_path": "",
            "login_logo_path": "",
            "primary_color": "#2563eb",
            "secondary_color": "#1e293b",
            "web_admin_enabled": False,
        }


def save_admin_token(token: str, user: dict):
    TOKEN_FILE.write_text(json.dumps({"token": token, "user": user}, ensure_ascii=False), encoding="utf-8")


def load_admin_token() -> tuple[str | None, dict | None]:
    try:
        data = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
        return data.get("token"), data.get("user")
    except Exception:
        return None, None


def clear_admin_token():
    try:
        TOKEN_FILE.unlink(missing_ok=True)
    except Exception:
        pass