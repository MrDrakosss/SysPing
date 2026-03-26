from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from db import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    machine_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    owner: Mapped[str] = mapped_column(String(120), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    last_ip: Mapped[str] = mapped_column(String(64), default="")
    is_online: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    sender_machine: Mapped[str] = mapped_column(String(120), index=True)
    sender_admin_user_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    sender_display_name: Mapped[str] = mapped_column(String(120), default="")

    recipient_machine: Mapped[str] = mapped_column(String(120), index=True)

    text: Mapped[str] = mapped_column(Text)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")  # queued, delivered, read

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    app_name: Mapped[str] = mapped_column(String(120), default="SysPing")
    company_name: Mapped[str] = mapped_column(String(120), default="")
    app_icon_path: Mapped[str] = mapped_column(String(255), default="")
    login_logo_path: Mapped[str] = mapped_column(String(255), default="")
    primary_color: Mapped[str] = mapped_column(String(20), default="#2563eb")
    secondary_color: Mapped[str] = mapped_column(String(20), default="#1e293b")
    web_admin_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(120), default="")
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    can_login_admin_gui: Mapped[bool] = mapped_column(Boolean, default=True)
    can_login_web_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False)

    can_send_messages: Mapped[bool] = mapped_column(Boolean, default=True)
    can_manage_devices: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_branding: Mapped[bool] = mapped_column(Boolean, default=False)
    can_manage_admin_users: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )