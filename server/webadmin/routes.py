import secrets
import shutil
from pathlib import Path
from typing import Dict

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from auth import authenticate_user
from db import get_db
from models import AdminUser, Device
from schemas import AdminSelfUpdate, AdminUserCreate, AdminUserUpdate, AppSettingUpdate, DeviceUpdate
from services.devices import list_devices, restore_device, soft_delete_device, update_device
from services.messages import get_dashboard_message_stats, list_all_messages, list_messages_for_admin
from services.settings import get_settings, update_settings
from services.users import create_admin_user, list_admin_users, update_admin_user, update_self_user
from api.client_routes import get_online_clients
from services.messages import create_message, create_bulk_messages

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(prefix="/webadmin", tags=["webadmin"])

WEB_SESSIONS: Dict[str, int] = {}
UPLOADS_DIR = BASE_DIR / "static" / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

SENDER_OPTIONS = [
    "Rendszergazda",
    "Rendszergazda csoport",
    "IT üzemeltetés",
    "Helpdesk",
]


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
        raise PermissionError
    return user


def redirect_to_login():
    return RedirectResponse(url="/webadmin/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def webadmin_login_page(request: Request, db: Session = Depends(get_db)):
    settings = get_settings(db)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "settings": settings, "error": None},
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
            request,
            "login.html",
            {
                "request": request,
                "settings": settings,
                "error": "Hibás belépési adatok vagy nincs web admin jogosultság.",
            },
        )

    session_token = secrets.token_urlsafe(32)
    WEB_SESSIONS[session_token] = user.id

    response = RedirectResponse(url="/webadmin/", status_code=303)
    response.set_cookie("webadmin_session", session_token, httponly=True, samesite="lax")
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

    msg_stats = get_dashboard_message_stats(db)
    recent_devices = db.execute(
        select(Device)
        .where(Device.is_deleted == False)  # noqa
        .order_by(Device.last_seen_at.desc())
        .limit(8)
    ).scalars().all()

    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
            "stats": {
                "total_devices": total_devices,
                "online_devices": online_devices,
                "offline_devices": total_devices - online_devices,
                "queued_messages": msg_stats["queued_messages"],
                "total_messages": msg_stats["total_messages"],
                "avg_read_seconds": msg_stats["avg_read_seconds"],
            },
            "recent_devices": recent_devices,
        },
    )


@router.get("/messages", response_class=HTMLResponse)
def messages_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    settings = get_settings(db)
    devices = list_devices(db, include_deleted=False)
    my_messages = list_messages_for_admin(db, user.id)

    return templates.TemplateResponse(
        request,
        "messages.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
            "devices": devices,
            "messages": my_messages,
            "sender_options": SENDER_OPTIONS,
        },
    )


@router.post("/messages/send")
async def messages_send(
    request: Request,
    recipient_machine: str = Form(...),
    text: str = Form(...),
    sender_display_name: str = Form(""),
    is_important: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    sender_name = sender_display_name.strip() or user.display_name or user.username

    await create_message(
        db=db,
        sender_machine=user.username,
        sender_admin_user_id=user.id,
        sender_display_name=sender_name,
        recipient_machine=recipient_machine,
        text=text,
        is_important=is_important is not None,
        online_clients=get_online_clients(),
    )
    return RedirectResponse(url="/webadmin/messages", status_code=303)


@router.post("/messages/send-bulk")
async def messages_send_bulk(
    request: Request,
    recipient_machines: list[str] = Form(...),
    text: str = Form(...),
    sender_display_name: str = Form(""),
    is_important: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    sender_name = sender_display_name.strip() or user.display_name or user.username

    await create_bulk_messages(
        db=db,
        sender_machine=user.username,
        sender_admin_user_id=user.id,
        sender_display_name=sender_name,
        recipient_machines=recipient_machines,
        text=text,
        is_important=is_important is not None,
        online_clients=get_online_clients(),
    )
    return RedirectResponse(url="/webadmin/messages", status_code=303)


@router.get("/message-log", response_class=HTMLResponse)
def message_log_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    if not user.is_superadmin:
        return RedirectResponse(url="/webadmin/", status_code=303)

    settings = get_settings(db)
    messages = list_all_messages(db)

    return templates.TemplateResponse(
        request,
        "message_log.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
            "messages": messages,
        },
    )


@router.get("/account", response_class=HTMLResponse)
def account_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    settings = get_settings(db)
    return templates.TemplateResponse(
        request,
        "account.html",
        {
            "request": request,
            "settings": settings,
            "current_user": user,
        },
    )


@router.post("/account/save")
def account_save(
    request: Request,
    display_name: str = Form(""),
    email: str = Form(""),
    password: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = require_web_user(request, db)
    except PermissionError:
        return redirect_to_login()

    update_self_user(
        db,
        user.id,
        AdminSelfUpdate(
            display_name=display_name.strip(),
            email=email.strip(),
            password=password.strip() or None,
        ),
    )
    return RedirectResponse(url="/webadmin/account", status_code=303)

# a devices/users/settings route-ok maradhatnak az előző verzióból,
# azokban csak a template context maradjon current_user + settings