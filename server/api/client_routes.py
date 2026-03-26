from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from db import SessionLocal
from services.devices import set_device_offline, upsert_device
from services.messages import deliver_pending_messages, mark_message_read

router = APIRouter(tags=["client_ws"])

online_clients: Dict[str, WebSocket] = {}


def get_online_clients() -> Dict[str, WebSocket]:
    return online_clients


@router.websocket("/ws/client/{machine_name}")
async def client_ws(websocket: WebSocket, machine_name: str):
    await websocket.accept()

    db: Session = SessionLocal()
    client_ip = websocket.client.host if websocket.client else ""

    try:
        print(f"[WS] Csatlakozott: {machine_name} ({client_ip})")

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
        print(f"[WS] Lecsatlakozott: {machine_name}")
    except Exception as e:
        print(f"[WS] Hiba {machine_name} esetén: {e}")
    finally:
        online_clients.pop(machine_name, None)
        set_device_offline(db, machine_name)
        db.close()