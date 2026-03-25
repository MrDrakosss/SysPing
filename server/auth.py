import hashlib
import hmac
import secrets
from typing import Dict, Optional

from fastapi import Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AdminUser

# egyszerű in-memory session token tároló
TOKENS: Dict[str, int] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    candidate = hash_password(password)
    return hmac.compare_digest(candidate, password_hash)


def create_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    TOKENS[token] = user_id
    return token


def get_user_by_token(db: Session, token: str) -> Optional[AdminUser]:
    user_id = TOKENS.get(token)
    if not user_id:
        return None
    return db.get(AdminUser, user_id)


def require_token_header(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Hiányzó Authorization header")

    if not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Hibás Authorization formátum")

    return authorization[7:].strip()


def require_admin_user(db: Session, token: str) -> AdminUser:
    user = get_user_by_token(db, token)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Érvénytelen vagy lejárt token")
    return user


def require_admin_gui_login(user: AdminUser) -> None:
    if not user.can_login_admin_gui:
        raise HTTPException(status_code=403, detail="Nincs GUI belépési jog")


def require_web_admin_login(user: AdminUser) -> None:
    if not user.can_login_web_admin:
        raise HTTPException(status_code=403, detail="Nincs web admin belépési jog")


def require_manage_devices(user: AdminUser) -> None:
    if not (user.is_superadmin or user.can_manage_devices):
        raise HTTPException(status_code=403, detail="Nincs eszközkezelési jog")


def require_manage_branding(user: AdminUser) -> None:
    if not (user.is_superadmin or user.can_manage_branding):
        raise HTTPException(status_code=403, detail="Nincs branding kezelési jog")


def require_manage_admin_users(user: AdminUser) -> None:
    if not (user.is_superadmin or user.can_manage_admin_users):
        raise HTTPException(status_code=403, detail="Nincs admin user kezelési jog")


def authenticate_user(db: Session, username: str, password: str) -> Optional[AdminUser]:
    user = db.execute(
        select(AdminUser).where(AdminUser.username == username)
    ).scalar_one_or_none()

    if not user:
        return None

    if not user.is_active:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user