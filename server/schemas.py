from datetime import datetime

from pydantic import BaseModel, EmailStr


class DeviceOut(BaseModel):
    id: int
    machine_name: str
    display_name: str
    owner: str
    note: str
    last_ip: str
    is_online: bool
    is_deleted: bool
    last_seen_at: datetime

    class Config:
        from_attributes = True


class DeviceUpdate(BaseModel):
    display_name: str | None = None
    owner: str | None = None
    note: str | None = None


class SendMessageIn(BaseModel):
    recipient_machine: str
    text: str
    is_important: bool = False
    sender_display_name: str | None = None


class BulkSendMessageIn(BaseModel):
    recipient_machines: list[str]
    text: str
    is_important: bool = False
    sender_display_name: str | None = None


class LoginIn(BaseModel):
    username: str
    password: str


class AdminUserCreate(BaseModel):
    username: str
    display_name: str = ""
    email: EmailStr
    password: str
    is_active: bool = True
    can_login_admin_gui: bool = True
    can_login_web_admin: bool = False
    is_superadmin: bool = False
    can_send_messages: bool = True
    can_manage_devices: bool = False
    can_manage_branding: bool = False
    can_manage_admin_users: bool = False


class AdminUserUpdate(BaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    is_active: bool | None = None
    can_login_admin_gui: bool | None = None
    can_login_web_admin: bool | None = None
    is_superadmin: bool | None = None
    can_send_messages: bool | None = None
    can_manage_devices: bool | None = None
    can_manage_branding: bool | None = None
    can_manage_admin_users: bool | None = None


class AdminSelfUpdate(BaseModel):
    display_name: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class AdminUserOut(BaseModel):
    id: int
    username: str
    display_name: str
    email: EmailStr
    is_active: bool
    can_login_admin_gui: bool
    can_login_web_admin: bool
    is_superadmin: bool
    can_send_messages: bool
    can_manage_devices: bool
    can_manage_branding: bool
    can_manage_admin_users: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AppSettingOut(BaseModel):
    id: int
    app_name: str
    company_name: str
    app_icon_path: str
    login_logo_path: str
    primary_color: str
    secondary_color: str
    web_admin_enabled: bool

    class Config:
        from_attributes = True


class AppSettingUpdate(BaseModel):
    app_name: str | None = None
    company_name: str | None = None
    app_icon_path: str | None = None
    login_logo_path: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    web_admin_enabled: bool | None = None


class MessageOut(BaseModel):
    id: int
    sender_machine: str
    sender_admin_user_id: int | None
    sender_display_name: str
    recipient_machine: str
    text: str
    is_important: bool
    status: str
    created_at: datetime
    delivered_at: datetime | None
    read_at: datetime | None

    class Config:
        from_attributes = True


class DashboardStatsOut(BaseModel):
    total_devices: int
    online_devices: int
    offline_devices: int
    queued_messages: int
    total_messages: int
    avg_read_seconds: float