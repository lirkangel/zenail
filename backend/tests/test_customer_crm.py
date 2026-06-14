from datetime import datetime, time, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.core.security import create_access_token, hash_password
from app.models import (
    Appointment,
    Branch,
    Customer,
    CustomerMergeLog,
    CustomerPreferenceDefinition,
    CustomerPreferenceValue,
    CustomerTag,
    CustomerTagDefinition,
    DefinitionScope,
    MasterProcedure,
    PreferenceValueType,
    Procedure,
    Staff,
)
from app.models.enums import AppointmentStatus, StaffRole


def _seed_booking_base(db: Session):
    branch = Branch(name="Central", timezone="UTC", open_time=time(8, 0), close_time=time(20, 0))
    db.add(branch)
    db.flush()
    master = Staff(
        full_name="Linh",
        email="linh@example.com",
        password_hash=hash_password("master123"),
        role=StaffRole.master,
        branch_id=branch.id,
        is_active=True,
    )
    db.add(master)
    db.flush()
    proc = Procedure(name="Manicure", duration_minutes=60, price=Decimal("100.00"), is_active=True)
    db.add(proc)
    db.flush()
    db.add(MasterProcedure(master_id=master.id, procedure_id=proc.id))
    db.commit()
    db.refresh(branch)
    db.refresh(master)
    db.refresh(proc)
    return branch, master, proc


def _book(client, *, branch, master, proc, name="An", phone="090 123 4567", email="an@example.com", hour=10):
    return client.post(
        "/api/appointments",
        json={
            "branch_id": branch.id,
            "master_id": master.id,
            "procedure_ids": [proc.id],
            "client_name": name,
            "client_phone": phone,
            "client_email": email,
            "start_time": datetime(2030, 1, 1, hour, 0, tzinfo=timezone.utc).isoformat(),
        },
    )


def _token_for(staff: Staff) -> str:
    return create_access_token(subject=str(staff.id), role=staff.role.value, branch_id=staff.branch_id)


def _seed_admin(db: Session) -> Staff:
    admin = Staff(
        full_name="Admin",
        email="admin@example.com",
        password_hash=hash_password("admin123"),
        role=StaffRole.admin,
        branch_id=None,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def _seed_manager(db: Session, branch_id: int) -> Staff:
    manager = Staff(
        full_name="Manager",
        email="manager@example.com",
        password_hash=hash_password("manager123"),
        role=StaffRole.manager,
        branch_id=branch_id,
        is_active=True,
    )
    db.add(manager)
    db.commit()
    db.refresh(manager)
    return manager


def test_public_booking_creates_customer_and_reuses_by_normalized_phone(client, db_session):
    branch, master, proc = _seed_booking_base(db_session)

    first = _book(client, branch=branch, master=master, proc=proc, phone="090 123 4567", hour=10)
    first.raise_for_status()
    second = _book(client, branch=branch, master=master, proc=proc, name="An Nguyen", phone="0901234567", hour=12)
    second.raise_for_status()

    customers = db_session.exec(select(Customer)).all()
    assert len(customers) == 1
    assert customers[0].phone_normalized == "0901234567"

    appointments = db_session.exec(select(Appointment).order_by(Appointment.start_time)).all()
    assert [a.customer_id for a in appointments] == [customers[0].id, customers[0].id]
    assert first.json()["customer_id"] == customers[0].id
    assert second.json()["customer_id"] == customers[0].id


def test_admin_customer_list_and_detail_include_history_and_spend(client, db_session):
    branch, master, proc = _seed_booking_base(db_session)
    customer = Customer(full_name="An", phone="0901234567", phone_normalized="0901234567", email="an@example.com")
    db_session.add(customer)
    db_session.flush()
    completed = Appointment(
        branch_id=branch.id,
        master_id=master.id,
        procedure_id=proc.id,
        customer_id=customer.id,
        client_name="An",
        client_phone="0901234567",
        client_email="an@example.com",
        start_time=datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2030, 1, 1, 11, 0, tzinfo=timezone.utc),
        price=Decimal("100.00"),
        status=AppointmentStatus.completed,
    )
    canceled = Appointment(
        branch_id=branch.id,
        master_id=master.id,
        procedure_id=proc.id,
        customer_id=customer.id,
        client_name="An",
        client_phone="0901234567",
        client_email="an@example.com",
        start_time=datetime(2030, 1, 2, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2030, 1, 2, 11, 0, tzinfo=timezone.utc),
        price=Decimal("100.00"),
        status=AppointmentStatus.canceled,
    )
    db_session.add_all([completed, canceled])
    admin = _seed_admin(db_session)

    token = _token_for(admin)
    list_res = client.get("/api/admin/customers?q=090", headers={"Authorization": f"Bearer {token}"})
    list_res.raise_for_status()
    rows = list_res.json()["items"]
    assert len(rows) == 1
    assert rows[0]["visit_count"] == 2
    assert rows[0]["completed_spend"] == "100.00"

    detail_res = client.get(f"/api/admin/customers/{customer.id}", headers={"Authorization": f"Bearer {token}"})
    detail_res.raise_for_status()
    detail = detail_res.json()
    assert detail["id"] == customer.id
    assert detail["completed_spend"] == "100.00"
    assert [a["status"] for a in detail["appointments"]] == ["canceled", "completed"]


def test_manager_customer_scope_and_notes_update(client, db_session):
    branch, master, proc = _seed_booking_base(db_session)
    other_branch = Branch(name="Riverside", timezone="UTC", open_time=time(8, 0), close_time=time(20, 0))
    db_session.add(other_branch)
    db_session.flush()
    visible = Customer(full_name="Visible", phone="1", phone_normalized="1")
    hidden = Customer(full_name="Hidden", phone="2", phone_normalized="2")
    db_session.add_all([visible, hidden])
    db_session.flush()
    db_session.add(
        Appointment(
            branch_id=branch.id,
            master_id=master.id,
            procedure_id=proc.id,
            customer_id=visible.id,
            client_name="Visible",
            client_phone="1",
            start_time=datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2030, 1, 1, 11, 0, tzinfo=timezone.utc),
            price=Decimal("100.00"),
        )
    )
    db_session.add(
        Appointment(
            branch_id=other_branch.id,
            master_id=master.id,
            procedure_id=proc.id,
            customer_id=hidden.id,
            client_name="Hidden",
            client_phone="2",
            start_time=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
            end_time=datetime(2030, 1, 1, 13, 0, tzinfo=timezone.utc),
            price=Decimal("100.00"),
        )
    )
    manager = _seed_manager(db_session, branch.id)

    token = _token_for(manager)
    list_res = client.get("/api/manager/customers", headers={"Authorization": f"Bearer {token}"})
    list_res.raise_for_status()
    assert [row["id"] for row in list_res.json()["items"]] == [visible.id]

    hidden_res = client.get(f"/api/manager/customers/{hidden.id}", headers={"Authorization": f"Bearer {token}"})
    assert hidden_res.status_code == 404

    patch_res = client.patch(
        f"/api/manager/customers/{visible.id}",
        json={"notes": "Prefers quiet morning slots"},
        headers={"Authorization": f"Bearer {token}"},
    )
    patch_res.raise_for_status()
    db_session.refresh(visible)
    assert visible.notes == "Prefers quiet morning slots"


def test_customer_crm_models_support_tag_and_preference_assignments(db_session: Session) -> None:
    branch, _, _ = _seed_booking_base(db_session)

    customer = Customer(full_name="Lan", phone="0901", phone_normalized="0901")
    tag_def = CustomerTagDefinition(
        name="VIP",
        slug="vip",
        scope=DefinitionScope.global_,
        branch_id=None,
        is_active=True,
        created_by_staff_id=1,
    )
    pref_def = CustomerPreferenceDefinition(
        name="Quiet",
        slug="quiet",
        scope=DefinitionScope.branch,
        branch_id=branch.id,
        value_type=PreferenceValueType.boolean,
        options_json=None,
        is_active=True,
        created_by_staff_id=1,
    )
    db_session.add_all([customer, tag_def, pref_def])
    db_session.commit()

    db_session.add(
        CustomerTag(
            customer_id=customer.id,
            tag_definition_id=tag_def.id,
            assigned_by_staff_id=1,
        )
    )
    db_session.add(
        CustomerPreferenceValue(
            customer_id=customer.id,
            preference_definition_id=pref_def.id,
            value_bool=True,
            updated_by_staff_id=1,
        )
    )
    db_session.commit()

    saved_customer = db_session.get(Customer, customer.id)
    assert saved_customer is not None
    assert saved_customer.is_active is True
    assert saved_customer.merged_into_customer_id is None

    saved_tag = db_session.get(CustomerTag, (customer.id, tag_def.id))
    saved_preference = db_session.get(CustomerPreferenceValue, (customer.id, pref_def.id))

    assert saved_tag is not None
    assert saved_preference is not None
    assert saved_preference.value_bool is True


def test_manager_cannot_edit_customer_phone(client, db_session):
    branch, master, proc = _seed_booking_base(db_session)
    customer = Customer(full_name="Visible", phone="0901", phone_normalized="0901")
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        Appointment(
            branch_id=branch.id,
            master_id=master.id,
            procedure_id=proc.id,
            customer_id=customer.id,
            client_name="Visible",
            client_phone="0901",
            start_time=datetime(2030, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2030, 1, 1, 11, 0, tzinfo=timezone.utc),
            price=Decimal("100.00"),
        )
    )
    manager = _seed_manager(db_session, branch.id)

    res = client.patch(
        f"/api/manager/customers/{customer.id}",
        headers={"Authorization": f"Bearer {_token_for(manager)}"},
        json={"phone": "0909999999"},
    )

    assert res.status_code == 403


def test_admin_phone_edit_auto_merges_customer(client, db_session):
    branch, master, proc = _seed_booking_base(db_session)
    admin = _seed_admin(db_session)

    keeper = Customer(
        full_name="Lan",
        phone="0901",
        phone_normalized="0901",
        email="lan@example.com",
        notes="Existing VIP",
    )
    source = Customer(
        full_name="Minh",
        phone="0902",
        phone_normalized="0902",
        email="minh@example.com",
        notes="Likes quiet",
    )
    db_session.add_all([keeper, source])
    db_session.flush()

    tag_def = CustomerTagDefinition(
        name="VIP",
        slug="vip",
        scope=DefinitionScope.global_,
        branch_id=None,
        is_active=True,
        created_by_staff_id=admin.id,
    )
    pref_def = CustomerPreferenceDefinition(
        name="Quiet",
        slug="quiet",
        scope=DefinitionScope.branch,
        branch_id=branch.id,
        value_type=PreferenceValueType.boolean,
        options_json=None,
        is_active=True,
        created_by_staff_id=admin.id,
    )
    db_session.add_all([tag_def, pref_def])
    db_session.flush()

    db_session.add(
        Appointment(
            branch_id=branch.id,
            master_id=master.id,
            procedure_id=proc.id,
            customer_id=source.id,
            client_name="Minh",
            client_phone="0902",
            client_email="minh@example.com",
            start_time=datetime(2030, 1, 3, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2030, 1, 3, 11, 0, tzinfo=timezone.utc),
            price=Decimal("120.00"),
        )
    )
    db_session.add(
        CustomerTag(
            customer_id=source.id,
            tag_definition_id=tag_def.id,
            assigned_by_staff_id=admin.id,
        )
    )
    db_session.add(
        CustomerPreferenceValue(
            customer_id=source.id,
            preference_definition_id=pref_def.id,
            value_bool=True,
            updated_by_staff_id=admin.id,
        )
    )
    db_session.commit()

    res = client.patch(
        f"/api/admin/customers/{source.id}",
        headers={"Authorization": f"Bearer {_token_for(admin)}"},
        json={"phone": "0901"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["id"] == keeper.id
    assert body["merge_happened"] is True
    assert body["merged_from_customer_id"] == source.id

    db_session.refresh(keeper)
    db_session.refresh(source)
    moved = db_session.exec(select(Appointment).where(Appointment.customer_id == keeper.id)).all()
    merge_logs = db_session.exec(select(CustomerMergeLog)).all()

    assert source.is_active is False
    assert source.merged_into_customer_id == keeper.id
    assert "Existing VIP" in (keeper.notes or "")
    assert "Likes quiet" in (keeper.notes or "")
    assert len(moved) == 1
    assert db_session.get(CustomerTag, (keeper.id, tag_def.id)) is not None
    assert db_session.get(CustomerPreferenceValue, (keeper.id, pref_def.id)) is not None
    assert len(merge_logs) == 1


def test_admin_can_manage_global_tag_definition(client, db_session):
    admin = _seed_admin(db_session)

    create_res = client.post(
        "/api/admin/customer-tag-definitions",
        headers={"Authorization": f"Bearer {_token_for(admin)}"},
        json={"name": "VIP", "slug": "vip", "scope": "global"},
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["scope"] == "global"
    assert created["branch_id"] is None

    patch_res = client.patch(
        f"/api/admin/customer-tag-definitions/{created['id']}",
        headers={"Authorization": f"Bearer {_token_for(admin)}"},
        json={"name": "VIP Gold"},
    )
    patch_res.raise_for_status()
    assert patch_res.json()["name"] == "VIP Gold"

    list_res = client.get(
        "/api/admin/customer-tag-definitions",
        headers={"Authorization": f"Bearer {_token_for(admin)}"},
    )
    list_res.raise_for_status()
    assert [row["slug"] for row in list_res.json()] == ["vip"]


def test_manager_can_manage_branch_preference_definition_only_for_own_branch(client, db_session):
    branch, _, _ = _seed_booking_base(db_session)
    other_branch = Branch(name="Riverside", timezone="UTC", open_time=time(8, 0), close_time=time(20, 0))
    db_session.add(other_branch)
    db_session.commit()

    admin = _seed_admin(db_session)
    manager = _seed_manager(db_session, branch.id)

    create_res = client.post(
        "/api/manager/customer-preference-definitions",
        headers={"Authorization": f"Bearer {_token_for(manager)}"},
        json={"name": "Quiet", "slug": "quiet", "value_type": "boolean"},
    )
    assert create_res.status_code == 201
    created = create_res.json()
    assert created["scope"] == "branch"
    assert created["branch_id"] == branch.id

    global_def = CustomerPreferenceDefinition(
        name="VIP room",
        slug="vip-room",
        scope=DefinitionScope.global_,
        branch_id=None,
        value_type=PreferenceValueType.boolean,
        options_json=None,
        is_active=True,
        created_by_staff_id=admin.id,
    )
    foreign_def = CustomerPreferenceDefinition(
        name="Window",
        slug="window",
        scope=DefinitionScope.branch,
        branch_id=other_branch.id,
        value_type=PreferenceValueType.boolean,
        options_json=None,
        is_active=True,
        created_by_staff_id=admin.id,
    )
    db_session.add_all([global_def, foreign_def])
    db_session.commit()

    global_patch = client.patch(
        f"/api/manager/customer-preference-definitions/{global_def.id}",
        headers={"Authorization": f"Bearer {_token_for(manager)}"},
        json={"name": "Changed"},
    )
    foreign_patch = client.patch(
        f"/api/manager/customer-preference-definitions/{foreign_def.id}",
        headers={"Authorization": f"Bearer {_token_for(manager)}"},
        json={"name": "Changed"},
    )

    assert global_patch.status_code == 404
    assert foreign_patch.status_code == 404


def test_admin_customer_update_syncs_tags_and_preferences(client, db_session):
    branch, master, proc = _seed_booking_base(db_session)
    admin = _seed_admin(db_session)
    customer = Customer(full_name="An", phone="0903", phone_normalized="0903", email="an@example.com")
    db_session.add(customer)
    db_session.flush()
    db_session.add(
        Appointment(
            branch_id=branch.id,
            master_id=master.id,
            procedure_id=proc.id,
            customer_id=customer.id,
            client_name="An",
            client_phone="0903",
            client_email="an@example.com",
            start_time=datetime(2030, 1, 4, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2030, 1, 4, 11, 0, tzinfo=timezone.utc),
            price=Decimal("90.00"),
        )
    )
    tag_def = CustomerTagDefinition(
        name="VIP",
        slug="vip",
        scope=DefinitionScope.global_,
        branch_id=None,
        is_active=True,
        created_by_staff_id=admin.id,
    )
    pref_def = CustomerPreferenceDefinition(
        name="Quiet",
        slug="quiet",
        scope=DefinitionScope.branch,
        branch_id=branch.id,
        value_type=PreferenceValueType.boolean,
        options_json=None,
        is_active=True,
        created_by_staff_id=admin.id,
    )
    db_session.add_all([tag_def, pref_def])
    db_session.commit()

    patch_res = client.patch(
        f"/api/admin/customers/{customer.id}",
        headers={"Authorization": f"Bearer {_token_for(admin)}"},
        json={
            "tag_ids": [tag_def.id],
            "preferences": [{"definition_id": pref_def.id, "value_bool": True}],
        },
    )

    assert patch_res.status_code == 200
    body = patch_res.json()
    assert [tag["slug"] for tag in body["tags"]] == ["vip"]
    assert body["preferences"][0]["slug"] == "quiet"
    assert body["preferences"][0]["value_bool"] is True
