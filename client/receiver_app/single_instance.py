"""
Single instance védelem Windows alatt.

Megakadályozza, hogy ugyanabból a kliensből egyszerre több példány fusson.
"""

from __future__ import annotations

import os


class SingleInstance:
    """
    Egy named mutex segítségével biztosítja, hogy csak egy példány fusson.
    """

    def __init__(self, app_id: str):
        self.app_id = app_id
        self.handle = None
        self.already_running = False

        if os.name != "nt":
            return

        try:
            import ctypes
            from ctypes import wintypes

            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
            kernel32.CreateMutexW.argtypes = [
                wintypes.LPVOID,
                wintypes.BOOL,
                wintypes.LPCWSTR,
            ]
            kernel32.CreateMutexW.restype = wintypes.HANDLE

            name = f"Global\\{self.app_id}"
            self.handle = kernel32.CreateMutexW(None, False, name)

            ERROR_ALREADY_EXISTS = 183
            self.already_running = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
        except Exception:
            self.already_running = False

    def is_running(self) -> bool:
        """
        Visszaadja, hogy fut-e már egy másik példány.
        """
        return self.already_running