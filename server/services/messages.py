from datetime import datetime
from typing import Dict

from sqlalchemy import select
from sqlalchemy.orm import Session
from fastapi import HTTPException, WebSocket

from models import Device, Message
from schemas import SendMessageIn


async def deliver_pending_messages(
    db: Session,
    machine_name: str,
    online_clients: Dict[str, WebSocket],
) -> None:
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
        await ws.send_json(
            {
                "type": "message",
                "message_id": msg.id,
                "sender_machine": msg.sender_machine,
                "recipient_machine": msg.recipient_machine,
                "text": msg.text,
                "is_important": msg.is_important,
                "created_at": msg.created_at.isoformat(),
            }
        )
        msg.status = "delivered"
        msg.delivered_at = datetime.utcnow()
        db.add(msg)

    db.commit()


async def create_message(
    db: Session,
    payload: SendMessageIn,
    online_clients: Dict[str, WebSocket],
) -> dict:
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
        await deliver_pending_messages(db, payload.recipient_machine, online_clients)

    return {
        "ok": True,
        "message_id": msg.id,
        "queued_for": payload.recipient_machine,
        "is_online": recipient.is_online,
    }


def mark_message_read(db: Session, machine_name: str, message_id: int) -> bool:
    msg = db.get(Message, message_id)
    if not msg:
        return False

    if msg.recipient_machine != machine_name:
        return False

    msg.status = "read"
    msg.read_at = datetime.utcnow()
    db.add(msg)
    db.commit()
    return True