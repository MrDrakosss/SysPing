"""
A fő Receiver ablak.
"""

from datetime import datetime, timedelta

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
    QSystemTrayIcon,
)

from receiver_app.chat_renderer import render_chat_html
from receiver_app.config import (
    APP_NAME,
    IMPORTANT_REMINDER_MINUTES,
    MACHINE_NAME,
    RECENT_MESSAGES_LIMIT,
    http_get_json,
)
from receiver_app.dialogs import ImportantAlertDialog
from receiver_app.tray import setup_tray
from receiver_app.utils import request_admin_close_approval
from receiver_app.websocket_client import ServerListenerThread

from receiver_app.cache_store import get_cached_messages, get_last_message_id, update_message_cache
from receiver_app.config import SERVER_HTTP
from common import http_get_json


class ReceiverSignals(QObject):
    """
    Qt signal konténer a websocket háttérszál és a fő UI között.
    """
    server_message = Signal(dict)
    server_status = Signal(str)


class ReceiverMainWindow(QMainWindow):
    """
    A chat felületet megjelenítő fő alkalmazásablak.
    """

    def __init__(self, dark: bool):
        super().__init__()
        self.dark = dark
        self.app_name = APP_NAME
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

        self.build_ui()
        setup_tray(self, self.app_name)

        self.server_thread = ServerListenerThread(self.signals)

        # Az indulás gyorsítása érdekében a hálózati műveletek később indulnak.
        QTimer.singleShot(50, self.start_background_services)

        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.check_important_reminders)
        self.reminder_timer.start(60_000)

    def build_ui(self):
        """
        Összerakja a fő ablak layoutját.
        """
        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(12)

        top_bar = QWidget()
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

    def load_recent_messages(self):
        """
        Először a helyi cache-ből tölt, majd csak az új üzeneteket kéri le a szervertől.
        """
        try:
            cached = get_cached_messages()
            for item in cached:
                sender_name = item.get("sender_display_name") or item["sender_machine"]
                msg = {
                    "message_id": item["id"],
                    "sender": sender_name,
                    "sender_machine": item["sender_machine"],
                    "text": item["text"],
                    "important": item["is_important"],
                    "timestamp": item["created_at"],
                    "direction": "in",
                    "read_sent": item.get("status") == "read",
                }
                self.chats.setdefault(sender_name, []).append(msg)

            self.refresh_chat_list(preserve_selection=False)

            latest = http_get_json(
                SERVER_HTTP,
                f"/client/messages/{MACHINE_NAME}?limit={RECENT_MESSAGES_LIMIT}"
            )

            last_id = get_last_message_id()
            new_items = [x for x in latest if int(x.get("id", 0) or 0) > last_id]

            if new_items:
                update_message_cache(new_items)

                for item in new_items:
                    sender_name = item.get("sender_display_name") or item["sender_machine"]
                    msg = {
                        "message_id": item["id"],
                        "sender": sender_name,
                        "sender_machine": item["sender_machine"],
                        "text": item["text"],
                        "important": item["is_important"],
                        "timestamp": item["created_at"],
                        "direction": "in",
                        "read_sent": item.get("status") == "read",
                    }
                    self.chats.setdefault(sender_name, []).append(msg)

                self.refresh_chat_list(preserve_selection=True)

        except Exception as e:
            print("[Receiver] History/cache betöltési hiba:", e)

    def handle_server_status(self, status: str):
        """
        Frissíti a kapcsolat állapotát mutató címkét.
        """
        labels = {
            "connecting": "Kapcsolat: csatlakozás...",
            "connected": "Kapcsolat: online",
            "disconnected": "Kapcsolat: megszakadt",
        }
        self.connection_label.setText(labels.get(status, status))

    def handle_server_message(self, payload: dict):
        """
        Feldolgozza a websocketen érkező új üzenetet.
        """
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
            ImportantAlertDialog(sender_name, text, self.app_name).show_centered()
        else:
            self.tray_icon.showMessage(
                f"{self.app_name} - Új üzenet: {sender_name}",
                short_text,
                QSystemTrayIcon.Information,
                7000,
            )
        
        update_message_cache([{
            "id": message_id,
            "sender_machine": sender_machine,
            "sender_display_name": sender_name,
            "recipient_machine": MACHINE_NAME,
            "text": text,
            "is_important": important,
            "status": "delivered",
            "created_at": timestamp,
            "delivered_at": timestamp,
            "read_at": None,
        }])

    def check_important_reminders(self):
        """
        10 percenként ismételt értesítést küld a még olvasatlan fontos üzenetekről.
        """
        now = datetime.now()
        for message_id, item in list(self.unread_important.items()):
            if now - item["last_reminder"] >= timedelta(minutes=IMPORTANT_REMINDER_MINUTES):
                short_text = item["text"] if len(item["text"]) <= 180 else item["text"][:177] + "..."
                self.tray_icon.showMessage(
                    f"{self.app_name} - FONTOS olvasatlan üzenet: {item['sender']}",
                    short_text,
                    QSystemTrayIcon.Critical,
                    10000,
                )
                item["last_reminder"] = now

    def refresh_chat_list(self, preserve_selection: bool = True):
        """
        Újraépíti a bal oldali chatlistát rekurzió nélkül.
        """
        if self._refreshing_chat_list:
            return

        self._refreshing_chat_list = True
        selected_chat = self.current_chat if preserve_selection else None

        try:
            self.chat_list.blockSignals(True)
            self.chat_list.clear()

            chats_sorted = sorted(
                self.chats.keys(),
                key=lambda s: (0 if self.unread.get(s, 0) > 0 else 1, s.lower()),
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
        """
        Chatváltáskor betölti a kiválasztott beszélgetést.
        """
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
        """
        A megnyitott chat összes még nem jelzett bejövő üzenetét olvasottnak jelöli.
        """
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
        """
        A jobb oldali chatnézetet rendereli.
        """
        if not self.current_chat:
            self.chat_view.clear()
            return

        messages = self.chats.get(self.current_chat, [])
        self.chat_view.setHtml(render_chat_html(messages, self.dark))
        self.chat_view.verticalScrollBar().setValue(self.chat_view.verticalScrollBar().maximum())

    def update_tray_icon(self):
        """
        Az olvasatlan üzenetek száma alapján frissíti a tray ikont.
        """
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
        """
        Admin jóváhagyással leállítja a teljes programot.
        """
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
        """
        Az X gomb hatására csak elrejti az ablakot, nem állítja le a programot.
        """
        event.ignore()
        self.hide()

    def restore_from_tray(self):
        """
        Visszahozza az ablakot a háttérből.
        """
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        """
        Dupla kattintásra megnyitja az ablakot a trayből.
        """
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore_from_tray()

    def start_background_services(self):
        """
        Az UI megjelenése után indítja el a háttérszolgáltatásokat,
        így az ablak gyorsabban jelenik meg.
        """
        try:
            self.server_thread.start()
        except Exception as e:
            print("[Receiver] Websocket indítási hiba:", e)

        QTimer.singleShot(50, self.load_recent_messages)