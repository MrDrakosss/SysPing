import json
import os
import sys
import tempfile
import threading
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from websocket import create_connection

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QSystemTrayIcon,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from common import MACHINE_NAME, SERVER_HTTP, SERVER_WS, fetch_branding, http_get_json


def is_dark_mode(app: QApplication) -> bool:
    palette = app.palette()
    window_color = palette.color(QPalette.Window)
    return window_color.lightness() < 128


def build_stylesheet(dark: bool) -> str:
    if dark:
        return """
        QMainWindow, QWidget {
            background: #1e1f22;
            color: #e8eaed;
        }
        QListWidget, QTextBrowser {
            background: #2b2d31;
            color: #e8eaed;
            border: 1px solid #3b3f45;
            border-radius: 10px;
            padding: 8px;
            font-size: 14px;
        }
        QPushButton {
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 10px;
            padding: 10px 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background: #2563eb;
        }
        QLabel {
            color: #e8eaed;
            font-size: 13px;
            font-weight: 600;
        }
        """
    return """
    QMainWindow, QWidget {
        background: #eef2f7;
        color: #111827;
    }
    QListWidget, QTextBrowser {
        background: white;
        color: #111827;
        border: 1px solid #d0d5dd;
        border-radius: 10px;
        padding: 8px;
        font-size: 14px;
    }
    QPushButton {
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 14px;
        font-weight: bold;
    }
    QPushButton:hover {
        background: #1d4ed8;
    }
    QLabel {
        color: #111827;
        font-size: 13px;
        font-weight: 600;
    }
    """


def set_windows_app_id(app_name: str) -> None:
    if os.name != "nt":
        return
    try:
        import ctypes
        safe_name = "".join(ch if ch.isalnum() else "." for ch in app_name).strip(".") or "SysPing"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(safe_name)
    except Exception:
        pass


def maybe_handle_admin_close_child() -> None:
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
        script_path = str(Path(__file__).resolve())
        params = f'"{script_path}" --authorize-close "{token_path}"'

    result = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        executable,
        params,
        str(Path(__file__).resolve().parent),
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


class ReceiverSignals(QObject):
    server_message = Signal(dict)
    server_status = Signal(str)


class ImportantAlertDialog(QDialog):
    def __init__(self, sender: str, text: str, dark: bool, app_name: str):
        super().__init__()
        self.setWindowTitle(f"{app_name} - FONTOS")
        self.setModal(True)
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.resize(560, 280)

        title = QLabel(f"Fontos üzenet érkezett: {sender}")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #ef4444;")

        body = QTextBrowser()
        body.setPlainText(text)

        ok_btn = QPushButton("Rendben")
        ok_btn.clicked.connect(self.accept)

        layout = QVBoxLayout()
        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(ok_btn, alignment=Qt.AlignRight)
        self.setLayout(layout)

    def show_centered(self):
        screen = QApplication.primaryScreen()
        if screen:
            geo = screen.availableGeometry()
            self.move(
                geo.x() + (geo.width() - self.width()) // 2,
                geo.y() + (geo.height() - self.height()) // 2
            )
        self.exec()


class ServerListenerThread(threading.Thread):
    def __init__(self, signals: ReceiverSignals):
        super().__init__(daemon=True)
        self.signals = signals
        self.running = True
        self.ws = None

    def run(self):
        while self.running:
            try:
                self.signals.server_status.emit("connecting")
                self.ws = create_connection(f"{SERVER_WS}/{MACHINE_NAME}", timeout=30)
                self.signals.server_status.emit("connected")

                last_heartbeat = time.time()

                while self.running:
                    if time.time() - last_heartbeat >= 30:
                        self.ws.send(json.dumps({"type": "heartbeat"}))
                        last_heartbeat = time.time()

                    self.ws.settimeout(1)
                    try:
                        raw = self.ws.recv()
                        if raw:
                            self.signals.server_message.emit(json.loads(raw))
                    except Exception:
                        pass

            except Exception as e:
                print("[Receiver] WebSocket hiba:", e)
                self.signals.server_status.emit("disconnected")
                time.sleep(5)

    def send_read(self, message_id: int):
        try:
            if self.ws:
                self.ws.send(json.dumps({"type": "message_read", "message_id": message_id}))
        except Exception:
            pass

    def stop(self):
        self.running = False
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass


class ReceiverWindow(QMainWindow):
    def __init__(self, dark: bool):
        super().__init__()
        self.dark = dark
        self.branding = fetch_branding()
        self.app_name = self.branding.get("app_name") or "SysPing"
        self.allow_real_exit = False

        self.setWindowTitle(f"{self.app_name} - {MACHINE_NAME}")
        self.resize(1050, 680)

        self.chats = {}
        self.unread = {}
        self.current_chat = None
        self.unread_important = {}

        self.signals = ReceiverSignals()
        self.signals.server_message.connect(self.handle_server_message)
        self.signals.server_status.connect(self.handle_server_status)

        self.server_thread = ServerListenerThread(self.signals)
        self.server_thread.start()

        self.chat_list = QListWidget()
        self.chat_list.currentItemChanged.connect(self.on_chat_selected)

        self.chat_view = QTextBrowser()
        self.chat_view.setOpenExternalLinks(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.addWidget(QLabel("Gépek / chat-ek"))
        left_layout.addWidget(self.chat_list)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.connection_label = QLabel("Kapcsolat: csatlakozás...")
        right_layout.addWidget(self.connection_label)
        right_layout.addWidget(self.chat_view)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([280, 760])
        self.setCentralWidget(splitter)

        self.setup_tray()
        self.load_recent_messages()

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_important_reminders)
        self.reminder_timer.start(60_000)

    def setup_tray(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.icon_normal = self.create_icon(False)
        self.icon_unread = self.create_icon(True)

        self.tray_icon.setIcon(self.icon_normal)
        self.setWindowIcon(self.icon_normal)
        self.tray_icon.setToolTip(f"{self.app_name}")

        menu = QMenu()
        open_action = QAction("Megnyitás", self)
        open_action.triggered.connect(self.restore_from_tray)
        menu.addAction(open_action)

        quit_action = QAction("Program leállítása (admin joggal)", self)
        quit_action.triggered.connect(self.request_full_exit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def load_recent_messages(self):
        try:
            data = http_get_json(f"/client/messages/{MACHINE_NAME}?limit=20")
            for item in data:
                sender = item.get("sender_display_name") or item["sender_machine"]
                msg = {
                    "message_id": item["id"],
                    "sender": sender,
                    "text": item["text"],
                    "important": item["is_important"],
                    "timestamp": item["created_at"],
                    "direction": "in",
                    "read_sent": item["status"] == "read",
                }
                self.chats.setdefault(sender, []).append(msg)

            self.refresh_chat_list()
        except Exception as e:
            print("[Receiver] History betöltési hiba:", e)

    def create_icon(self, unread: bool) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#2563eb"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(8, 8, 48, 48)

        if unread:
            painter.setBrush(QColor("#ef4444"))
            painter.drawEllipse(42, 6, 16, 16)

        painter.end()
        return QIcon(pixmap)

    def handle_server_status(self, status: str):
        labels = {
            "connecting": "Kapcsolat: csatlakozás...",
            "connected": "Kapcsolat: online",
            "disconnected": "Kapcsolat: megszakadt",
        }
        self.connection_label.setText(labels.get(status, status))

    def handle_server_message(self, payload: dict):
        if payload.get("type") != "message":
            return

        message_id = payload["message_id"]
        real_sender_machine = payload["sender_machine"]
        sender = payload.get("sender_display_name") or real_sender_machine
        text = payload["text"]
        important = payload["is_important"]
        timestamp = payload["created_at"]

        msg = {
            "message_id": message_id,
            "sender": sender,
            "text": text,
            "important": important,
            "timestamp": timestamp,
            "direction": "in",
            "read_sent": False,
        }

        self.chats.setdefault(sender, []).append(msg)
        self.unread.setdefault(sender, 0)

        if sender != self.current_chat or not self.isActiveWindow():
            self.unread[sender] += 1

        if important:
            self.unread_important[message_id] = {
                "sender": sender,
                "text": text,
                "last_reminder": datetime.min,
            }

        self.refresh_chat_list()
        if sender == self.current_chat:
            self.render_current_chat()

        self.update_tray_icon()

        short_text = text if len(text) <= 180 else text[:177] + "..."
        if important:
            self.tray_icon.showMessage(
                f"{self.app_name} - FONTOS - {sender}",
                short_text,
                QSystemTrayIcon.Critical,
                10000,
            )
            self.restore_from_tray()
            ImportantAlertDialog(sender, text, self.dark, self.app_name).show_centered()
        else:
            self.tray_icon.showMessage(
                f"{self.app_name} - Új üzenet: {sender}",
                short_text,
                QSystemTrayIcon.Information,
                7000,
            )

    def check_important_reminders(self):
        now = datetime.now()
        for message_id, item in list(self.unread_important.items()):
            if now - item["last_reminder"] >= timedelta(minutes=10):
                short_text = item["text"] if len(item["text"]) <= 180 else item["text"][:177] + "..."
                self.tray_icon.showMessage(
                    f"{self.app_name} - FONTOS olvasatlan üzenet: {item['sender']}",
                    short_text,
                    QSystemTrayIcon.Critical,
                    10000,
                )
                item["last_reminder"] = now

    def refresh_chat_list(self):
        current = self.current_chat
        self.chat_list.clear()

        for sender in sorted(self.chats.keys(), key=lambda s: s.lower()):
            unread_count = self.unread.get(sender, 0)
            label = sender if unread_count == 0 else f"{sender} ({unread_count})"

            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, sender)

            if unread_count > 0:
                font = QFont()
                font.setBold(True)
                item.setFont(font)

            self.chat_list.addItem(item)

        if current:
            for i in range(self.chat_list.count()):
                item = self.chat_list.item(i)
                if item.data(Qt.UserRole) == current:
                    self.chat_list.setCurrentItem(item)
                    break

    def on_chat_selected(self, current, previous):
        if not current:
            self.current_chat = None
            self.chat_view.clear()
            return

        sender = current.data(Qt.UserRole)
        self.current_chat = sender
        self.unread[sender] = 0
        self.refresh_chat_list()
        self.render_current_chat()
        self.mark_visible_messages_as_read(sender)
        self.update_tray_icon()

    def mark_visible_messages_as_read(self, sender: str):
        for msg in self.chats.get(sender, []):
            if msg["direction"] != "in":
                continue
            if msg.get("read_sent"):
                continue

            message_id = msg.get("message_id")
            if isinstance(message_id, int):
                self.server_thread.send_read(message_id)
                msg["read_sent"] = True
                self.unread_important.pop(message_id, None)

    def render_current_chat(self):
        if not self.current_chat:
            self.chat_view.clear()
            return

        messages = self.chats.get(self.current_chat, [])
        html = ["<div style='font-family:Segoe UI;'>"]

        for msg in messages:
            badge = ""
            bubble_bg = "#2b2d31" if self.dark else "#ffffff"
            border = "#3b3f45" if self.dark else "#d1d5db"
            meta = "#9ca3af" if self.dark else "#6b7280"
            text_color = "#e8eaed" if self.dark else "#111827"

            if msg["important"]:
                badge = (
                    "<div style='display:inline-block; background:#7f1d1d; color:#fecaca; padding:4px 8px; border-radius:10px; font-size:12px; font-weight:bold; margin-bottom:6px;'>FONTOS</div>"
                    if self.dark else
                    "<div style='display:inline-block; background:#fee2e2; color:#b91c1c; padding:4px 8px; border-radius:10px; font-size:12px; font-weight:bold; margin-bottom:6px;'>FONTOS</div>"
                )
                bubble_bg = "#3a2323" if self.dark else "#fff7f7"
                border = "#7f1d1d" if self.dark else "#fca5a5"

            html.append(f"""
                <div style="margin-bottom:14px;">
                    {badge}
                    <div style="background:{bubble_bg}; border:1px solid {border}; border-radius:14px; padding:10px 12px;">
                        <div style="font-size:12px; color:{meta}; margin-bottom:6px;">
                            {self.escape_html(msg["sender"])} • {self.escape_html(msg["timestamp"])}
                        </div>
                        <div style="font-size:14px; color:{text_color}; white-space:pre-wrap;">
                            {self.escape_html(msg["text"])}
                        </div>
                    </div>
                </div>
            """)

        html.append("</div>")
        self.chat_view.setHtml("".join(html))
        self.chat_view.verticalScrollBar().setValue(self.chat_view.verticalScrollBar().maximum())

    def update_tray_icon(self):
        total_unread = sum(self.unread.values())
        if total_unread > 0:
            self.tray_icon.setIcon(self.icon_unread)
            self.setWindowIcon(self.icon_unread)
            self.tray_icon.setToolTip(f"{self.app_name} - {total_unread} olvasatlan")
        else:
            self.tray_icon.setIcon(self.icon_normal)
            self.setWindowIcon(self.icon_normal)
            self.tray_icon.setToolTip(f"{self.app_name}")

    def request_full_exit(self):
        approved = request_admin_close_approval()
        if approved:
            self.allow_real_exit = True
            self.server_thread.stop()
            self.tray_icon.hide()
            QApplication.quit()
        else:
            QMessageBox.information(
                self,
                self.app_name,
                "A teljes leállításhoz rendszergazdai jóváhagyás szükséges.",
            )

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def restore_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_from_tray()

    @staticmethod
    def escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )


if __name__ == "__main__":
    maybe_handle_admin_close_child()

    app = QApplication(sys.argv)
    dark = is_dark_mode(app)

    branding = fetch_branding()
    app_name = branding.get("app_name") or "SysPing"

    set_windows_app_id(app_name)
    app.setApplicationName(app_name)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(build_stylesheet(dark))

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Hiba", "A system tray nem érhető el.")
        sys.exit(1)

    window = ReceiverWindow(dark)
    sys.exit(app.exec())