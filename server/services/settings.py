from sqlalchemy import select
from sqlalchemy.orm import Session

from models import AppSetting
from schemas import AppSettingUpdate


def get_settings(db: Session) -> AppSetting:
    settings = db.execute(select(AppSetting)).scalar_one_or_none()

    if not settings:
        settings = AppSetting()
        db.add(settings)
        db.commit()
        db.refresh(settings)

    return settings


def update_settings(db: Session, payload: AppSettingUpdate) -> AppSetting:
    settings = get_settings(db)

    if payload.app_name is not None:
        settings.app_name = payload.app_name
    if payload.company_name is not None:
        settings.company_name = payload.company_name
    if payload.app_icon_path is not None:
        settings.app_icon_path = payload.app_icon_path
    if payload.login_logo_path is not None:
        settings.login_logo_path = payload.login_logo_path
    if payload.primary_color is not None:
        settings.primary_color = payload.primary_color
    if payload.secondary_color is not None:
        settings.secondary_color = payload.secondary_color
    if payload.web_admin_enabled is not None:
        settings.web_admin_enabled = payload.web_admin_enabled

    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings