import json
import urllib.request


def http_get_json(base_url: str, path: str, token: str | None = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        f"{base_url}{path}",
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_branding(server_http: str) -> dict:
    try:
        return http_get_json(server_http, "/public/branding")
    except Exception:
        return {
            "id": 0,
            "app_name": "SysPing",
            "company_name": "",
            "app_icon_path": "",
            "login_logo_path": "",
            "primary_color": "#2563eb",
            "secondary_color": "#1e293b",
            "web_admin_enabled": False,
        }