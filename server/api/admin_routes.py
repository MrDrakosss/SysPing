from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import (
    require_admin_user,
    require_manage_admin_users,
    require_manage_branding,
    require_manage_devices,
    require_token_header,
)
from db import get_db
from schemas import (
    AdminUserCreate,
    AdminUserOut,
    AdminUserUpdate,
    AppSettingOut,
    AppSettingUpdate,
    DeviceOut,
    DeviceUpdate,
    SendMessageIn,
)
from services.devices import list_devices, soft_delete_device, update_device
from services.messages import create_message
from services.settings import get_settings, update_settings
from services.users import create_admin_user, list_admin_users, update_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])

# machine_name -> websocket
online_clients = {}


def configure_online_clients(mapping: dict):
    global online_clients
    online_clients = mapping


@router.get("/devices", response_model=list[DeviceOut])
def admin_list_devices(
    search: str = "",
    include_deleted: bool = False,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_devices(user)
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


@router.post("/messages")
async def admin_send_message(
    payload: SendMessageIn,
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    if not user.can_send_messages and not user.is_superadmin:
        raise HTTPException(status_code=403, detail="Nincs üzenetküldési jog")

    return await create_message(db, payload, online_clients)


@router.get("/settings", response_model=AppSettingOut)
def admin_get_settings(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    require_manage_branding(user)
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