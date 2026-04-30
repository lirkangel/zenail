from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import StaffRole
from app.models.staff import Staff


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_staff(db: Session = Depends(get_db), token: str = Depends(oauth2_scheme)) -> Staff:
    try:
        payload = decode_token(token)
        staff_id = int(payload.get("sub"))
    except (JWTError, TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    staff = db.scalar(select(Staff).where(Staff.id == staff_id))
    if not staff or not staff.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    return staff


def require_roles(*allowed: StaffRole) -> Callable[[Staff], Staff]:
    def _dep(staff: Staff = Depends(get_current_staff)) -> Staff:
        if staff.role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return staff

    return _dep


require_master = require_roles(StaffRole.master, StaffRole.admin)
require_manager = require_roles(StaffRole.manager, StaffRole.admin)
require_admin = require_roles(StaffRole.admin)

