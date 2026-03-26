from datetime import datetime
from typing import Dict, List

from fastapi import HTTPException, WebSocket
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import Device, Message


async def deliver_pending_messages(
    db: Session,
    machine_name: str,
    online_clients: Dict[str, List[WebSocket]],
) -> None:
    sockets = online_clients.get(machine_name, [])
    if not sockets:
        return

    pending = db.execute(
        select(Message)
        .where(Message.recipient_machine == machine_name)
        .where(Message.status == "queued")
        .order_by(Message.created_at.asc())
    ).scalars().all()

    for msg in pending:
        payload = {
            "type": "message",
            "message_id": msg.id,
            "sender_machine": msg.sender_machine,
            "recipient_machine": msg.recipient_machine,
            "text": msg.text,
            "is_important": msg.is_important,
            "created_at": msg.created_at.isoformat(),
        }

        delivered = False
        for ws in list(sockets):
            try:
                await ws.send_json(payload)
                delivered = True
            except Exception:
                pass

        if delivered:
            msg.status = "delivered"
            msg.delivered_at = datetime.utcnow()
            db.add(msg)

    db.commit()


async def create_message(
    db: Session,
    sender_machine: str,
    sender_admin_user_id: int | None,
    recipient_machine: str,
    text: str,
    is_important: bool,
    online_clients: Dict[str, List[WebSocket]],
) -> Message:
    recipient = db.execute(
        select(Device)
        .where(Device.machine_name == recipient_machine)
        .where(Device.is_deleted == False)  # noqa
    ).scalar_one_or_none()

    if not recipient:
        raise HTTPException(status_code=404, detail=f"Célgép nem található: {recipient_machine}")

    msg = Message(
        sender_machine=sender_machine,
        sender_admin_user_id=sender_admin_user_id,
        recipient_machine=recipient_machine,
        text=text,
        is_important=is_important,
        status="queued",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    if recipient_machine in online_clients:
        await deliver_pending_messages(db, recipient_machine, online_clients)

    return msg


async def create_bulk_messages(
    db: Session,
    sender_machine: str,
    sender_admin_user_id: int | None,
    recipient_machines: list[str],
    text: str,
    is_important: bool,
    online_clients: Dict[str, List[WebSocket]],
) -> list[Message]:
    created: list[Message] = []

    for recipient_machine in recipient_machines:
        msg = await create_message(
            db=db,
            sender_machine=sender_machine,
            sender_admin_user_id=sender_admin_user_id,
            recipient_machine=recipient_machine,
            text=text,
            is_important=is_important,
            online_clients=online_clients,
        )
        created.append(msg)

    return created


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


def list_recent_messages_for_machine(db: Session, machine_name: str, limit: int = 20) -> list[Message]:
    items = db.execute(
        select(Message)
        .where(Message.recipient_machine == machine_name)
        .order_by(Message.created_at.desc())
        .limit(limit)
    ).scalars().all()

    return list(reversed(items))


def list_messages_for_admin(db: Session, admin_user_id: int) -> list[Message]:
    return db.execute(
        select(Message)
        .where(Message.sender_admin_user_id == admin_user_id)
        .order_by(Message.created_at.desc())
    ).scalars().all()


def list_all_messages(db: Session) -> list[Message]:
    return db.execute(
        select(Message).order_by(Message.created_at.desc())
    ).scalars().all()


def get_dashboard_message_stats(db: Session) -> dict:
    total_messages = db.execute(select(Message)).scalars().all()
    read_messages = [m for m in total_messages if m.read_at is not None and m.created_at is not None]

    if read_messages:
        avg_read_seconds = sum(
            (m.read_at - m.created_at).total_seconds() for m in read_messages
        ) / len(read_messages)
    else:
        avg_read_seconds = 0.0

    queued_messages = sum(1 for m in total_messages if m.status == "queued")

    return {
        "total_messages": len(total_messages),
        "queued_messages": queued_messages,
        "avg_read_seconds": avg_read_seconds,
    }