from pydantic import BaseModel


class PCRegisterRequest(BaseModel):
    lab_name: str
    pc_number: str
    device_id: str
    hostname: str
    agent_version: str = "1.0.0"


class HeartbeatRequest(BaseModel):
    device_id: str


class UserCreateRequest(BaseModel):
    telegram_id: str
    name: str
    username: str | None = None
    role: str = "FACULTY"
    assigned_lab: str | None = None