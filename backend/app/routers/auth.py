from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.api.deps import get_current_staff
from app.core.security import create_access_token, hash_password, verify_password
from app.db.sqlmodel import get_db
from app.models.staff import Staff
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse, MeUpdateRequest

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
        phone=staff.phone,
        role=staff.role,
        branch_id=staff.branch_id,
    )


@router.patch("/me", response_model=MeResponse)
def update_me(
    payload: MeUpdateRequest,
    db: Session = Depends(get_db),
    staff: Staff = Depends(get_current_staff),
) -> MeResponse:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).lower()
        existing = db.scalar(select(Staff).where(Staff.email == data["email"], Staff.id != staff.id))
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already in use")
    if "password" in data:
        if data["password"]:
            staff.password_hash = hash_password(data["password"])
        data.pop("password")
    for key, value in data.items():
        setattr(staff, key, value)
    db.commit()
    db.refresh(staff)
    return MeResponse(
        id=staff.id,
        full_name=staff.full_name,
        email=staff.email,
        phone=staff.phone,
        role=staff.role,
        branch_id=staff.branch_id,
    )
