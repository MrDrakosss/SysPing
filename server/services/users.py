from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from auth import hash_password
from models import AdminUser
from schemas import AdminSelfUpdate, AdminUserCreate, AdminUserUpdate


def list_admin_users(db: Session) -> list[AdminUser]:
    return db.execute(
        select(AdminUser).order_by(AdminUser.username.asc())
    ).scalars().all()


def create_admin_user(db: Session, payload: AdminUserCreate) -> AdminUser:
    existing = db.execute(
        select(AdminUser).where(
            or_(
                AdminUser.username == payload.username,
                AdminUser.email == payload.email,
            )
        )
    ).scalar_one_or_none()

    if existing:
        raise ValueError("A felhasználónév vagy email már létezik")

    user = AdminUser(
        username=payload.username.strip(),
        display_name=(payload.display_name or payload.username).strip(),
        email=str(payload.email).strip(),
        password_hash=hash_password(payload.password),
        is_active=payload.is_active,
        can_login_admin_gui=payload.can_login_admin_gui,
        can_login_web_admin=payload.can_login_web_admin,
        is_superadmin=payload.is_superadmin,
        can_send_messages=payload.can_send_messages,
        can_manage_devices=payload.can_manage_devices,
        can_manage_branding=payload.can_manage_branding,
        can_manage_admin_users=payload.can_manage_admin_users,
    )

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_admin_user(db: Session, user_id: int, payload: AdminUserUpdate) -> AdminUser | None:
    user = db.get(AdminUser, user_id)
    if not user:
        return None

    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.email is not None:
        user.email = str(payload.email).strip()
    if payload.password is not None:
        user.password_hash = hash_password(payload.password)
    if payload.is_active is not None:
        user.is_active = payload.is_active
    if payload.can_login_admin_gui is not None:
        user.can_login_admin_gui = payload.can_login_admin_gui
    if payload.can_login_web_admin is not None:
        user.can_login_web_admin = payload.can_login_web_admin
    if payload.is_superadmin is not None:
        user.is_superadmin = payload.is_superadmin
    if payload.can_send_messages is not None:
        user.can_send_messages = payload.can_send_messages
    if payload.can_manage_devices is not None:
        user.can_manage_devices = payload.can_manage_devices
    if payload.can_manage_branding is not None:
        user.can_manage_branding = payload.can_manage_branding
    if payload.can_manage_admin_users is not None:
        user.can_manage_admin_users = payload.can_manage_admin_users

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_self_user(db: Session, user_id: int, payload: AdminSelfUpdate) -> AdminUser | None:
    user = db.get(AdminUser, user_id)
    if not user:
        return None

    if payload.display_name is not None:
        user.display_name = payload.display_name.strip()
    if payload.email is not None:
        user.email = str(payload.email).strip()
    if payload.password is not None and payload.password.strip():
        user.password_hash = hash_password(payload.password)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user