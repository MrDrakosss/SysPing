from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from db import SessionLocal
from runtime_state import online_clients
from schemas import MessageOut
from services.devices import set_device_offline, upsert_device
from services.messages import (
    deliver_pending_messages,
    list_recent_messages_for_machine,
    mark_message_read,
)

router = APIRouter(tags=["client_ws"])


@router.get("/client/messages/{machine_name}", response_model=list[MessageOut])
def client_recent_messages(machine_name: str, limit: int = 20):
    db: Session = SessionLocal()
    try:
        return list_recent_messages_for_machine(db, machine_name, limit=limit)
    finally:
        db.close()


@router.websocket("/ws/client/{machine_name}")
async def client_ws(websocket: WebSocket, machine_name: str):
    await websocket.accept()

    db: Session = SessionLocal()
    client_ip = websocket.client.host if websocket.client else ""

    try:
        print(f"[WS] Csatlakozott: {machine_name} ({client_ip})", flush=True)

        upsert_device(db, machine_name, client_ip)

        if machine_name not in online_clients:
            online_clients[machine_name] = []
        online_clients[machine_name].append(websocket)

        print(f"[WS] Online kliensek: {list(online_clients.keys())}", flush=True)

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
        sockets = online_clients.get(machine_name, [])
        if websocket in sockets:
            sockets.remove(websocket)

        if not sockets:
            online_clients.pop(machine_name, None)
            try:
                set_device_offline(db, machine_name)
            except Exception as e:
                print(f"[WS] Offline állapot mentési hiba {machine_name}: {e}", flush=True)

        print(f"[WS] Maradt online kliens: {list(online_clients.keys())}", flush=True)
        db.close()