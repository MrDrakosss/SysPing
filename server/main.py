from datetime import datetime
from typing import Dict

from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from db import Base, engine, get_db
from models import Device, Message
from schemas import DeviceOut, DeviceUpdate, SendMessageIn

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Central Messenger Server")

# machine_name -> websocket
online_clients: Dict[str, WebSocket] = {}


def upsert_device(db: Session, machine_name: str, ip: str | None = None) -> Device:
    device = db.execute(
        select(Device).where(Device.machine_name == machine_name)
    ).scalar_one_or_none()

    if not device:
        device = Device(machine_name=machine_name, display_name=machine_name)

    if ip:
        device.last_ip = ip

    device.is_online = True
    device.last_seen_at = datetime.utcnow()
    device.is_deleted = False

    db.add(device)
    db.commit()
    db.refresh(device)
    return device


def set_device_offline(db: Session, machine_name: str):
    device = db.execute(
        select(Device).where(Device.machine_name == machine_name)
    ).scalar_one_or_none()

    if device:
        device.is_online = False
        device.last_seen_at = datetime.utcnow()
        db.add(device)
        db.commit()


async def deliver_pending_messages(db: Session, machine_name: str):
    ws = online_clients.get(machine_name)
    if not ws:
        return

    pending = db.execute(
        select(Message)
        .where(Message.recipient_machine == machine_name)
        .where(Message.status == "queued")
        .order_by(Message.created_at.asc())
    ).scalars().all()

    for msg in pending:
        await ws.send_json({
            "type": "message",
            "message_id": msg.id,
            "sender_machine": msg.sender_machine,
            "recipient_machine": msg.recipient_machine,
            "text": msg.text,
            "is_important": msg.is_important,
            "created_at": msg.created_at.isoformat(),
        })
        msg.status = "delivered"
        msg.delivered_at = datetime.utcnow()
        db.add(msg)

    db.commit()


@app.get("/admin/devices", response_model=list[DeviceOut])
def list_devices(
    search: str = Query(default=""),
    include_deleted: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    stmt = select(Device)

    if not include_deleted:
        stmt = stmt.where(Device.is_deleted == False)  # noqa

    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(
            or_(
                Device.machine_name.like(pattern),
                Device.display_name.like(pattern),
                Device.owner.like(pattern),
                Device.note.like(pattern),
            )
        )

    stmt = stmt.order_by(Device.machine_name.asc())
    return db.execute(stmt).scalars().all()


@app.patch("/admin/devices/{device_id}", response_model=DeviceOut)
def update_device(device_id: int, payload: DeviceUpdate, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Gép nem található")

    if payload.display_name is not None:
        device.display_name = payload.display_name
    if payload.owner is not None:
        device.owner = payload.owner
    if payload.note is not None:
        device.note = payload.note

    db.add(device)
    db.commit()
    db.refresh(device)
    return device


@app.delete("/admin/devices/{device_id}")
def delete_device(device_id: int, db: Session = Depends(get_db)):
    device = db.get(Device, device_id)
    if not device:
        raise HTTPException(status_code=404, detail="Gép nem található")

    device.is_deleted = True
    device.is_online = False
    db.add(device)
    db.commit()
    return {"ok": True}


@app.post("/admin/messages")
async def send_message(payload: SendMessageIn, db: Session = Depends(get_db)):
    recipient = db.execute(
        select(Device)
        .where(Device.machine_name == payload.recipient_machine)
        .where(Device.is_deleted == False)  # noqa
    ).scalar_one_or_none()

    if not recipient:
        raise HTTPException(status_code=404, detail="Célgép nem található")

    msg = Message(
        sender_machine=payload.sender_machine,
        recipient_machine=payload.recipient_machine,
        text=payload.text,
        is_important=payload.is_important,
        status="queued",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    if payload.recipient_machine in online_clients:
        await deliver_pending_messages(db, payload.recipient_machine)

    return {
        "ok": True,
        "message_id": msg.id,
        "queued_for": payload.recipient_machine,
        "is_online": recipient.is_online,
    }


@app.websocket("/ws/client/{machine_name}")
async def client_ws(websocket: WebSocket, machine_name: str):
    await websocket.accept()

    db = next(get_db())
    client_ip = websocket.client.host if websocket.client else ""

    try:
        upsert_device(db, machine_name, client_ip)
        online_clients[machine_name] = websocket
        await deliver_pending_messages(db, machine_name)

        while True:
            data = await websocket.receive_json()
            event_type = data.get("type")

            if event_type == "heartbeat":
                upsert_device(db, machine_name, client_ip)

            elif event_type == "message_read":
                message_id = data.get("message_id")
                msg = db.get(Message, message_id)
                if msg and msg.recipient_machine == machine_name:
                    msg.status = "read"
                    msg.read_at = datetime.utcnow()
                    db.add(msg)
                    db.commit()

    except WebSocketDisconnect:
        pass
    finally:
        online_clients.pop(machine_name, None)
        set_device_offline(db, machine_name)
        db.close()