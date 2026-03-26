"""
A háttérben futó websocket kliens.
"""

import json
import threading
import time

from websocket import create_connection

from receiver_app.config import HEARTBEAT_SECONDS, MACHINE_NAME, SERVER_WS


class ReceiverSignalsMixin:
    """
    Dokumentációs segédtípus: olyan objektum kell, amin server_message és server_status signal van.
    """
    pass


class ServerListenerThread(threading.Thread):
    """
    Háttérszál, amely fenntartja a websocket kapcsolatot a szerverrel.
    """

    def __init__(self, signals):
        super().__init__(daemon=True)
        self.signals = signals
        self.running = True
        self.ws = None

    def run(self):
        """
        Folyamatosan kapcsolódik a szerverhez, fogadja az üzeneteket és heartbeat-et küld.
        """
        while self.running:
            try:
                self.signals.server_status.emit("connecting")
                self.ws = create_connection(f"{SERVER_WS}/{MACHINE_NAME}", timeout=30)
                self.signals.server_status.emit("connected")

                last_heartbeat = time.time()

                while self.running:
                    if time.time() - last_heartbeat >= HEARTBEAT_SECONDS:
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
        """
        Olvasottnak jelölt üzenet státuszát elküldi a szervernek.
        """
        try:
            if self.ws:
                self.ws.send(json.dumps({"type": "message_read", "message_id": message_id}))
        except Exception:
            pass

    def stop(self):
        """
        Leállítja a websocket szálat és bezárja a kapcsolatot.
        """
        self.running = False
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass