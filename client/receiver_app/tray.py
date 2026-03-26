"""
Tray ikon és kapcsolódó műveletek.
"""

from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QSystemTrayIcon


def create_app_icon(unread: bool) -> QIcon:
    """
    Létrehoz egy egyszerű kör alakú ikont.
    Olvasatlan üzenet esetén piros jelölést tesz rá.
    """
    pixmap = QPixmap(64, 64)
    pixmap.fill("transparent")

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#2563eb"))
    painter.setPen("transparent")
    painter.drawEllipse(8, 8, 48, 48)

    if unread:
        painter.setBrush(QColor("#ef4444"))
        painter.drawEllipse(42, 6, 16, 16)

    painter.end()
    return QIcon(pixmap)


def setup_tray(window, app_name: str):
    """
    Inicializálja a tray ikont, menüt és eseménykezelőket.
    """
    window.tray_icon = QSystemTrayIcon(window)
    window.icon_normal = create_app_icon(False)
    window.icon_unread = create_app_icon(True)

    window.tray_icon.setIcon(window.icon_normal)
    window.setWindowIcon(window.icon_normal)
    window.tray_icon.setToolTip(app_name)

    menu = QMenu()
    open_action = QAction("Megnyitás", window)
    open_action.triggered.connect(window.restore_from_tray)
    menu.addAction(open_action)

    quit_action = QAction("Program leállítása (admin joggal)", window)
    quit_action.triggered.connect(window.request_full_exit)
    menu.addAction(quit_action)

    window.tray_icon.setContextMenu(menu)
    window.tray_icon.activated.connect(window.on_tray_activated)
    window.tray_icon.show()