import json
import sys
import threading
import time
import urllib.parse
import urllib.request

from websocket import create_connection

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from common import (
    MACHINE_NAME,
    SERVER_HTTP,
    SERVER_WS,
    clear_admin_token,
    fetch_branding,
    load_admin_token,
    save_admin_token,
)


def http_json(path: str, method: str = "GET", payload: dict | None = None, token: str | None = None):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    if token:
        headers["Authorization"] = f"Bearer {token}"

    req = urllib.request.Request(
        f"{SERVER_HTTP}{path}",
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


class AdminSignals(QObject):
    server_message = Signal(dict)
    server_status = Signal(str)


class ServerListenerThread(threading.Thread):
    def __init__(self, signals: AdminSignals):
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

            except Exception:
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


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.branding = fetch_branding()
        self.setWindowTitle(f"{self.branding.get('app_name', 'SysPing')} Admin Login")
        self.resize(380, 180)
        self.token = None
        self.user = None

        self.username_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        form = QFormLayout()
        form.addRow("Felhasználónév:", self.username_input)
        form.addRow("Jelszó:", self.password_input)

        login_btn = QPushButton("Belépés")
        login_btn.clicked.connect(self.try_login)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(login_btn, alignment=Qt.AlignRight)
        self.setLayout(layout)

    def try_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not username or not password:
            QMessageBox.warning(self, "Hiba", "Add meg a felhasználónevet és a jelszót.")
            return

        try:
            result = http_json("/auth/login", method="POST", payload={
                "username": username,
                "password": password,
            })
            self.token = result["token"]
            self.user = result["user"]
            save_admin_token(self.token, self.user)
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Belépési hiba", str(e))


class AdminChatWindow(QMainWindow):
    def __init__(self, token: str, user_info: dict):
        super().__init__()
        self.token = token
        self.user_info = user_info
        self.branding = fetch_branding()

        self.setWindowTitle(f"{self.branding.get('app_name', 'SysPing')} Admin - {user_info['username']} - {MACHINE_NAME}")
        self.resize(1500, 850)

        self.devices = []
        self.chats = {}
        self.unread = {}
        self.current_chat = None

        self.signals = AdminSignals()
        self.signals.server_message.connect(self.handle_server_message)
        self.signals.server_status.connect(self.handle_server_status)

        self.server_thread = ServerListenerThread(self.signals)
        self.server_thread.start()

        self.build_ui()
        self.refresh_devices()
        self.refresh_chat_list()
        self.load_settings()

    def build_ui(self):
        self.tabs = QTabWidget()

        self.tab_chat = QWidget()
        self.tab_settings = QWidget()

        self.build_chat_tab()
        self.build_settings_tab()

        self.tabs.addTab(self.tab_chat, "Chat")
        self.tabs.addTab(self.tab_settings, "Beállítások")

        root = QWidget()
        root_layout = QVBoxLayout(root)

        top_bar = QHBoxLayout()
        self.connection_label = QLabel("Kapcsolat: csatlakozás...")
        self.logout_btn = QPushButton("Kijelentkezés")
        self.logout_btn.clicked.connect(self.logout)
        top_bar.addWidget(self.connection_label)
        top_bar.addStretch()
        top_bar.addWidget(self.logout_btn)

        root_layout.addLayout(top_bar)
        root_layout.addWidget(self.tabs)
        self.setCentralWidget(root)

        self.setStyleSheet("""
            QMainWindow { background: #eef2f7; }
            QListWidget, QTextBrowser, QLineEdit, QTextEdit, QTabWidget::pane {
                background: white;
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
            QPushButton:hover { background: #1d4ed8; }
            QLabel, QCheckBox { font-size: 13px; }
            QGroupBox {
                font-weight: 700;
                border: 1px solid #cfd8e3;
                border-radius: 12px;
                margin-top: 8px;
                padding-top: 12px;
            }
        """)

        self.setWindowIcon(self.create_icon())

    def build_chat_tab(self):
        layout = QVBoxLayout(self.tab_chat)

        self.chat_list = QListWidget()
        self.chat_list.currentItemChanged.connect(self.on_chat_selected)

        self.chat_view = QTextBrowser()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Keresés gépnévre, tulajdonosra, megjegyzésre...")
        self.search_input.textChanged.connect(self.refresh_devices)

        self.device_list = QListWidget()
        self.device_list.setSelectionMode(QAbstractItemView.MultiSelection)

        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Írd ide az üzenetet...")

        self.important_checkbox = QCheckBox("Fontos üzenet")

        self.send_btn = QPushButton("Küldés a kijelölt gépeknek")
        self.send_btn.clicked.connect(self.send_to_selected_devices)

        self.use_chat_btn = QPushButton("Aktív chat kijelölése")
        self.use_chat_btn.clicked.connect(self.use_current_chat_target)

        self.device_name_input = QLineEdit()
        self.display_name_input = QLineEdit()
        self.owner_input = QLineEdit()
        self.note_input = QTextEdit()
        self.note_input.setFixedHeight(100)

        self.save_device_btn = QPushButton("Eszköz mentése")
        self.save_device_btn.clicked.connect(self.save_selected_device)

        self.delete_device_btn = QPushButton("Eszköz archiválása")
        self.delete_device_btn.clicked.connect(self.archive_selected_device)
        self.delete_device_btn.setStyleSheet("background:#dc2626; color:white; border:none; border-radius:10px; padding:10px 14px; font-weight:bold;")

        left_box = QGroupBox("Chat-ek")
        left_layout = QVBoxLayout(left_box)
        left_layout.addWidget(self.chat_list)

        center_box = QGroupBox("Beszélgetés")
        center_layout = QVBoxLayout(center_box)
        center_layout.addWidget(self.chat_view)

        right_box = QGroupBox("Eszközök és küldés")
        right_layout = QVBoxLayout(right_box)
        right_layout.addWidget(self.search_input)
        right_layout.addWidget(self.device_list)
        right_layout.addWidget(self.use_chat_btn)
        right_layout.addWidget(self.important_checkbox)
        right_layout.addWidget(self.message_input)
        right_layout.addWidget(self.send_btn)

        meta_box = QGroupBox("Kiválasztott eszköz adatai")
        meta_form = QFormLayout(meta_box)
        meta_form.addRow("Gépnév:", self.device_name_input)
        meta_form.addRow("Megjelenített név:", self.display_name_input)
        meta_form.addRow("Tulajdonos:", self.owner_input)
        meta_form.addRow("Megjegyzés:", self.note_input)

        btns = QHBoxLayout()
        btns.addWidget(self.save_device_btn)
        btns.addWidget(self.delete_device_btn)
        meta_form.addRow("", btns)

        right_layout.addWidget(meta_box)

        self.device_list.itemSelectionChanged.connect(self.load_selected_device_meta)

        splitter = QSplitter()
        splitter.addWidget(left_box)
        splitter.addWidget(center_box)
        splitter.addWidget(right_box)
        splitter.setSizes([260, 620, 460])

        layout.addWidget(splitter)

    def build_settings_tab(self):
        layout = QVBoxLayout(self.tab_settings)

        settings_box = QGroupBox("Branding és szerver beállítások")
        form = QFormLayout(settings_box)

        self.settings_app_name = QLineEdit()
        self.settings_company_name = QLineEdit()
        self.settings_app_icon_path = QLineEdit()
        self.settings_login_logo_path = QLineEdit()
        self.settings_primary_color = QLineEdit()
        self.settings_secondary_color = QLineEdit()
        self.settings_web_admin_enabled = QCheckBox("Web admin engedélyezése")

        form.addRow("Program neve:", self.settings_app_name)
        form.addRow("Cég neve:", self.settings_company_name)
        form.addRow("App ikon útvonal:", self.settings_app_icon_path)
        form.addRow("Login logó útvonal:", self.settings_login_logo_path)
        form.addRow("Elsődleges szín:", self.settings_primary_color)
        form.addRow("Másodlagos szín:", self.settings_secondary_color)
        form.addRow("", self.settings_web_admin_enabled)

        self.save_settings_btn = QPushButton("Beállítások mentése")
        self.save_settings_btn.clicked.connect(self.save_settings)
        form.addRow("", self.save_settings_btn)

        layout.addWidget(settings_box)
        layout.addStretch()

    def create_icon(self) -> QIcon:
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#2563eb"))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(8, 8, 48, 48)
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

        sender = payload["sender_machine"]
        msg = {
            "message_id": payload["message_id"],
            "sender": sender,
            "text": payload["text"],
            "important": payload["is_important"],
            "timestamp": payload["created_at"],
            "direction": "in",
            "read_sent": False,
        }

        self.chats.setdefault(sender, []).append(msg)
        self.unread.setdefault(sender, 0)

        if sender != self.current_chat or not self.isActiveWindow():
            self.unread[sender] += 1

        self.refresh_chat_list()
        if sender == self.current_chat:
            self.render_current_chat()

    def refresh_devices(self):
        try:
            search = urllib.parse.quote(self.search_input.text().strip())
            data = http_json(
                f"/admin/devices?search={search}",
                method="GET",
                token=self.token,
            )
            self.devices = data
            self.device_list.clear()

            for device in self.devices:
                label = f"{device['machine_name']}  |  {'online' if device['is_online'] else 'offline'}"
                if device.get("owner"):
                    label += f"  |  {device['owner']}"
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, device)

                if device["is_online"]:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)

                self.device_list.addItem(item)

        except Exception as e:
            QMessageBox.warning(self, "Eszközlista hiba", str(e))

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
        self.mark_current_chat_read()

    def mark_current_chat_read(self):
        if not self.current_chat:
            return

        for msg in self.chats.get(self.current_chat, []):
            if msg["direction"] == "in" and not msg.get("read_sent"):
                message_id = msg.get("message_id")
                if isinstance(message_id, int):
                    self.server_thread.send_read(message_id)
                    msg["read_sent"] = True

    def render_current_chat(self):
        if not self.current_chat:
            self.chat_view.clear()
            return

        messages = self.chats.get(self.current_chat, [])
        html = ["<div style='font-family:Segoe UI;'>"]

        for msg in messages:
            align = "left" if msg["direction"] == "in" else "right"
            bg = "#ffffff" if msg["direction"] == "in" else "#dbeafe"
            border = "#d1d5db" if msg["direction"] == "in" else "#93c5fd"

            badge = ""
            if msg["important"]:
                badge = (
                    "<div style='display:inline-block; background:#fee2e2; color:#b91c1c; "
                    "padding:4px 8px; border-radius:10px; font-size:12px; font-weight:bold; "
                    "margin-bottom:6px;'>FONTOS</div>"
                )

            html.append(f"""
                <div style="margin-bottom:14px; text-align:{align};">
                    {badge}
                    <div style="
                        display:inline-block;
                        max-width:78%;
                        text-align:left;
                        background:{bg};
                        border:1px solid {border};
                        border-radius:14px;
                        padding:10px 12px;">
                        <div style="font-size:12px; color:#6b7280; margin-bottom:6px;">
                            {self.escape_html(msg["sender"])} • {self.escape_html(msg["timestamp"])}
                        </div>
                        <div style="font-size:14px; color:#111827; white-space:pre-wrap;">
                            {self.escape_html(msg["text"])}
                        </div>
                    </div>
                </div>
            """)

        html.append("</div>")
        self.chat_view.setHtml("".join(html))
        self.chat_view.verticalScrollBar().setValue(self.chat_view.verticalScrollBar().maximum())

    def selected_devices(self):
        return [item.data(Qt.UserRole) for item in self.device_list.selectedItems()]

    def send_to_selected_devices(self):
        selected = self.selected_devices()
        if not selected:
            QMessageBox.information(self, "Nincs kijelölés", "Jelölj ki legalább egy gépet.")
            return

        text = self.message_input.toPlainText().strip()
        important = self.important_checkbox.isChecked()

        if not text:
            QMessageBox.warning(self, "Hiba", "Az üzenet nem lehet üres.")
            return

        ok_count = 0
        errors = []

        for device in selected:
            try:
                http_json(
                    "/admin/messages",
                    method="POST",
                    payload={
                        "sender_machine": MACHINE_NAME,
                        "recipient_machine": device["machine_name"],
                        "text": text,
                        "is_important": important,
                    },
                    token=self.token,
                )

                self.chats.setdefault(device["machine_name"], []).append({
                    "message_id": 0,
                    "sender": MACHINE_NAME,
                    "text": text,
                    "important": important,
                    "timestamp": "most",
                    "direction": "out",
                    "read_sent": True,
                })
                ok_count += 1

            except Exception as e:
                errors.append(f"{device['machine_name']}: {e}")

        self.message_input.clear()
        self.refresh_chat_list()
        if self.current_chat:
            self.render_current_chat()

        if errors:
            QMessageBox.warning(
                self,
                "Részben sikeres küldés",
                f"Sikeres: {ok_count}\n\nHibák:\n" + "\n".join(errors),
            )
        else:
            QMessageBox.information(self, "Küldés kész", f"Sikeresen elküldve {ok_count} gépnek.")

    def use_current_chat_target(self):
        if not self.current_chat:
            QMessageBox.information(self, "Nincs aktív chat", "Előbb válassz egy chatet.")
            return

        for i in range(self.device_list.count()):
            item = self.device_list.item(i)
            device = item.data(Qt.UserRole)
            item.setSelected(device["machine_name"] == self.current_chat)

    def load_selected_device_meta(self):
        selected = self.selected_devices()
        if len(selected) != 1:
            self.device_name_input.clear()
            self.display_name_input.clear()
            self.owner_input.clear()
            self.note_input.clear()
            return

        device = selected[0]
        self.device_name_input.setText(device["machine_name"])
        self.display_name_input.setText(device.get("display_name", ""))
        self.owner_input.setText(device.get("owner", ""))
        self.note_input.setPlainText(device.get("note", ""))

    def save_selected_device(self):
        selected = self.selected_devices()
        if len(selected) != 1:
            QMessageBox.information(self, "Hiba", "Pontosan egy eszközt válassz a mentéshez.")
            return

        device = selected[0]

        try:
            http_json(
                f"/admin/devices/{device['id']}",
                method="PATCH",
                payload={
                    "display_name": self.display_name_input.text().strip(),
                    "owner": self.owner_input.text().strip(),
                    "note": self.note_input.toPlainText().strip(),
                },
                token=self.token,
            )
            self.refresh_devices()
            QMessageBox.information(self, "Mentés", "Eszköz adatai frissítve.")
        except Exception as e:
            QMessageBox.warning(self, "Mentési hiba", str(e))

    def archive_selected_device(self):
        selected = self.selected_devices()
        if len(selected) != 1:
            QMessageBox.information(self, "Hiba", "Pontosan egy eszközt válassz.")
            return

        device = selected[0]
        try:
            http_json(f"/admin/devices/{device['id']}", method="DELETE", token=self.token)
            self.refresh_devices()
            QMessageBox.information(self, "Archiválás", "Az eszköz archiválva lett.")
        except Exception as e:
            QMessageBox.warning(self, "Archiválási hiba", str(e))

    def load_settings(self):
        try:
            settings = http_json("/admin/settings", method="GET", token=self.token)
            self.settings_app_name.setText(settings.get("app_name", ""))
            self.settings_company_name.setText(settings.get("company_name", ""))
            self.settings_app_icon_path.setText(settings.get("app_icon_path", ""))
            self.settings_login_logo_path.setText(settings.get("login_logo_path", ""))
            self.settings_primary_color.setText(settings.get("primary_color", ""))
            self.settings_secondary_color.setText(settings.get("secondary_color", ""))
            self.settings_web_admin_enabled.setChecked(settings.get("web_admin_enabled", False))
        except Exception:
            pass

    def save_settings(self):
        try:
            http_json(
                "/admin/settings",
                method="PATCH",
                payload={
                    "app_name": self.settings_app_name.text().strip(),
                    "company_name": self.settings_company_name.text().strip(),
                    "app_icon_path": self.settings_app_icon_path.text().strip(),
                    "login_logo_path": self.settings_login_logo_path.text().strip(),
                    "primary_color": self.settings_primary_color.text().strip(),
                    "secondary_color": self.settings_secondary_color.text().strip(),
                    "web_admin_enabled": self.settings_web_admin_enabled.isChecked(),
                },
                token=self.token,
            )
            QMessageBox.information(self, "Mentés", "Beállítások frissítve.")
        except Exception as e:
            QMessageBox.warning(self, "Mentési hiba", str(e))

    def logout(self):
        try:
            http_json("/auth/logout", method="POST", token=self.token)
        except Exception:
            pass
        clear_admin_token()
        self.server_thread.stop()
        self.close()

    def closeEvent(self, event):
        self.server_thread.stop()
        event.accept()

    @staticmethod
    def escape_html(text: str) -> str:
        return (
            text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)

    token, user = load_admin_token()

    if token and user:
        try:
            http_json("/auth/me", method="GET", token=token)
            window = AdminChatWindow(token, user)
            window.show()
            sys.exit(app.exec())
        except Exception:
            clear_admin_token()

    login = LoginDialog()
    if login.exec() != QDialog.Accepted:
        sys.exit(0)

    window = AdminChatWindow(login.token, login.user)
    window.show()
    sys.exit(app.exec())