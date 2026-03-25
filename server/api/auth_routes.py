from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import (
    TOKENS,
    authenticate_user,
    create_token,
    require_admin_gui_login,
    require_admin_user,
    require_token_header,
)
from db import get_db
from schemas import LoginIn

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.username.strip(), payload.password)

    if not user:
        raise HTTPException(status_code=401, detail="Hibás felhasználónév vagy jelszó")

    require_admin_gui_login(user)
    token = create_token(user.id)

    return {
        "token": token,
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "is_active": user.is_active,
            "is_superadmin": user.is_superadmin,
            "can_login_admin_gui": user.can_login_admin_gui,
            "can_login_web_admin": user.can_login_web_admin,
            "can_send_messages": user.can_send_messages,
            "can_manage_devices": user.can_manage_devices,
            "can_manage_branding": user.can_manage_branding,
            "can_manage_admin_users": user.can_manage_admin_users,
        },
    }


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
        "is_superadmin": user.is_superadmin,
        "can_login_admin_gui": user.can_login_admin_gui,
        "can_login_web_admin": user.can_login_web_admin,
        "can_send_messages": user.can_send_messages,
        "can_manage_devices": user.can_manage_devices,
        "can_manage_branding": user.can_manage_branding,
        "can_manage_admin_users": user.can_manage_admin_users,
    }


@router.post("/logout")
def logout(
    token: str = Depends(require_token_header),
    db: Session = Depends(get_db),
):
    user = require_admin_user(db, token)
    TOKENS.pop(token, None)
    return {
        "ok": True,
        "message": f"Sikeres kijelentkezés: {user.username}",
    }