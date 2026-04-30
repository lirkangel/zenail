from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_staff
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.models.staff import Staff
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    staff = db.scalar(select(Staff).where(Staff.email == payload.email.lower()))
    if not staff or not verify_password(payload.password, staff.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not staff.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    token = create_access_token(subject=str(staff.id), role=staff.role.value, branch_id=staff.branch_id)
    return LoginResponse(access_token=token, role=staff.role, branch_id=staff.branch_id)


@router.get("/me", response_model=MeResponse)
def me(staff: Staff = Depends(get_current_staff)) -> MeResponse:
    return MeResponse(
        id=staff.id,
        full_name=staff.full_name,
        email=staff.email,
        role=staff.role,
        branch_id=staff.branch_id,
    )

