from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from db import Base, engine
from api.auth_routes import router as auth_router
from api.admin_routes import router as admin_router, configure_online_clients
from api.public_routes import router as public_router
from api.client_routes import router as client_router, get_online_clients
from webadmin.routes import router as webadmin_router

BASE_DIR = Path(__file__).resolve().parent

Base.metadata.create_all(bind=engine)

app = FastAPI(title="SysPing Server")

app.mount(
    "/webadmin/static",
    StaticFiles(directory=str(BASE_DIR / "webadmin" / "static")),
    name="webadmin_static",
)

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(public_router)
app.include_router(client_router)
app.include_router(webadmin_router)

configure_online_clients(get_online_clients())


@app.get("/")
def root():
    return {
        "name": "SysPing Server",
        "status": "ok",
    }