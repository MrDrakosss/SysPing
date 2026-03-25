from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from db import get_db
from services.settings import get_settings

router = APIRouter(prefix="/webadmin", tags=["webadmin"])
templates = Jinja2Templates(directory="webadmin/templates")


@router.get("/", response_class=HTMLResponse)
def webadmin_index(request: Request, db: Session = Depends(get_db)):
    settings = get_settings(db)
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "settings": settings,
        },
    )