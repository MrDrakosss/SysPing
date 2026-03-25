from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from schemas import AppSettingOut
from services.settings import get_settings

router = APIRouter(prefix="/public", tags=["public"])


@router.get("/branding", response_model=AppSettingOut)
def public_branding(db: Session = Depends(get_db)):
    return get_settings(db)