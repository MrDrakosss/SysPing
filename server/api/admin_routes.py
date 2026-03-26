from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import (
    require_admin_user,
    require_manage_admin_users,
    require_manage_branding,
    require_manage_devices,
    require_token_header,
)
from db import get_db
from models import Device
from runtime_state import online_clients
from schemas import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    AppSettingOut,
    AppSettingUpdate,
    BulkSendMessageIn,
    DashboardStatsOut,
    DeviceOut,
    DeviceUpdate,
    MessageOut,
    SendMessageIn,
)
from services.devices import list_devices, restore_device, soft_delete_device, update_device
from services.messages import (
    create_bulk_messages,
    create_message,
    get_dashboard_message_stats,
    list_all_messages,
    list_messages_for_admin,
)
from services.settings import get_settings, update_settings
from services.users import create_admin_user, list_admin_users, update_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

online_clients = {}


def configure_online_clients(mapping: dict):
    global online_clients
    online_clients = mapping


@router.get("/dashboard/stats", response_model=DashboardStatsOut)
def admin_dashboard_stats(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)

    total_devices = db.scalar(select(func.count()).select_from(Device)) or 0
    online_devices = db.scalar(
        select(func.count()).select_from(Device).where(Device.is_online == True)  # noqa
    ) or 0

    msg_stats = get_dashboard_message_stats(db)

    return {
        "total_devices": total_devices,
        "online_devices": online_devices,
        "offline_devices": total_devices - online_devices,
        "queued_messages": msg_stats["queued_messages"],
        "total_messages": msg_stats["total_messages"],
        "avg_read_seconds": msg_stats["avg_read_seconds"],
    }


@router.get("/devices", response_model=list[DeviceOut])
def admin_list_devices(
    search: str = "",
    include_deleted: bool = False,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    return list_devices(db, search=search, include_deleted=include_deleted)


@router.patch("/devices/{device_id}", response_model=DeviceOut)
def admin_update_device(
    device_id: int,
    payload: DeviceUpdate,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_devices(user)

    device = update_device(db, device_id, payload)
    if not device:
        raise HTTPException(status_code=404, detail="Gép nem található")
    return device


@router.delete("/devices/{device_id}")
def admin_delete_device(
    device_id: int,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_devices(user)

    ok = soft_delete_device(db, device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Gép nem található")
    return {"ok": True}


@router.post("/devices/{device_id}/restore")
def admin_restore_device(
    device_id: int,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_devices(user)

    ok = restore_device(db, device_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Gép nem található")
    return {"ok": True}


@router.post("/messages", response_model=MessageOut)
async def admin_send_message(
    payload: SendMessageIn,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    if not user.can_send_messages and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nincs üzenetküldési jog")

    msg = await create_message(
        db=db,
        sender_machine=user.username,
        sender_admin_user_id=user.id,
        sender_display_name=payload.sender_display_name or user.display_name or user.username,
        recipient_machine=payload.recipient_machine,
        text=payload.text,
        is_important=payload.is_important,
        online_clients=online_clients,
    )
    return msg


@router.post("/messages/bulk")
async def admin_send_bulk_message(
    payload: BulkSendMessageIn,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    if not user.can_send_messages and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nincs üzenetküldési jog")

    items = await create_bulk_messages(
        db=db,
        sender_machine=user.username,
        sender_admin_user_id=user.id,
        sender_display_name=payload.sender_display_name or user.display_name or user.username,
        recipient_machines=payload.recipient_machines,
        text=payload.text,
        is_important=payload.is_important,
        online_clients=online_clients,
    )

    return {"ok": True, "count": len(items)}


@router.get("/messages/my", response_model=list[MessageOut])
def admin_my_messages(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    return list_messages_for_admin(db, user.id)


@router.get("/messages/all", response_model=list[MessageOut])
def admin_all_messages(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    if not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Csak superadmin érheti el")
    return list_all_messages(db)


@router.get("/settings", response_model=AppSettingOut)
def admin_get_settings(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    return get_settings(db)


@router.patch("/settings", response_model=AppSettingOut)
def admin_update_settings(
    payload: AppSettingUpdate,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_branding(user)
    return update_settings(db, payload)


@router.get("/users", response_model=list[AdminUserOut])
def admin_list_users(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_admin_users(user)
    return list_admin_users(db)


@router.post("/users", response_model=AdminUserOut)
def admin_create_user(
    payload: AdminUserCreate,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_admin_users(user)

    try:
        return create_admin_user(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_admin_users(user)

    updated = update_admin_user(db, user_id, payload)
    if not updated:
        raise HTTPException(status_code=404, detail="Felhasználó nem található")
    return updated