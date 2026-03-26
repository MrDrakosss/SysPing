import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from websocket import create_connection

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QHBoxLayout,
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
            background: #111827;
            color: #e5e7eb;
            font-family: "Segoe UI";
        }

        QListWidget {
            background: #0f172a;
            border: 1px solid #1f2937;
            border-radius: 18px;
            padding: 8px;
            outline: none;
        }

        QListWidget::item {
            background: transparent;
            border-radius: 14px;
            padding: 12px;
            margin: 4px 0;
        }

        QListWidget::item:selected {
            background: #1e3a8a;
            color: white;
        }

        QListWidget::item:hover {
            background: #1f2937;
        }

        QTextBrowser {
            background: #0b1220;
            border: 1px solid #1f2937;
            border-radius: 20px;
            padding: 12px;
        }

        QLabel {
            color: #e5e7eb;
        }

        QPushButton {
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 12px;
            padding: 10px 14px;
            font-weight: 600;
        }

        QPushButton:hover {
            background: #1d4ed8;
        }

        QMenu {
            background: #111827;
            color: #e5e7eb;
            border: 1px solid #1f2937;
            padding: 6px;
        }

        QMenu::item {
            padding: 8px 14px;
            border-radius: 8px;
        }

        QMenu::item:selected {
            background: #1f2937;
        }
        """
    return """
    QMainWindow, QWidget {
        background: #f8fafc;
        color: #0f172a;
        font-family: "Segoe UI";
    }

    QListWidget {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 8px;
        outline: none;
    }

    QListWidget::item {
        background: transparent;
        border-radius: 14px;
        padding: 12px;
        margin: 4px 0;
    }

    QListWidget::item:selected {
        background: #dbeafe;
        color: #1e3a8a;
    }

    QListWidget::item:hover {
        background: #f1f5f9;
    }

    QTextBrowser {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 20px;
        padding: 12px;
    }

    QLabel {
        color: #0f172a;
    }

    QPushButton {
        background: #2563eb;
        color: white;
        border: none;
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 600;
    }

    QPushButton:hover {
        background: #1d4ed8;
    }

    QMenu {
        background: white;
        color: #0f172a;
        border: 1px solid #e2e8f0;
        padding: 6px;
    }

    QMenu::item {
        padding: 8px 14px;
        border-radius: 8px;
    }

    QMenu::item:selected {
        background: #eff6ff;
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
        self.resize(580, 320)

        title = QLabel(f"Fontos üzenet érkezett: {sender}")
        title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ef4444;")

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

        self.chats: dict[str, list[dict]] = {}
        self.unread: dict[str, int] = {}
        self.unread_important: dict[int, dict] = {}
        self.current_chat: str | None = None
        self._refreshing_chat_list = False

        self.setWindowTitle(f"{self.app_name} - {MACHINE_NAME}")
        self.resize(1180, 760)

        self.signals = ReceiverSignals()
        self.signals.server_message.connect(self.handle_server_message)
        self.signals.server_status.connect(self.handle_server_status)

        self.server_thread = ServerListenerThread(self.signals)
        self.server_thread.start()

        self.build_ui()
        self.setup_tray()
        self.load_recent_messages()

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_important_reminders)
        self.reminder_timer.start(60_000)

    def build_ui(self):
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(12)

        top_bar = QWidget()
        top_bar.setStyleSheet("""
            QWidget {
                background: transparent;
            }
        """)
        top_layout = QHBoxLayout(top_bar)
        top_layout.setContentsMargins(0, 0, 0, 0)

        title_wrap = QVBoxLayout()
        self.title_label = QLabel(self.app_name)
        self.title_label.setStyleSheet("font-size: 24px; font-weight: 700;")
        self.subtitle_label = QLabel(f"Gép: {MACHINE_NAME}")
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #64748b;")
        title_wrap.addWidget(self.title_label)
        title_wrap.addWidget(self.subtitle_label)

        self.connection_label = QLabel("Kapcsolat: csatlakozás...")
        self.connection_label.setStyleSheet("""
            QLabel {
                padding: 8px 12px;
                border-radius: 999px;
                background: rgba(37, 99, 235, 0.12);
                color: #2563eb;
                font-weight: 600;
            }
        """)

        top_layout.addLayout(title_wrap)
        top_layout.addStretch()
        top_layout.addWidget(self.connection_label)

        self.chat_list = QListWidget()
        self.chat_list.currentItemChanged.connect(self.on_chat_selected)
        self.chat_list.setMinimumWidth(300)

        self.chat_view = QTextBrowser()
        self.chat_view.setOpenExternalLinks(False)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        left_header = QLabel("Beszélgetések")
        left_header.setStyleSheet("font-size: 16px; font-weight: 700;")
        left_layout.addWidget(left_header)
        left_layout.addWidget(self.chat_list)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        self.chat_header = QLabel("Válassz beszélgetést")
        self.chat_header.setStyleSheet("font-size: 16px; font-weight: 700;")
        right_layout.addWidget(self.chat_header)
        right_layout.addWidget(self.chat_view)

        splitter = QSplitter()
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([320, 820])

        root_layout.addWidget(top_bar)
        root_layout.addWidget(splitter)

        self.setCentralWidget(root)

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

        quit_action = QAction("Leállítás", self)
        quit_action.triggered.connect(self.request_full_exit)
        menu.addAction(quit_action)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def load_recent_messages(self):
        try:
            data = http_get_json(f"/client/messages/{MACHINE_NAME}?limit=20")
            for item in data:
                sender_name = item.get("sender_display_name") or item["sender_machine"]
                msg = {
                    "message_id": item["id"],
                    "sender": sender_name,
                    "sender_machine": item["sender_machine"],
                    "text": item["text"],
                    "important": item["is_important"],
                    "timestamp": item["created_at"],
                    "direction": "in",
                    "read_sent": item["status"] == "read",
                }
                self.chats.setdefault(sender_name, []).append(msg)

            self.refresh_chat_list(preserve_selection=False)
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
        sender_machine = payload["sender_machine"]
        sender_name = payload.get("sender_display_name") or sender_machine
        text = payload["text"]
        important = payload["is_important"]
        timestamp = payload["created_at"]

        msg = {
            "message_id": message_id,
            "sender": sender_name,
            "sender_machine": sender_machine,
            "text": text,
            "important": important,
            "timestamp": timestamp,
            "direction": "in",
            "read_sent": False,
        }

        self.chats.setdefault(sender_name, []).append(msg)
        self.unread.setdefault(sender_name, 0)

        if sender_name != self.current_chat or not self.isActiveWindow():
            self.unread[sender_name] += 1

        if important:
            self.unread_important[message_id] = {
                "sender": sender_name,
                "text": text,
                "last_reminder": datetime.min,
            }

        self.refresh_chat_list(preserve_selection=True)

        if sender_name == self.current_chat:
            self.render_current_chat()

        self.update_tray_icon()

        short_text = text if len(text) <= 180 else text[:177] + "..."
        if important:
            self.tray_icon.showMessage(
                f"{self.app_name} - FONTOS - {sender_name}",
                short_text,
                QSystemTrayIcon.Critical,
                10000,
            )
            self.restore_from_tray()
            ImportantAlertDialog(sender_name, text, self.dark, self.app_name).show_centered()
        else:
            self.tray_icon.showMessage(
                f"{self.app_name} - Új üzenet: {sender_name}",
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

    def refresh_chat_list(self, preserve_selection: bool = True):
        if self._refreshing_chat_list:
            return

        self._refreshing_chat_list = True
        selected_chat = self.current_chat if preserve_selection else None

        try:
            self.chat_list.blockSignals(True)
            self.chat_list.clear()

            chats_sorted = sorted(
                self.chats.keys(),
                key=lambda s: (
                    0 if self.unread.get(s, 0) > 0 else 1,
                    s.lower()
                )
            )

            selected_item_to_restore = None

            for sender in chats_sorted:
                unread_count = self.unread.get(sender, 0)
                last_text = self.chats[sender][-1]["text"] if self.chats[sender] else ""
                preview = last_text[:36] + "..." if len(last_text) > 36 else last_text

                label = sender
                if unread_count > 0:
                    label += f" ({unread_count})"
                if preview:
                    label += f"\n{preview}"

                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, sender)

                font = QFont()
                font.setBold(unread_count > 0)
                item.setFont(font)

                self.chat_list.addItem(item)

                if selected_chat and sender == selected_chat:
                    selected_item_to_restore = item

            if selected_item_to_restore is not None:
                self.chat_list.setCurrentItem(selected_item_to_restore)
            elif self.chat_list.count() > 0 and self.current_chat is None:
                self.chat_list.setCurrentRow(0)
                item = self.chat_list.currentItem()
                if item:
                    self.current_chat = item.data(Qt.UserRole)

        finally:
            self.chat_list.blockSignals(False)
            self._refreshing_chat_list = False

    def on_chat_selected(self, current, previous):
        if self._refreshing_chat_list:
            return

        if not current:
            self.current_chat = None
            self.chat_header.setText("Válassz beszélgetést")
            self.chat_view.clear()
            return

        sender = current.data(Qt.UserRole)
        if sender == self.current_chat and self.chat_view.toPlainText():
            return

        self.current_chat = sender
        self.chat_header.setText(sender)
        self.unread[sender] = 0

        self.mark_visible_messages_as_read(sender)
        self.render_current_chat()
        self.refresh_chat_list(preserve_selection=True)
        self.update_tray_icon()

    def mark_visible_messages_as_read(self, sender: str):
        changed = False
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
                changed = True

        if changed:
            self.update_tray_icon()

    def render_current_chat(self):
        if not self.current_chat:
            self.chat_view.clear()
            return

        messages = self.chats.get(self.current_chat, [])
        html = [
            "<div style='font-family: Segoe UI, Arial; padding: 4px;'>"
        ]

        dark_in_bg = "#1f2937"
        dark_out_bg = "#1d4ed8"
        dark_important_bg = "#3f1d1d"
        dark_border = "#374151"
        dark_meta = "#94a3b8"
        dark_text = "#e5e7eb"
        dark_out_text = "#ffffff"

        light_in_bg = "#ffffff"
        light_out_bg = "#dbeafe"
        light_important_bg = "#fff1f2"
        light_border = "#e2e8f0"
        light_meta = "#64748b"
        light_text = "#0f172a"

        for msg in messages:
            is_in = msg["direction"] == "in"
            align = "left" if is_in else "right"

            if self.dark:
                bg = dark_in_bg if is_in else dark_out_bg
                border = dark_border
                text_color = dark_text if is_in else dark_out_text
                meta_color = dark_meta
                if msg["important"]:
                    bg = dark_important_bg
                    border = "#7f1d1d"
            else:
                bg = light_in_bg if is_in else light_out_bg
                border = light_border
                text_color = light_text
                meta_color = light_meta
                if msg["important"]:
                    bg = light_important_bg
                    border = "#fda4af"

            badge = ""
            if msg["important"]:
                badge = (
                    "<div style='display:inline-block; margin-bottom:6px; "
                    "padding:4px 8px; border-radius:999px; font-size:11px; font-weight:700; "
                    "background:#fee2e2; color:#b91c1c;'>FONTOS</div>"
                )

            html.append(f"""
                <div style="margin-bottom: 14px; text-align: {align};">
                    <div style="display:inline-block; max-width: 75%; text-align:left;">
                        {badge}
                        <div style="
                            background:{bg};
                            border:1px solid {border};
                            border-radius:18px;
                            padding:10px 12px;
                            box-shadow: 0 4px 12px rgba(0,0,0,0.06);
                        ">
                            <div style="font-size:11px; color:{meta_color}; margin-bottom:6px; font-weight:600;">
                                {self.escape_html(msg['sender'])}
                            </div>
                            <div style="font-size:14px; color:{text_color}; white-space:pre-wrap; line-height:1.45;">
                                {self.escape_html(msg['text'])}
                            </div>
                            <div style="font-size:10px; color:{meta_color}; margin-top:8px; text-align:right;">
                                {self.escape_html(msg['timestamp'])}
                            </div>
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
            self.tray_icon.setToolTip(self.app_name)

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
            str(text).replace("&", "&amp;")
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