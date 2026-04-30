from pydantic import BaseModel

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
    role: StaffRole
    branch_id: int | None

