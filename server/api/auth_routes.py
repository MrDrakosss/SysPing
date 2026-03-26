from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import (
    authenticate_user,
    create_access_token_for_user,
    require_admin_user,
    require_token_header,
    revoke_token,
)
from db import get_db
from schemas import LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username.strip(), payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Hibás felhasználónév vagy jelszó")

    token = create_access_token_for_user(user)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "can_login_admin_gui": user.can_login_admin_gui,
            "can_login_web_admin": user.can_login_web_admin,
            "is_superadmin": user.is_superadmin,
            "can_send_messages": user.can_send_messages,
            "can_manage_devices": user.can_manage_devices,
            "can_manage_branding": user.can_manage_branding,
            "can_manage_admin_users": user.can_manage_admin_users,
        },
    }


@router.post("/logout")
def logout(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    revoke_token(token)
    return {"ok": True, "username": user.username}


@router.get("/me")
def me(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_active": user.is_active,
        "can_login_admin_gui": user.can_login_admin_gui,
        "can_login_web_admin": user.can_login_web_admin,
        "is_superadmin": user.is_superadmin,
        "can_send_messages": user.can_send_messages,
        "can_manage_devices": user.can_manage_devices,
        "can_manage_branding": user.can_manage_branding,
        "can_manage_admin_users": user.can_manage_admin_users,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }