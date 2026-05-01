from pydantic import BaseModel, EmailStr

from app.models.enums import StaffRole


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: StaffRole
    branch_id: int | None


class MeResponse(BaseModel):
    id: int
    full_name: str
    email: str
    phone: str | None = None
    role: StaffRole
    branch_id: int | None


class MeUpdateRequest(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    password: str | None = None
