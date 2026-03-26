"""
Kliens oldali websocket és history endpointok.

Feladatai:
- websocket kapcsolat fogadása a receiver kliensektől
- online állapot kezelése
- pending üzenetek kiküldése csatlakozáskor
- üzenetek olvasottnak jelölése
- history / új üzenetek lekérése cache-hez
"""

from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from db import SessionLocal
from models import Message
from schemas import MessageOut
from services.devices import set_device_offline, upsert_device
from services.messages import deliver_pending_messages, mark_message_read

router = APIRouter(tags=["client_ws"])

# Az aktuálisan online kliensek websocket kapcsolatai gépnév alapján.
online_clients: Dict[str, WebSocket] = {}


def get_online_clients() -> Dict[str, WebSocket]:
    """
    Visszaadja az online websocket klienseket.

    Erre az admin és webadmin oldali azonnali üzenetküldéshez van szükség.
    """
    return online_clients


@router.get("/client/messages/{machine_name}", response_model=list[MessageOut])
def client_recent_messages(
    machine_name: str,
    limit: int = 20,
    after_id: int = 0,
):
    """
    Visszaadja a kliens számára az üzenethistoryt.

    Működés:
    - ha after_id = 0, akkor az utolsó `limit` üzenetet adja vissza
    - ha after_id > 0, akkor csak az ennél újabb üzeneteket adja vissza

    Ez ideális helyi cache használatához.
    """
    db: Session = SessionLocal()
    try:
        stmt = select(Message).where(Message.recipient_machine == machine_name)

        if after_id > 0:
            stmt = stmt.where(Message.id > after_id).order_by(Message.id.asc()).limit(limit)
            items = db.execute(stmt).scalars().all()
            return items

        stmt = stmt.order_by(Message.created_at.desc()).limit(limit)
        items = db.execute(stmt).scalars().all()

        # A legutóbbi üzeneteket időrendbe rakjuk vissza, hogy szépen jelenjenek meg a kliensen.
        return list(reversed(items))
    finally:
        db.close()


@router.websocket("/ws/client/{machine_name}")
async def client_ws(websocket: WebSocket, machine_name: str):
    """
    Websocket kapcsolat a receiver kliens és a szerver között.

    Feladata:
    - kapcsolat elfogadása
    - kliens online státuszba állítása
    - pending üzenetek kiküldése
    - heartbeat fogadása
    - message_read esemény kezelése
    - lecsatlakozáskor offline állapot mentése
    """
    await websocket.accept()

    db: Session = SessionLocal()
    client_ip = websocket.client.host if websocket.client else ""

    try:
        print(f"[WS] Csatlakozott: {machine_name} ({client_ip})", flush=True)

        upsert_device(db, machine_name, client_ip)
        online_clients[machine_name] = websocket

        await deliver_pending_messages(db, machine_name, online_clients)

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "heartbeat":
                upsert_device(db, machine_name, client_ip)

            elif event_type == "message_read":
                message_id = data.get("message_id")
                if isinstance(message_id, int):
                    mark_message_read(db, machine_name, message_id)

    except WebSocketDisconnect:
        print(f"[WS] Lecsatlakozott: {machine_name}", flush=True)

    except Exception as e:
        print(f"[WS] Hiba {machine_name} esetén: {e}", flush=True)

    finally:
        online_clients.pop(machine_name, None)
        try:
            set_device_offline(db, machine_name)
        finally:
            db.close()