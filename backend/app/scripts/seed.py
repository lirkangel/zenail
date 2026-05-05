from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.core.security import hash_password
from app.db.sqlmodel import engine
from app.models.appointment import Appointment
from app.models.appointment_procedure import AppointmentProcedure
from app.models.branch import Branch
from app.models.enums import AppointmentStatus, StaffRole
from app.models.master_procedure import MasterProcedure
from app.models.procedure import Procedure
from app.models.staff import Staff


def _ensure_branch(
    db,
    *,
    name: str,
    timezone: str,
    open_time: time,
    close_time: time,
    address: str,
) -> Branch:
    b = db.scalar(select(Branch).where(Branch.name == name))
    if b:
        b.timezone = timezone
        return b
    b = Branch(name=name, timezone=timezone, open_time=open_time, close_time=close_time, address=address)
    db.add(b)
    db.flush()
    return b


def _ensure_staff(
    db,
    *,
    email: str,
    full_name: str,
    role: StaffRole,
    branch_id: int | None,
    password: str,
) -> Staff:
    s = db.scalar(select(Staff).where(Staff.email == email))
    if s:
        return s
    s = Staff(
        email=email,
        full_name=full_name,
        role=role,
        branch_id=branch_id,
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(s)
    db.flush()
    return s


def _ensure_procedure(
    db,
    *,
    name: str,
    duration: int,
    price: Decimal,
    category: str,
    description: str,
) -> Procedure:
    p = db.scalar(select(Procedure).where(Procedure.name == name))
    if p:
        p.duration_minutes = duration
        p.price = price
        p.category = category
        p.description = description
        p.is_active = True
        return p
    p = Procedure(
        name=name,
        duration_minutes=duration,
        price=price,
        category=category,
        description=description,
        is_active=True,
    )
    db.add(p)
    db.flush()
    return p


def _link_master_proc(db, *, master_id: int, procedure_id: int) -> None:
    exists = db.scalar(
        select(MasterProcedure).where(
            MasterProcedure.master_id == master_id,
            MasterProcedure.procedure_id == procedure_id,
        )
    )
    if exists:
        return
    db.add(MasterProcedure(master_id=master_id, procedure_id=procedure_id))


def run() -> None:
    db = Session(engine)
    try:
        branch_a = _ensure_branch(
            db,
            name="Zenail Central",
            timezone="Asia/Ho_Chi_Minh",
            open_time=time(9, 0),
            close_time=time(20, 0),
            address="1 Main Street",
        )
        branch_b = _ensure_branch(
            db,
            name="Zenail Riverside",
            timezone="Asia/Ho_Chi_Minh",
            open_time=time(10, 0),
            close_time=time(21, 0),
            address="99 River Road",
        )

        _ensure_staff(
            db,
            email="admin@zenail.local",
            full_name="Admin",
            role=StaffRole.admin,
            branch_id=None,
            password="admin123",
        )
        _ensure_staff(
            db,
            email="manager.a@zenail.local",
            full_name="Manager Central",
            role=StaffRole.manager,
            branch_id=branch_a.id,
            password="manager123",
        )
        _ensure_staff(
            db,
            email="manager.b@zenail.local",
            full_name="Manager Riverside",
            role=StaffRole.manager,
            branch_id=branch_b.id,
            password="manager123",
        )

        masters_a = [
            _ensure_staff(
                db,
                email=f"master.a{i}@zenail.local",
                full_name=f"Master A{i}",
                role=StaffRole.master,
                branch_id=branch_a.id,
                password="master123",
            )
            for i in range(1, 4)
        ]
        masters_b = [
            _ensure_staff(
                db,
                email=f"master.b{i}@zenail.local",
                full_name=f"Master B{i}",
                role=StaffRole.master,
                branch_id=branch_b.id,
                password="master123",
            )
            for i in range(1, 4)
        ]

        procs = [
            _ensure_procedure(db, name="Manicure (Classic)", duration=60, price=Decimal("25.00"), category="Hands", description="Nail shaping, cuticle care, light buffing, and classic polish."),
            _ensure_procedure(db, name="Manicure (Gel)", duration=75, price=Decimal("35.00"), category="Hands", description="Long-lasting gel polish with cuticle care and nail shaping."),
            _ensure_procedure(db, name="Pedicure (Classic)", duration=75, price=Decimal("32.00"), category="Feet", description="Foot soak, nail care, heel smoothing, massage, and classic polish."),
            _ensure_procedure(db, name="Pedicure (Spa)", duration=90, price=Decimal("45.00"), category="Feet", description="Classic pedicure plus exfoliation, mask, and extended massage."),
            _ensure_procedure(db, name="Nail Art (Add-on)", duration=30, price=Decimal("15.00"), category="Add-ons", description="Simple hand-painted art, accent nails, stickers, or small details."),
            _ensure_procedure(db, name="Removal (Gel)", duration=30, price=Decimal("10.00"), category="Add-ons", description="Careful gel removal before a new service or nail rest."),
        ]

        for m in masters_a + masters_b:
            _link_master_proc(db, master_id=m.id, procedure_id=procs[0].id)
            _link_master_proc(db, master_id=m.id, procedure_id=procs[1].id)
            _link_master_proc(db, master_id=m.id, procedure_id=procs[2].id)
        for m in masters_a:
            _link_master_proc(db, master_id=m.id, procedure_id=procs[3].id)
        for m in masters_b:
            _link_master_proc(db, master_id=m.id, procedure_id=procs[4].id)
            _link_master_proc(db, master_id=m.id, procedure_id=procs[5].id)

        now = datetime.now(timezone.utc)
        today = now.date()
        start_base = datetime(today.year, today.month, today.day, 11, 0, tzinfo=timezone.utc)

        def ensure_appt(
            branch_id: int,
            master_id: int,
            procedure: Procedure,
            i: int,
            status: AppointmentStatus,
        ) -> None:
            start = start_base + timedelta(hours=i * 2)
            end = start + timedelta(minutes=procedure.duration_minutes)
            exists = db.scalar(
                select(Appointment).where(
                    Appointment.master_id == master_id,
                    Appointment.start_time == start,
                    Appointment.procedure_id == procedure.id,
                )
            )
            if exists:
                return
            appt = Appointment(
                branch_id=branch_id,
                master_id=master_id,
                procedure_id=procedure.id,
                client_name=f"Client {i}",
                client_phone=f"+100000000{i}",
                start_time=start,
                end_time=end,
                price=procedure.price,
                status=status,
            )
            db.add(appt)
            db.flush()
            db.add(
                AppointmentProcedure(
                    appointment_id=appt.id,
                    procedure_id=procedure.id,
                    sort_order=0,
                    name_snapshot=procedure.name,
                    duration_minutes_snapshot=procedure.duration_minutes,
                    price_snapshot=procedure.price,
                )
            )

        for i, m in enumerate(masters_a, start=1):
            ensure_appt(branch_a.id, m.id, procs[0], i, AppointmentStatus.scheduled)
            ensure_appt(branch_a.id, m.id, procs[2], i + 1, AppointmentStatus.completed)
        for i, m in enumerate(masters_b, start=1):
            ensure_appt(branch_b.id, m.id, procs[1], i, AppointmentStatus.scheduled)

        db.commit()
        print("Seed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
