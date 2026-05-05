from pydantic import EmailStr
from sqlmodel import SQLModel

from app.models.enums import StaffRole


class LoginRequest(SQLModel):
    email: str
    password: str


class LoginResponse(SQLModel):
    access_token: str
    token_type: str = "bearer"
    role: StaffRole
    branch_id: int | None


class MeResponse(SQLModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    role: StaffRole
    branch_id: int | None


class MeUpdateRequest(SQLModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
