import os
import secrets
import shutil
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from pathlib import Path
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import authenticate_user
from db import get_db
from models import AdminUser, Device, Message
from schemas import AdminUserCreate, AdminUserUpdate, AppSettingUpdate, DeviceUpdate
from services.devices import list_devices, restore_device, soft_delete_device, update_device
from services.settings import get_settings, update_settings
from services.users import create_admin_user, list_admin_users, update_admin_user

router = APIRouter(prefix="/webadmin", tags=["webadmin"])
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

WEB_SESSIONS: Dict[str, int] = {}
UPLOADS_DIR = Path("webadmin/static/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def save_upload(file: UploadFile | None, prefix: str) -> str:
    if not file or not file.filename:
        return ""

    filename = f"{prefix}_{secrets.token_hex(8)}_{Path(file.filename).name}"
    target = UPLOADS_DIR / filename

    with target.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    return f"/webadmin/static/uploads/{filename}"


def get_web_user(request: Request, db: Session) -> AdminUser | None:
    token = request.cookies.get("webadmin_session")
    if not token:
        return None

    user_id = WEB_SESSIONS.get(token)
    if not user_id:
        return None

    user = db.get(AdminUser, user_id)
    if not user or not user.is_active or not user.can_login_web_admin:
        return None

    return user


def require_web_user(request: Request, db: Session) -> AdminUser:
    user = get_web_user(request, db)
    if not user:
        raise PermissionError("Nincs belépve vagy nincs web admin jogosultság")
    return user


def redirect_to_login() -> RedirectResponse:
    return RedirectResponse(url="/webadmin/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def webadmin_login_page(request: Request, db: Session = Depends(get_db)):
    settings = get_settings(db)
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "settings": settings,
            "error": None,
        },
    )


@router.post("/login", response_class=HTMLResponse)
def webadmin_login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    settings = get_settings(db)
    user = authenticate_user(db, username.strip(), password)

    if not user or not user.can_login_web_admin:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "settings": settings,
                "error": "Hibás belépési adatok vagy nincs web admin jogosultság.",
            },
            status_code=401,
        )

    session_token = secrets.token_urlsafe(32)
    WEB_SESSIONS[session_token] = user.id

    response = RedirectResponse(url="/webadmin/", status_code=303)
    response.set_cookie(
        key="webadmin_session",
        value=session_token,
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/logout")
def webadmin_logout(request: Request):
    token = request.cookies.get("webadmin_session")
    if token:
        WEB_SESSIONS.pop(token, None)

    response = RedirectResponse(url="/webadmin/login", status_code=303)
    response.delete_cookie("webadmin_session")
    return response


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    settings = get_settings(db)

    total_devices = db.scalar(select(func.count()).select_from(Device)) or 0
    online_devices = db.scalar(
        select(func.count()).select_from(Device).where(Device.is_online == True)  # noqa
    ) or 0
    queued_messages = db.scalar(
        select(func.count()).select_from(Message).where(Message.status == "queued")
    ) or 0

    recent_devices = db.execute(
        select(Device)
        .where(Device.is_deleted == False)  # noqa
        .order_by(Device.last_seen_at.desc())
        .limit(10)
    ).scalars().all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
            "stats": {
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": total_devices - online_devices,
                "queued_messages": queued_messages,
            },
            "recent_devices": recent_devices,
        },
    )


@router.get("/devices", response_class=HTMLResponse)
def devices_page(
    request: Request,
    search: str = "",
    include_deleted: bool = False,
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    settings = get_settings(db)
    devices = list_devices(db, search=search, include_deleted=include_deleted)

    return templates.TemplateResponse(
        "devices.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
            "devices": devices,
            "search": search,
            "include_deleted": include_deleted,
        },
    )


@router.post("/devices/{device_id}/save")
def devices_save(
    request: Request,
    device_id: int,
    display_name: str = Form(""),
    owner: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    if not (user.is_superadmin or user.can_manage_devices):
        return RedirectResponse(url="/webadmin/devices", status_code=303)

    payload = DeviceUpdate(
        display_name=display_name,
        owner=owner,
        note=note,
    )
    update_device(db, device_id, payload)
    return RedirectResponse(url="/webadmin/devices", status_code=303)


@router.post("/devices/{device_id}/archive")
def devices_archive(
    request: Request,
    device_id: int,
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    if user.is_superadmin or user.can_manage_devices:
        soft_delete_device(db, device_id)

    return RedirectResponse(url="/webadmin/devices", status_code=303)


@router.post("/devices/{device_id}/restore")
def devices_restore(
    request: Request,
    device_id: int,
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    if user.is_superadmin or user.can_manage_devices:
        restore_device(db, device_id)

    return RedirectResponse(url="/webadmin/devices?include_deleted=true", status_code=303)


@router.get("/users", response_class=HTMLResponse)
def users_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    settings = get_settings(db)
    users = list_admin_users(db)

    return templates.TemplateResponse(
        "users.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
            "users": users,
        },
    )


@router.post("/users/create")
def users_create(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    is_active: str | None = Form(default=None),
    can_login_admin_gui: str | None = Form(default=None),
    can_login_web_admin: str | None = Form(default=None),
    is_superadmin: str | None = Form(default=None),
    can_send_messages: str | None = Form(default=None),
    can_manage_devices: str | None = Form(default=None),
    can_manage_branding: str | None = Form(default=None),
    can_manage_admin_users: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    if not (user.is_superadmin or user.can_manage_admin_users):
        return RedirectResponse(url="/webadmin/users", status_code=303)

    payload = AdminUserCreate(
        username=username.strip(),
        email=email.strip(),
        password=password,
        is_active=is_active is not None,
        can_login_admin_gui=can_login_admin_gui is not None,
        can_login_web_admin=can_login_web_admin is not None,
        is_superadmin=is_superadmin is not None,
        can_send_messages=can_send_messages is not None,
        can_manage_devices=can_manage_devices is not None,
        can_manage_branding=can_manage_branding is not None,
        can_manage_admin_users=can_manage_admin_users is not None,
    )

    try:
        create_admin_user(db, payload)
    except ValueError:
        pass

    return RedirectResponse(url="/webadmin/users", status_code=303)


@router.post("/users/{user_id}/save")
def users_save(
    request: Request,
    user_id: int,
    email: str = Form(...),
    password: str = Form(""),
    is_active: str | None = Form(default=None),
    can_login_admin_gui: str | None = Form(default=None),
    can_login_web_admin: str | None = Form(default=None),
    is_superadmin: str | None = Form(default=None),
    can_send_messages: str | None = Form(default=None),
    can_manage_devices: str | None = Form(default=None),
    can_manage_branding: str | None = Form(default=None),
    can_manage_admin_users: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    if not (user.is_superadmin or user.can_manage_admin_users):
        return RedirectResponse(url="/webadmin/users", status_code=303)

    payload = AdminUserUpdate(
        email=email.strip(),
        password=password.strip() or None,
        is_active=is_active is not None,
        can_login_admin_gui=can_login_admin_gui is not None,
        can_login_web_admin=can_login_web_admin is not None,
        is_superadmin=is_superadmin is not None,
        can_send_messages=can_send_messages is not None,
        can_manage_devices=can_manage_devices is not None,
        can_manage_branding=can_manage_branding is not None,
        can_manage_admin_users=can_manage_admin_users is not None,
    )
    update_admin_user(db, user_id, payload)
    return RedirectResponse(url="/webadmin/users", status_code=303)


@router.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    settings = get_settings(db)
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
        },
    )


@router.post("/settings/save")
def settings_save(
    request: Request,
    app_name: str = Form(""),
    company_name: str = Form(""),
    primary_color: str = Form("#2563eb"),
    secondary_color: str = Form("#1e293b"),
    web_admin_enabled: str | None = Form(default=None),
    app_icon_path: str = Form(""),
    login_logo_path: str = Form(""),
    app_icon_file: UploadFile | None = File(default=None),
    login_logo_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    if not (user.is_superadmin or user.can_manage_branding):
        return RedirectResponse(url="/webadmin/settings", status_code=303)

    uploaded_icon = save_upload(app_icon_file, "app_icon")
    uploaded_logo = save_upload(login_logo_file, "login_logo")

    payload = AppSettingUpdate(
        app_name=app_name.strip(),
        company_name=company_name.strip(),
        app_icon_path=uploaded_icon or app_icon_path.strip(),
        login_logo_path=uploaded_logo or login_logo_path.strip(),
        primary_color=primary_color.strip(),
        secondary_color=secondary_color.strip(),
        web_admin_enabled=web_admin_enabled is not None,
    )
    update_settings(db, payload)
    return RedirectResponse(url="/webadmin/settings", status_code=303)