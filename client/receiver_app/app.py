"""
Az alkalmazás indítása.
"""

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from receiver_app.config import APP_NAME
from receiver_app.main_window import ReceiverMainWindow
from receiver_app.styles import build_stylesheet, is_dark_mode
from receiver_app.utils import maybe_handle_admin_close_child, set_windows_app_id


def run_receiver_app():
    """
    Elindítja a teljes receiver alkalmazást.
    """
    maybe_handle_admin_close_child()

    app = QApplication(sys.argv)
    dark = is_dark_mode(app)

    set_windows_app_id(APP_NAME)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Hiba", "A system tray nem érhető el.")
        sys.exit(1)

    app.setStyleSheet(build_stylesheet(dark))

    window = ReceiverMainWindow(dark)
    window.show()

    sys.exit(app.exec())