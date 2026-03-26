"""
Windows-specifikus és általános segédfüggvények.
"""

import os
import sys
import tempfile
import time
from pathlib import Path


def set_windows_app_id(app_name: str) -> None:
    """
    Beállítja a Windows AppUserModelID-t, hogy a notification cím ne Python legyen.
    """
    if os.name != "nt":
        return

    try:
        import ctypes
        safe_name = "".join(ch if ch.isalnum() else "." for ch in app_name).strip(".") or "SysPing"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(safe_name)
    except Exception:
        pass


def maybe_handle_admin_close_child() -> None:
    """
    Ha az alkalmazás admin jóváhagyás ellenőrző segédmódban indult,
    létrehozza a token fájlt és kilép.
    """
    if os.name != "nt":
        return

    if "--authorize-close" not in sys.argv:
        return

    try:
        idx = sys.argv.index("--authorize-close")
        token_path = sys.argv[idx + 1]
        Path(token_path).write_text("approved", encoding="utf-8")
        sys.exit(0)
    except Exception:
        sys.exit(2)


def request_admin_close_approval() -> bool:
    """
    Windows UAC segítségével admin jóváhagyást kér a teljes leállításhoz.
    """
    if os.name != "nt":
        return True

    try:
        import ctypes
    except Exception:
        return False

    fd, token_path = tempfile.mkstemp(prefix="sysping_close_", suffix=".token")
    os.close(fd)

    try:
        Path(token_path).unlink(missing_ok=True)
    except Exception:
        pass

    if getattr(sys, "frozen", False):
        executable = sys.executable
        params = f'--authorize-close "{token_path}"'
    else:
        executable = sys.executable
        script_path = str(Path(__file__).resolve().parents[1] / "receiver_client.py")
        params = f'"{script_path}" --authorize-close "{token_path}"'

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        params,
        str(Path(__file__).resolve().parents[1]),
        1,
    )

    if result <= 32:
        return False

    deadline = time.time() + 20
    while time.time() < deadline:
        if Path(token_path).exists():
            try:
                Path(token_path).unlink(missing_ok=True)
            except Exception:
                pass
            return True
        time.sleep(0.2)

    return False


def escape_html(text: str) -> str:
    """
    HTML escape a QTextBrowser biztonságos rendereléséhez.
    """
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )