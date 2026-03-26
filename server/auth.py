import hashlib
import secrets

from fastapi import Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AdminUser

ACTIVE_TOKENS: dict[str, int] = {}


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def authenticate_user(db: Session, username: str, password: str) -> AdminUser | None:
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


def create_access_token_for_user(user: AdminUser) -> str:
    token = secrets.token_urlsafe(32)
    ACTIVE_TOKENS[token] = user.id
    return token


def revoke_token(token: str) -> None:
    ACTIVE_TOKENS.pop(token, None)


def get_user_by_token(db: Session, token: str) -> AdminUser | None:
    user_id = ACTIVE_TOKENS.get(token)
    if not user_id:
        return None

    user = db.get(AdminUser, user_id)
    if not user or not user.is_active:
        return None

    return user


def require_token_header(authorization: str | None = Header(default=None)) -> str:
    if not authorization:
        raise HTTPException(status_code=401, detail="Hiányzó Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Érvénytelen Authorization header")

    return authorization.removeprefix("Bearer ").strip()


def require_admin_user(db: Session, token: str) -> AdminUser:
    user = get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="Érvénytelen vagy lejárt token")
    return user


def require_manage_devices(user: AdminUser) -> None:
    if not (user.is_superadmin or user.can_manage_devices):
        raise HTTPException(status_code=403, detail="Nincs eszközkezelési jogosultság")


def require_manage_branding(user: AdminUser) -> None:
    if not (user.is_superadmin or user.can_manage_branding):
        raise HTTPException(status_code=403, detail="Nincs branding kezelési jogosultság")


def require_manage_admin_users(user: AdminUser) -> None:
    if not (user.is_superadmin or user.can_manage_admin_users):
        raise HTTPException(status_code=403, detail="Nincs admin user kezelési jogosultság")