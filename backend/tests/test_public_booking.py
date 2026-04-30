from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import select

from app.core.security import hash_password
from app.models.appointment import Appointment
from app.models.branch import Branch
from app.models.enums import AppointmentStatus, StaffRole
from app.models.master_procedure import MasterProcedure
from app.models.procedure import Procedure
from app.models.staff import Staff


def seed_min(db):
    branch = Branch(name="B1", open_time=time(9, 0), close_time=time(20, 0))
    db.add(branch)
    db.flush()
    master = Staff(
        full_name="M1",
        email="m1@example.com",
        role=StaffRole.master,
        branch_id=branch.id,
        password_hash=hash_password("x"),
        is_active=True,
    )
    db.add(master)
    db.flush()
    proc = Procedure(name="P1", duration_minutes=60, price=Decimal("10.00"), is_active=True)
    db.add(proc)
    db.flush()
    db.add(MasterProcedure(master_id=master.id, procedure_id=proc.id))
    db.commit()
    return branch, master, proc


def test_booking_conflict_returns_409(client, db_session):
    branch, master, proc = seed_min(db_session)

    start = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
    client.post(
        "/api/appointments",
        json={
            "branch_id": branch.id,
            "master_id": master.id,
            "procedure_id": proc.id,
            "client_name": "A",
            "client_phone": "1",
            "start_time": start.isoformat(),
        },
    ).raise_for_status()

    r2 = client.post(
        "/api/appointments",
        json={
            "branch_id": branch.id,
            "master_id": master.id,
            "procedure_id": proc.id,
            "client_name": "B",
            "client_phone": "2",
            "start_time": start.isoformat(),
        },
    )
    assert r2.status_code == 409


def test_revenue_sums_completed_only(client, db_session):
    branch, master, proc = seed_min(db_session)
    day = date(2030, 1, 1)

    a1 = Appointment(
        branch_id=branch.id,
        master_id=master.id,
        procedure_id=proc.id,
        client_name="A",
        client_phone="1",
        start_time=datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2030, 1, 1, 11, 0, tzinfo=timezone.utc),
        price=Decimal("10.00"),
        status=AppointmentStatus.completed,
    )
    a2 = Appointment(
        branch_id=branch.id,
        master_id=master.id,
        procedure_id=proc.id,
        client_name="B",
        client_phone="2",
        start_time=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
        end_time=datetime(2030, 1, 1, 13, 0, tzinfo=timezone.utc),
        price=Decimal("10.00"),
        status=AppointmentStatus.canceled,
    )
    db_session.add_all([a1, a2])
    db_session.commit()

    manager = Staff(
        full_name="Mgr",
        email="mgr@example.com",
        role=StaffRole.manager,
        branch_id=branch.id,
        password_hash=hash_password("manager123"),
        is_active=True,
    )
    db_session.add(manager)
    db_session.commit()

    # login to get token
    token = client.post("/api/auth/login", json={"email": manager.email, "password": "manager123"}).json()[
        "access_token"
    ]
    r = client.get(
        f"/api/manager/revenue?from={day.isoformat()}&to={day.isoformat()}",
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()
    assert r.json()["total"] == "10.00"


def test_manager_approves_reschedule_updates_appointment(client, db_session):
    branch, master, proc = seed_min(db_session)
    manager = Staff(
        full_name="Mgr",
        email="mgr2@example.com",
        role=StaffRole.manager,
        branch_id=branch.id,
        password_hash=hash_password("manager123"),
        is_active=True,
    )
    db_session.add(manager)
    db_session.flush()

    appt = Appointment(
        branch_id=branch.id,
        master_id=master.id,
        procedure_id=proc.id,
        client_name="A",
        client_phone="1",
        start_time=datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2030, 1, 1, 11, 0, tzinfo=timezone.utc),
        price=Decimal("10.00"),
        status=AppointmentStatus.scheduled,
    )
    db_session.add(appt)
    db_session.commit()

    # master requests reschedule (direct insert)
    from app.models.reschedule_request import RescheduleRequest
    from app.models.enums import RescheduleRequestStatus

    req = RescheduleRequest(
        appointment_id=appt.id,
        master_id=master.id,
        proposed_start_time=datetime(2030, 1, 1, 14, 0, tzinfo=timezone.utc),
        status=RescheduleRequestStatus.pending,
    )
    db_session.add(req)
    db_session.commit()

    token = client.post("/api/auth/login", json={"email": manager.email, "password": "manager123"}).json()[
        "access_token"
    ]
    r = client.patch(
        f"/api/manager/reschedule-requests/{req.id}",
        json={"status": "approved"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()

    updated = db_session.scalar(select(Appointment).where(Appointment.id == appt.id))
    assert updated is not None
    assert updated.start_time.hour == 14

