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
    proc = Procedure(
        name="P1",
        duration_minutes=60,
        price=Decimal("10.00"),
        description="Classic nail care",
        category="Hands",
        is_active=True,
    )
    proc2 = Procedure(
        name="P2",
        duration_minutes=30,
        price=Decimal("5.00"),
        description="Nail art detail",
        category="Add-ons",
        is_active=True,
    )
    db.add_all([proc, proc2])
    db.flush()
    db.add(MasterProcedure(master_id=master.id, procedure_id=proc.id))
    db.add(MasterProcedure(master_id=master.id, procedure_id=proc2.id))
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


def test_multi_procedure_booking_sums_duration_and_price_and_can_be_looked_up(client, db_session):
    branch, master, proc = seed_min(db_session)
    proc2 = db_session.scalar(select(Procedure).where(Procedure.name == "P2"))

    start = datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc)
    r = client.post(
        "/api/appointments",
        json={
            "branch_id": branch.id,
            "master_id": master.id,
            "procedure_ids": [proc.id, proc2.id],
            "client_name": "A",
            "client_phone": "555",
            "start_time": start.isoformat(),
        },
    )
    r.raise_for_status()
    data = r.json()
    assert data["price"] == "15.00"
    assert data["end_time"].startswith("2030-01-01T11:30:00")
    assert [p["id"] for p in data["procedures"]] == [proc.id, proc2.id]

    lookup = client.get(f"/api/appointments/{data['id']}?client_phone=555")
    lookup.raise_for_status()
    assert lookup.json()["status"] == "scheduled"


def test_public_booking_rejects_past_dates(client, db_session):
    branch, master, proc = seed_min(db_session)

    r = client.get(f"/api/availability?master_id={master.id}&procedure_ids={proc.id}&date=2000-01-01")
    assert r.status_code == 422

    r = client.post(
        "/api/appointments",
        json={
            "branch_id": branch.id,
            "master_id": master.id,
            "procedure_ids": [proc.id],
            "client_name": "A",
            "client_phone": "555",
            "start_time": datetime(2000, 1, 1, 10, 0, tzinfo=timezone.utc).isoformat(),
        },
    )
    assert r.status_code == 422


def test_branch_non_working_day_blocks_availability(client, db_session):
    branch, master, proc = seed_min(db_session)
    admin = Staff(
        full_name="Admin",
        email="admin@example.com",
        role=StaffRole.admin,
        branch_id=None,
        password_hash=hash_password("admin123"),
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    token = client.post("/api/auth/login", json={"email": admin.email, "password": "admin123"}).json()[
        "access_token"
    ]
    day = "2030-01-02"

    r = client.post(
        f"/api/admin/branches/{branch.id}/non-working-days",
        json={"day": day, "reason": "Holiday"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r.raise_for_status()

    r = client.get(f"/api/availability?master_id={master.id}&procedure_ids={proc.id}&date={day}")
    r.raise_for_status()
    assert r.json()["slots"] == []


def test_seed_style_local_demo_email_can_login_and_load_me(client, db_session):
    staff = Staff(
        full_name="Demo Admin",
        email="admin@zenail.local",
        role=StaffRole.admin,
        branch_id=None,
        password_hash=hash_password("admin123"),
        is_active=True,
    )
    db_session.add(staff)
    db_session.commit()

    r = client.post("/api/auth/login", json={"email": staff.email, "password": "admin123"})
    r.raise_for_status()
    token = r.json()["access_token"]

    me = client.get("/api/me", headers={"Authorization": f"Bearer {token}"})
    me.raise_for_status()
    assert me.json()["email"] == "admin@zenail.local"


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

