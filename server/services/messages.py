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
        print(f"[MSG] Nincs aktív websocket ehhez: {machine_name}", flush=True)
        return

    pending = db.execute(
        select(Message)
        .where(Message.recipient_machine == machine_name)
        .where(Message.status == "queued")
        .order_by(Message.created_at.asc())
    ).scalars().all()

    print(f"[MSG] Pending üzenetek {machine_name} részére: {len(pending)}", flush=True)

    for msg in pending:
        payload = {
            "type": "message",
            "message_id": msg.id,
            "sender_machine": msg.sender_machine,
            "sender_display_name": msg.sender_display_name or msg.sender_machine,
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
                print(f"[MSG] Kiküldve websocketen: #{msg.id} -> {machine_name}", flush=True)
            except Exception as e:
                print(f"[MSG] Websocket küldési hiba #{msg.id}: {e}", flush=True)

        if delivered and msg.status == "queued":
            msg.status = "delivered"
            msg.delivered_at = datetime.utcnow()
            db.add(msg)

    db.commit()


async def create_message(
    db: Session,
    sender_machine: str,
    sender_admin_user_id: int | None,
    sender_display_name: str,
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
        sender_display_name=sender_display_name,
        recipient_machine=recipient_machine,
        text=text,
        is_important=is_important,
        status="queued",
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    print(f"[MSG] Új üzenet létrehozva #{msg.id} -> {recipient_machine}", flush=True)
    print(f"[MSG] Jelenlegi online kliensek: {list(online_clients.keys())}", flush=True)

    if recipient_machine in online_clients and online_clients.get(recipient_machine):
        await deliver_pending_messages(db, recipient_machine, online_clients)
        db.refresh(msg)
    else:
        print(f"[MSG] {recipient_machine} jelenleg nincs online websocket listában", flush=True)

    return msg


async def create_bulk_messages(
    db: Session,
    sender_machine: str,
    sender_admin_user_id: int | None,
    sender_display_name: str,
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
            sender_display_name=sender_display_name,
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

    if msg.status != "read":
        msg.status = "read"
        msg.read_at = datetime.utcnow()
        if msg.delivered_at is None:
            msg.delivered_at = msg.read_at
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