"""
Telepített kliens konfiguráció kezelés XML fájlban.
"""

from __future__ import annotations

import os
import socket
import xml.etree.ElementTree as ET
from pathlib import Path


APP_DIR_NAME = "SysPing"
PROGRAM_DATA_DIR = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / APP_DIR_NAME
CONFIG_PATH = PROGRAM_DATA_DIR / "config.xml"


DEFAULT_HTTP_URL = "http://127.0.0.1:8080"
DEFAULT_WS_URL = "ws://127.0.0.1:8080/ws/client"


def ensure_data_dir() -> Path:
    """
    Létrehozza a ProgramData alatti SysPing könyvtárat, ha még nem létezik.
    """
    PROGRAM_DATA_DIR.mkdir(parents=True, exist_ok=True)
    return PROGRAM_DATA_DIR


def create_default_config() -> None:
    """
    Létrehozza az alapértelmezett XML konfigurációt, ha még nincs.
    """
    ensure_data_dir()

    if CONFIG_PATH.exists():
        return

    root = ET.Element("SysPingConfig")

    server = ET.SubElement(root, "Server")
    ET.SubElement(server, "HttpUrl").text = DEFAULT_HTTP_URL
    ET.SubElement(server, "WsUrl").text = DEFAULT_WS_URL

    client = ET.SubElement(root, "Client")
    ET.SubElement(client, "MachineName").text = ""
    ET.SubElement(client, "AutoStart").text = "true"
    ET.SubElement(client, "StartMinimized").text = "true"

    tree = ET.ElementTree(root)
    tree.write(CONFIG_PATH, encoding="utf-8", xml_declaration=True)


def read_config() -> dict:
    """
    Beolvassa az XML konfigurációt és dict formában visszaadja.
    """
    create_default_config()

    tree = ET.parse(CONFIG_PATH)
    root = tree.getroot()

    http_url = root.findtext("./Server/HttpUrl", DEFAULT_HTTP_URL).strip()
    ws_url = root.findtext("./Server/WsUrl", DEFAULT_WS_URL).strip()
    machine_name = root.findtext("./Client/MachineName", "").strip()
    auto_start = root.findtext("./Client/AutoStart", "true").strip().lower() == "true"
    start_minimized = root.findtext("./Client/StartMinimized", "true").strip().lower() == "true"

    if not machine_name:
        machine_name = socket.gethostname()

    return {
        "http_url": http_url,
        "ws_url": ws_url,
        "machine_name": machine_name,
        "auto_start": auto_start,
        "start_minimized": start_minimized,
        "config_path": str(CONFIG_PATH),
    }


def write_server_urls(http_url: str, ws_url: str) -> None:
    """
    Frissíti a szerver URL-eket az XML fájlban.
    """
    create_default_config()

    tree = ET.parse(CONFIG_PATH)
    root = tree.getroot()

    root.find("./Server/HttpUrl").text = http_url.strip()
    root.find("./Server/WsUrl").text = ws_url.strip()

    tree.write(CONFIG_PATH, encoding="utf-8", xml_declaration=True)