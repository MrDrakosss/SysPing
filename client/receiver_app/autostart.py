"""
Windows automatikus indítás kezelése.
"""

from __future__ import annotations

import os
import sys


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_VALUE_NAME = "SysPingReceiver"


def get_executable_command() -> str:
    """
    Visszaadja az automatikus indításhoz szükséges parancsot.
    """
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    return f'"{sys.executable}" "{sys.argv[0]}"'


def enable_autostart() -> bool:
    """
    Bekapcsolja az automatikus indulást a registryben.
    """
    if os.name != "nt":
        return False

    try:
        import winreg

        command = get_executable_command()
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print("[Receiver] Autostart beállítási hiba:", e)
        return False


def disable_autostart() -> bool:
    """
    Kikapcsolja az automatikus indulást a registryben.
    """
    if os.name != "nt":
        return False

    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print("[Receiver] Autostart törlési hiba:", e)
        return False