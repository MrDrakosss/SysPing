from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from models import Device
from schemas import DeviceUpdate


def upsert_device(db: Session, machine_name: str, ip: str | None = None) -> Device:
    try:
        device = db.execute(
            select(Device).where(Device.machine_name == machine_name)
        ).scalar_one_or_none()

        if not device:
            device = Device(
                machine_name=machine_name,
                display_name=machine_name,
            )

        if ip:
            device.last_ip = ip

        device.is_online = True
        device.is_deleted = False
        device.last_seen_at = datetime.utcnow()

        db.add(device)
        db.commit()
        db.refresh(device)
        return device
    except Exception:
        db.rollback()
        raise


def set_device_offline(db: Session, machine_name: str) -> None:
    try:
        device = db.execute(
            select(Device).where(Device.machine_name == machine_name)
        ).scalar_one_or_none()

        if device:
            db.refresh(device)
            device.is_online = False
            device.last_seen_at = datetime.utcnow()
            db.add(device)
            db.commit()
    except Exception:
        db.rollback()
        raise


def list_devices(db: Session, search: str = "", include_deleted: bool = False) -> list[Device]:
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
                Device.last_ip.like(pattern),
            )
        )

    stmt = stmt.order_by(Device.machine_name.asc())
    return db.execute(stmt).scalars().all()


def update_device(db: Session, device_id: int, payload: DeviceUpdate) -> Device | None:
    device = db.get(Device, device_id)
    if not device:
        return None

    try:
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
    except Exception:
        db.rollback()
        raise


def soft_delete_device(db: Session, device_id: int) -> bool:
    device = db.get(Device, device_id)
    if not device:
        return False

    try:
        device.is_deleted = True
        device.is_online = False
        db.add(device)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise


def restore_device(db: Session, device_id: int) -> bool:
    device = db.get(Device, device_id)
    if not device:
        return False

    try:
        device.is_deleted = False
        db.add(device)
        db.commit()
        return True
    except Exception:
        db.rollback()
        raise