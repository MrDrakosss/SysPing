from pathlib import Path
import getpass

from db import Base, SessionLocal, engine
from models import AppSetting
from schemas import AdminUserCreate
from services.settings import get_settings
from services.users import create_admin_user


def ask_bool(label: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    value = input(label + suffix).strip().lower()

    if not value:
        return default

    return value in {"y", "yes", "i", "igen"}


def main():
    print("=" * 60)
    print("SysPing telepítő")
    print("=" * 60)

    print("\nAdatbázis táblák létrehozása...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        settings = get_settings(db)

        print("\nAlap branding beállítások")
        app_name = input(f"Program neve [{settings.app_name}]: ").strip() or settings.app_name
        company_name = input(f"Cég neve [{settings.company_name}]: ").strip() or settings.company_name
        web_admin_enabled = ask_bool(
            f"Web admin engedélyezése? (jelenleg: {'igen' if settings.web_admin_enabled else 'nem'})",
            settings.web_admin_enabled,
        )

        settings.app_name = app_name
        settings.company_name = company_name
        settings.web_admin_enabled = web_admin_enabled
        db.add(settings)
        db.commit()

        create_first_admin = ask_bool("\nLétrehozzuk az első admin felhasználót?", True)

        if create_first_admin:
            username = input("Admin felhasználónév: ").strip()
            email = input("Admin email: ").strip()
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
                print("Admin felhasználó létrehozva.")
            except ValueError as e:
                print(f"Admin user létrehozás kihagyva: {e}")

        uploads_dir = Path("webadmin/static/uploads")
        uploads_dir.mkdir(parents=True, exist_ok=True)

        print("\nTelepítés kész.")
        print(f"Program neve: {app_name}")
        print(f"Cég neve: {company_name}")
        print(f"Web admin: {'engedélyezve' if web_admin_enabled else 'kikapcsolva'}")
        print(f"Uploads könyvtár: {uploads_dir.resolve()}")

    finally:
        db.close()


if __name__ == "__main__":
    main()