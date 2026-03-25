from pathlib import Path
import getpass
import os
import textwrap

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db import Base
from models import AppSetting
from schemas import AdminUserCreate
from services.users import create_admin_user


def ask(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def ask_bool(label: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    value = input(label + suffix).strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "i", "igen"}


def build_database_url(host: str, port: str, db_name: str, user: str, password: str) -> str:
    return f"mysql+pymysql://{user}:{password}@{host}:{port}/{db_name}?charset=utf8mb4"


def write_env(server_dir: Path, database_url: str, host: str, port: str):
    env_content = textwrap.dedent(f"""\
    DATABASE_URL={database_url}
    SERVER_HOST={host}
    SERVER_PORT={port}
    """)
    (server_dir / ".env").write_text(env_content, encoding="utf-8")


def write_systemd_service(project_root: Path, service_user: str, server_port: str):
    content = textwrap.dedent(f"""\
    [Unit]
    Description=SysPing Server
    After=network.target mysql.service mariadb.service
    Wants=network.target

    [Service]
    Type=simple
    User={service_user}
    WorkingDirectory={project_root / "server"}
    Environment="PATH={project_root / ".venv" / "bin"}"
    ExecStart={project_root / ".venv" / "bin" / "uvicorn"} main:app --host 0.0.0.0 --port {server_port}
    Restart=always
    RestartSec=5

    [Install]
    WantedBy=multi-user.target
    """)
    (project_root / "central-messenger.service").write_text(content, encoding="utf-8")


def main():
    project_root = Path(__file__).resolve().parent.parent
    server_dir = Path(__file__).resolve().parent
    uploads_dir = server_dir / "webadmin" / "static" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("SysPing telepítő")
    print("=" * 60)

    db_host = ask("MySQL host", "127.0.0.1")
    db_port = ask("MySQL port", "3306")
    db_name = ask("MySQL adatbázis neve", "messenger_db")
    db_user = ask("MySQL felhasználó", "messenger_user")
    db_password = getpass.getpass("MySQL jelszó: ").strip()

    server_host = ask("Szerver host", "0.0.0.0")
    server_port = ask("Szerver port", "8080")

    app_name = ask("Program neve", "SysPing")
    company_name = ask("Cég neve", "")
    web_admin_enabled = ask_bool("Web admin engedélyezése?", True)

    database_url = build_database_url(db_host, db_port, db_name, db_user, db_password)
    write_env(server_dir, database_url, server_host, server_port)

    print("\nAdatbázis kapcsolat tesztelése és táblák létrehozása...")

    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    db = SessionLocal()
    try:
        settings = db.query(AppSetting).first()
        if not settings:
            settings = AppSetting()

        settings.app_name = app_name
        settings.company_name = company_name
        settings.web_admin_enabled = web_admin_enabled
        db.add(settings)
        db.commit()

        if ask_bool("Első superadmin létrehozása?", True):
            username = ask("Admin felhasználónév", "admin")
            email = ask("Admin email", "admin@example.local")
            password = getpass.getpass("Admin jelszó: ").strip()

            payload = AdminUserCreate(
                username=username,
                email=email,
                password=password,
                is_active=True,
                can_login_admin_gui=True,
                can_login_web_admin=web_admin_enabled,
                is_superadmin=True,
                can_send_messages=True,
                can_manage_devices=True,
                can_manage_branding=True,
                can_manage_admin_users=True,
            )

            try:
                create_admin_user(db, payload)
                print("Első admin létrehozva.")
            except ValueError as e:
                print(f"Admin létrehozás kihagyva: {e}")

    finally:
        db.close()

    if ask_bool("Generáljunk systemd service fájlt?", True):
        service_user = ask("Linux felhasználó a service-hez", os.getenv("USER", "root"))
        write_systemd_service(project_root, service_user, server_port)
        print(f"Service fájl elkészült: {project_root / 'central-messenger.service'}")

    print("\nTelepítés kész.")
    print(f".env fájl: {server_dir / '.env'}")
    print(f"Uploads mappa: {uploads_dir}")


if __name__ == "__main__":
    main()