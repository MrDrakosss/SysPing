from datetime import datetime
from pydantic import BaseModel


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
    sender_machine: str
    recipient_machine: str
    text: str
    is_important: bool = False


class ClientEvent(BaseModel):
    type: str
    message_id: int | None = None