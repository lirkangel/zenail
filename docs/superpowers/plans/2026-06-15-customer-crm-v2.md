# Customer CRM v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add structured customer CRM metadata, full customer profile editing, appointment CRM hydration, and admin-triggered auto-merge on phone collisions.

**Architecture:** Extend the existing `Customer` domain with structured tag/preference catalogs and assignment tables, then hydrate the existing admin/manager customer and appointment routes from shared CRM service helpers. Auto-merge stays synchronous and deterministic inside the admin customer update flow so the business rule is easy to test and audit.

**Tech Stack:** FastAPI, SQLModel, Alembic, PostgreSQL/SQLite tests, React, Vite, TypeScript, React Query.

---

## File Structure

- `backend/app/models/customer.py`
  - Extend `Customer` with merge state and define CRM catalog/assignment/log tables.
- `backend/alembic/versions/<rev>_customer_crm_v2.py`
  - Create new CRM tables and customer merge columns.
- `backend/app/schemas/customer.py`
  - Extend customer DTOs and add CRM catalog/value payloads.
- `backend/app/services/customers.py`
  - Keep list/detail shaping here, add CRM assignment/value hydration.
- `backend/app/services/customer_merge.py`
  - Isolate merge logic instead of bloating `customers.py`.
- `backend/app/routers/admin.py`
  - Add admin CRM definition endpoints and expand customer patch flow.
- `backend/app/routers/manager.py`
  - Add manager CRM definition endpoints and manager-safe customer editing.
- `backend/app/schemas/admin.py` and `backend/app/schemas/manager.py`
  - Only if route-local schema types are needed to keep `customer.py` focused.
- `backend/tests/test_customer_crm.py`
  - Extend current CRM coverage instead of creating a fragmented second test file.
- `frontend/src/api/types.ts`
  - Add CRM definition/value types and hydrated appointment customer shape.
- `frontend/src/pages/staff/CustomerListPage.tsx`
  - Render tags and preference summary.
- `frontend/src/pages/staff/CustomerDetailPage.tsx`
  - Replace notes-only editor with full CRM editor.
- `frontend/src/pages/staff/admin/AdminAppointmentsPage.tsx` or existing admin appointment surface files
  - Inject full CRM block.
- `frontend/src/pages/staff/manager/ManagerAppointmentsPage.tsx`
  - Inject full CRM block.
- `frontend/src/App.tsx`
  - Add routes for CRM definition screens if they do not already exist.
- `frontend/src/layouts/StaffLayout.tsx`
  - Add navigation entry points for CRM definitions where appropriate.
- `frontend/src/i18n/messages.ts`
  - Add labels and merge-status messages.
- `README.md`
  - Update feature list after implementation.

---

### Task 1: Add CRM Schema and Migration

**Files:**
- Modify: `backend/app/models/customer.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/<rev>_customer_crm_v2.py`
- Test: `backend/tests/test_customer_crm.py`

- [ ] **Step 1: Write failing model-level tests**

Add tests like:

```python
def test_customer_crm_models_support_tag_and_preference_assignments(db_session: Session) -> None:
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
        scope=DefinitionScope.global_,
        branch_id=None,
        value_type=PreferenceValueType.boolean,
        options_json=None,
        is_active=True,
        created_by_staff_id=1,
    )
    db_session.add_all([customer, tag_def, pref_def])
    db_session.commit()

    db_session.add(CustomerTag(customer_id=customer.id, tag_definition_id=tag_def.id, assigned_by_staff_id=1))
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
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k crm_models_support_tag_and_preference_assignments -q
```

Expected: FAIL with missing CRM model classes or fields.

- [ ] **Step 3: Add CRM model classes and enums**

Update `backend/app/models/customer.py` with the new types. The shape should look like:

```python
class DefinitionScope(str, Enum):
    global_ = "global"
    branch = "branch"


class PreferenceValueType(str, Enum):
    text = "text"
    boolean = "boolean"
    single_select = "single_select"


class Customer(SQLModel, table=True):
    __tablename__ = "customers"
    ...
    merged_into_customer_id: int | None = Field(
        default=None,
        foreign_key="customers.id",
        index=True,
    )
    is_active: bool = Field(default=True, nullable=False)


class CustomerTagDefinition(SQLModel, table=True):
    __tablename__ = "customer_tag_definitions"
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True, max_length=120)
    slug: str = Field(index=True, max_length=120)
    scope: DefinitionScope = Field(sa_column=Column(sa.Enum(DefinitionScope), nullable=False))
    branch_id: int | None = Field(default=None, foreign_key="branches.id")
    is_active: bool = Field(default=True, nullable=False)
    created_by_staff_id: int = Field(foreign_key="staff.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CustomerPreferenceDefinition(SQLModel, table=True):
    __tablename__ = "customer_preference_definitions"
    ...


class CustomerTag(SQLModel, table=True):
    __tablename__ = "customer_tags"
    customer_id: int = Field(foreign_key="customers.id", primary_key=True)
    tag_definition_id: int = Field(foreign_key="customer_tag_definitions.id", primary_key=True)
    assigned_by_staff_id: int = Field(foreign_key="staff.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CustomerPreferenceValue(SQLModel, table=True):
    __tablename__ = "customer_preference_values"
    customer_id: int = Field(foreign_key="customers.id", primary_key=True)
    preference_definition_id: int = Field(foreign_key="customer_preference_definitions.id", primary_key=True)
    value_text: str | None = Field(default=None)
    value_bool: bool | None = Field(default=None)
    value_option: str | None = Field(default=None, max_length=120)
    updated_by_staff_id: int = Field(foreign_key="staff.id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CustomerMergeLog(SQLModel, table=True):
    __tablename__ = "customer_merge_logs"
    ...
```

Also export the new models and enums from `backend/app/models/__init__.py`.

- [ ] **Step 4: Write the migration**

Create `backend/alembic/versions/<rev>_customer_crm_v2.py` with operations equivalent to:

```python
def upgrade() -> None:
    op.add_column("customers", sa.Column("merged_into_customer_id", sa.Integer(), nullable=True))
    op.add_column("customers", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_foreign_key(
        "fk_customers_merged_into_customer_id",
        "customers",
        "customers",
        ["merged_into_customer_id"],
        ["id"],
    )
    op.create_table(...)
    op.create_index("ix_customer_tag_definitions_scope_branch_slug", "customer_tag_definitions", ["scope", "branch_id", "slug"], unique=True)
    ...
    op.alter_column("customers", "is_active", server_default=None)
```

Ensure the migration uses the actual current `down_revision`.

- [ ] **Step 5: Run the focused test to verify it passes**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k crm_models_support_tag_and_preference_assignments -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/customer.py backend/app/models/__init__.py backend/alembic/versions backend/tests/test_customer_crm.py
git commit -m "feat(crm): add customer crm v2 schema"
```

### Task 2: Add Merge Service and Customer Patch Rules

**Files:**
- Create: `backend/app/services/customer_merge.py`
- Modify: `backend/app/services/customers.py`
- Modify: `backend/app/schemas/customer.py`
- Modify: `backend/app/routers/admin.py`
- Modify: `backend/app/routers/manager.py`
- Test: `backend/tests/test_customer_crm.py`

- [ ] **Step 1: Write failing API tests for edit permissions and auto-merge**

Add tests like:

```python
def test_manager_cannot_edit_customer_phone(client, db_session):
    ...
    res = client.patch(
        f"/api/manager/customers/{customer.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "0909999999"},
    )
    assert res.status_code == 403


def test_admin_phone_edit_auto_merges_customer(client, db_session):
    keeper = Customer(full_name="A", phone="0901", phone_normalized="0901")
    source = Customer(full_name="B", phone="0902", phone_normalized="0902", notes="Likes quiet")
    ...
    res = client.patch(
        f"/api/admin/customers/{source.id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "0901"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["merge_happened"] is True
    assert body["merged_from_customer_id"] == source.id
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k "manager_cannot_edit_customer_phone or admin_phone_edit_auto_merges_customer" -q
```

Expected: FAIL because the routes do not enforce the new policy or merge behavior.

- [ ] **Step 3: Add merge service**

Create `backend/app/services/customer_merge.py` with functions shaped like:

```python
def merge_customers(
    db: Session,
    *,
    source: Customer,
    target: Customer,
    performed_by_staff_id: int,
) -> CustomerMergeResult:
    _move_appointments(db, source_id=source.id, target_id=target.id)
    _merge_tags(db, source_id=source.id, target_id=target.id)
    _merge_preference_values(db, source_id=source.id, target_id=target.id)
    merged_notes = combine_notes(target.notes, source.notes)
    target.notes = merged_notes
    source.is_active = False
    source.merged_into_customer_id = target.id
    db.add(CustomerMergeLog(...))
    db.flush()
    return CustomerMergeResult(target_customer_id=target.id, source_customer_id=source.id)
```

- [ ] **Step 4: Expand schemas and patch helpers**

Update `backend/app/schemas/customer.py` with payload/response types:

```python
class CustomerPreferenceValueIn(SQLModel):
    definition_id: int
    value_text: str | None = None
    value_bool: bool | None = None
    value_option: str | None = None


class CustomerUpdate(SQLModel):
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None
    tag_ids: list[int] | None = None
    preferences: list[CustomerPreferenceValueIn] | None = None


class CustomerTagOut(SQLModel):
    id: int
    name: str
    slug: str
    scope: str
    branch_id: int | None = None


class CustomerPreferenceOut(SQLModel):
    definition_id: int
    name: str
    slug: str
    value_type: str
    value_text: str | None = None
    value_bool: bool | None = None
    value_option: str | None = None


class CustomerDetailOut(CustomerListItemOut):
    tags: list[CustomerTagOut]
    preferences: list[CustomerPreferenceOut]
    merge_happened: bool = False
    merged_from_customer_id: int | None = None
    appointments: list[CustomerAppointmentOut]
```

- [ ] **Step 5: Implement admin and manager patch rules**

Route logic should follow this shape:

```python
@router.patch("/admin/customers/{customer_id}", response_model=CustomerDetailOut)
def update_customer(...):
    customer = active_customer_or_404(db, customer_id)
    result = apply_customer_update(
        db,
        actor=me,
        customer=customer,
        payload=payload,
        allow_phone_edit=True,
        branch_scope=None,
    )
    db.commit()
    db.refresh(result.customer)
    return customer_detail_out(
        db,
        customer=result.customer,
        branch_id=None,
        merge_happened=result.merge_happened,
        merged_from_customer_id=result.merged_from_customer_id,
    )


@router.patch("/manager/customers/{customer_id}", response_model=CustomerDetailOut)
def update_customer(...):
    if payload.phone is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Managers cannot edit phone")
```

Keep the actual mutation logic in `customers.py`, not in the routers.

- [ ] **Step 6: Run the focused tests to verify they pass**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k "manager_cannot_edit_customer_phone or admin_phone_edit_auto_merges_customer" -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/customer_merge.py backend/app/services/customers.py backend/app/schemas/customer.py backend/app/routers/admin.py backend/app/routers/manager.py backend/tests/test_customer_crm.py
git commit -m "feat(crm): add customer edit and auto-merge flow"
```

### Task 3: Add Catalog CRUD and CRM Hydration Helpers

**Files:**
- Modify: `backend/app/services/customers.py`
- Modify: `backend/app/routers/admin.py`
- Modify: `backend/app/routers/manager.py`
- Modify: `backend/app/schemas/customer.py`
- Test: `backend/tests/test_customer_crm.py`

- [ ] **Step 1: Write failing tests for catalog CRUD and branch scoping**

Add tests like:

```python
def test_admin_can_manage_global_tag_definition(client, db_session):
    ...
    res = client.post(
        "/api/admin/customer-tag-definitions",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "VIP", "slug": "vip", "scope": "global", "branch_id": None},
    )
    assert res.status_code == 201


def test_manager_can_only_manage_branch_local_definitions(client, db_session):
    ...
    res = client.post(
        "/api/manager/customer-tag-definitions",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Quiet", "slug": "quiet", "scope": "global", "branch_id": None},
    )
    assert res.status_code == 403
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k "manage_global_tag_definition or manage_branch_local_definitions" -q
```

Expected: FAIL because endpoints do not exist.

- [ ] **Step 3: Add definition schemas and service helpers**

Add DTOs like:

```python
class CustomerTagDefinitionIn(SQLModel):
    name: str
    slug: str
    scope: str
    branch_id: int | None = None


class CustomerPreferenceDefinitionIn(SQLModel):
    name: str
    slug: str
    scope: str
    branch_id: int | None = None
    value_type: str
    options_json: list[str] | None = None
```

Add helpers in `customers.py`:

```python
def create_tag_definition(...): ...
def update_tag_definition(...): ...
def list_visible_tag_definitions(...): ...
def create_preference_definition(...): ...
def update_preference_definition(...): ...
def list_visible_preference_definitions(...): ...
```

- [ ] **Step 4: Add admin and manager definition routes**

The routes should look like:

```python
@router.get("/admin/customer-tag-definitions", response_model=list[CustomerTagDefinitionOut])
def customer_tag_definitions(...): ...


@router.post("/admin/customer-tag-definitions", response_model=CustomerTagDefinitionOut, status_code=status.HTTP_201_CREATED)
def create_customer_tag_definition(...): ...


@router.get("/manager/customer-preference-definitions", response_model=list[CustomerPreferenceDefinitionOut])
def customer_preference_definitions(...): ...
```

Manager create/update routes must reject global scope or foreign branch scope.

- [ ] **Step 5: Extend CRM shaping for customer detail/list**

Update `customer_item_out` and `customer_detail_out` so they include:

```python
tags = load_customer_tags(db, customer_id=customer.id, branch_id=branch_id)
preferences = load_customer_preferences(db, customer_id=customer.id, branch_id=branch_id)
```

Keep visibility rules:

- include all global definitions
- include branch-local definitions only when visible to that viewer context

- [ ] **Step 6: Run the focused tests to verify they pass**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k "manage_global_tag_definition or manage_branch_local_definitions" -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/customers.py backend/app/routers/admin.py backend/app/routers/manager.py backend/app/schemas/customer.py backend/tests/test_customer_crm.py
git commit -m "feat(crm): add crm catalog management"
```

### Task 4: Hydrate Appointment APIs With CRM Data

**Files:**
- Modify: `backend/app/schemas/public.py`
- Modify: `backend/app/routers/admin.py`
- Modify: `backend/app/routers/manager.py`
- Modify: `backend/app/services/appointment_out.py`
- Modify: `frontend/src/api/types.ts`
- Test: `backend/tests/test_customer_crm.py`

- [ ] **Step 1: Write failing tests for appointment CRM hydration**

Add tests like:

```python
def test_manager_appointments_include_customer_crm_block(client, db_session):
    ...
    res = client.get("/api/manager/appointments?date=2030-01-01", headers={"Authorization": f"Bearer {token}"})
    body = res.json()
    assert body[0]["customer_summary"]["full_name"] == "Lan"
    assert body[0]["customer_tags"][0]["slug"] == "vip"
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k appointments_include_customer_crm_block -q
```

Expected: FAIL because appointment responses do not expose CRM data.

- [ ] **Step 3: Extend appointment response schemas**

In `backend/app/schemas/public.py`, add:

```python
class AppointmentCustomerSummary(SQLModel):
    id: int
    full_name: str
    phone: str
    email: str | None = None
    notes: str | None = None


class AppointmentOut(SQLModel):
    ...
    customer_summary: AppointmentCustomerSummary | None = None
    customer_tags: list[CustomerTagOut] = []
    customer_preferences: list[CustomerPreferenceOut] = []
```

- [ ] **Step 4: Hydrate appointment DTOs from shared helpers**

In `backend/app/services/appointment_out.py`, shape the payload like:

```python
customer_summary = None
customer_tags: list[CustomerTagOut] = []
customer_preferences: list[CustomerPreferenceOut] = []
if appt.customer_id:
    customer = appt.customer or db.get(Customer, appt.customer_id)
    if customer and customer.is_active:
        customer_summary = AppointmentCustomerSummary(...)
        customer_tags = load_customer_tags(db, customer_id=customer.id, branch_id=appt.branch_id)
        customer_preferences = load_customer_preferences(db, customer_id=customer.id, branch_id=appt.branch_id)
```

Pass `db` if needed rather than duplicating CRM logic in routers.

- [ ] **Step 5: Update frontend API types**

In `frontend/src/api/types.ts`, add:

```ts
export type AppointmentCustomerSummary = {
  id: number
  full_name: string
  phone: string
  email?: string | null
  notes?: string | null
}

export type Appointment = {
  ...
  customer_summary?: AppointmentCustomerSummary | null
  customer_tags?: CustomerTag[]
  customer_preferences?: CustomerPreference[]
}
```

- [ ] **Step 6: Run the focused test to verify it passes**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py -k appointments_include_customer_crm_block -q
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/schemas/public.py backend/app/services/appointment_out.py backend/app/routers/admin.py backend/app/routers/manager.py frontend/src/api/types.ts backend/tests/test_customer_crm.py
git commit -m "feat(crm): hydrate appointments with customer crm data"
```

### Task 5: Build CRM UI for Customer and Appointment Surfaces

**Files:**
- Modify: `frontend/src/pages/staff/CustomerListPage.tsx`
- Modify: `frontend/src/pages/staff/CustomerDetailPage.tsx`
- Modify: `frontend/src/pages/staff/manager/ManagerAppointmentsPage.tsx`
- Modify: `frontend/src/pages/staff/admin/AdminRevenuePage.tsx` only if admin appointment surface lives elsewhere; otherwise touch the actual admin appointment page file
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/StaffLayout.tsx`
- Modify: `frontend/src/i18n/messages.ts`
- Create if needed: `frontend/src/pages/staff/CustomerTagDefinitionsPage.tsx`
- Create if needed: `frontend/src/pages/staff/CustomerPreferenceDefinitionsPage.tsx`

- [ ] **Step 1: Write a minimal UI behavior test plan in comments at the top of the task branch**

Record these manual checks in the commit message body or scratch notes:

```text
1. customer list shows tags and preference summary
2. customer detail allows full edit for admin
3. manager cannot edit phone
4. appointment cards show CRM block
5. merge banner appears after admin phone collision edit
```

- [ ] **Step 2: Expand customer list/detail screens**

In `CustomerListPage.tsx`, render CRM summary blocks shaped like:

```tsx
{customer.tags?.slice(0, 3).map((tag) => (
  <span key={tag.id} className="rounded-full bg-rose-100 px-2 py-1 text-[11px] font-medium text-rose-900">
    {tag.name}
  </span>
))}
{customer.preferences?.slice(0, 2).map((pref) => (
  <div key={pref.definition_id} className="text-xs text-rose-900/65">
    {pref.name}: {formatCustomerPreference(pref)}
  </div>
))}
```

In `CustomerDetailPage.tsx`, replace notes-only editing with:

```tsx
<Input value={fullName} onChange={(e) => setFullName(e.target.value)} />
<Input value={email} onChange={(e) => setEmail(e.target.value)} />
{canEditPhone ? <Input value={phone} onChange={(e) => setPhone(e.target.value)} /> : null}
<TagAssignmentEditor ... />
<PreferenceValueEditor ... />
<textarea ... />
```

If the response has `merge_happened`, show:

```tsx
<div className="rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-900">
  {t('customers.mergeSuccess')}
</div>
```

- [ ] **Step 3: Add CRM block to appointment surfaces**

On manager/admin appointment cards, render:

```tsx
{appt.customer_summary ? (
  <div className="mt-2 rounded-xl border border-rose-100 bg-rose-50/50 px-3 py-2">
    <div className="text-xs font-semibold text-rose-950">{appt.customer_summary.full_name}</div>
    <div className="text-[11px] text-rose-900/70">{appt.customer_summary.phone}</div>
    <div className="mt-1 flex flex-wrap gap-1">
      {(appt.customer_tags ?? []).map((tag) => (
        <span key={tag.id} className="rounded-full bg-white px-2 py-0.5 text-[10px] text-rose-900">
          {tag.name}
        </span>
      ))}
    </div>
    <div className="mt-1 space-y-1 text-[11px] text-rose-900/70">
      {(appt.customer_preferences ?? []).map((pref) => (
        <div key={pref.definition_id}>{pref.name}: {formatCustomerPreference(pref)}</div>
      ))}
    </div>
  </div>
) : null}
```

- [ ] **Step 4: Add catalog management routes and navigation**

Wire routes in `App.tsx`:

```tsx
<Route path="/staff/customer-tags" element={<CustomerTagDefinitionsPage />} />
<Route path="/staff/customer-preferences" element={<CustomerPreferenceDefinitionsPage />} />
```

Add staff navigation entries in `StaffLayout.tsx` only for admin and manager.

- [ ] **Step 5: Add translations**

Add strings to `frontend/src/i18n/messages.ts` for:

- `customers.tags`
- `customers.preferences`
- `customers.mergeSuccess`
- `customers.phoneAdminOnly`
- `customers.tagDefinitions`
- `customers.preferenceDefinitions`

- [ ] **Step 6: Run frontend verification**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: both commands pass.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/staff frontend/src/App.tsx frontend/src/layouts/StaffLayout.tsx frontend/src/i18n/messages.ts frontend/src/api/types.ts
git commit -m "feat(crm): add customer crm v2 ui"
```

### Task 6: Final Verification and Docs

**Files:**
- Modify: `README.md`
- Optionally modify: `docs/backlog/2026-06-05-customer-crm-foundation-backlog.md`
- Test: `backend/tests/test_customer_crm.py`

- [ ] **Step 1: Update docs**

Add a concise feature line to `README.md`:

```md
- Structured customer CRM tags and preferences with appointment-side CRM context
```

If the backlog file is being kept current, append a note under future work clarifying that CRM v2 adds structured metadata and merge behavior.

- [ ] **Step 2: Run the full backend CRM and regression suite**

Run:

```bash
cd backend
uv run python -m pytest tests/test_customer_crm.py tests/test_public_booking.py tests/test_notifications_service.py tests/test_appointment_service.py -q
```

Expected: PASS

- [ ] **Step 3: Run whole backend suite**

Run:

```bash
cd backend
uv run python -m pytest tests -q
```

Expected: PASS

- [ ] **Step 4: Run frontend lint/build again**

Run:

```bash
cd frontend
npm run lint
npm run build
```

Expected: PASS

- [ ] **Step 5: Commit docs and verification changes**

```bash
git add README.md docs/backlog/2026-06-05-customer-crm-foundation-backlog.md
git commit -m "docs(crm): document customer crm v2"
```

---

## Self-Review

### Spec coverage

- Data model changes: Task 1
- Roles and permissions: Tasks 2 and 3
- Auto-merge behavior: Task 2
- Catalog CRUD: Task 3
- Appointment CRM hydration: Task 4
- Customer and appointment UI: Task 5
- Docs and verification: Task 6

No spec section is left without a task.

### Placeholder scan

- No `TBD` / `TODO`.
- Every task includes exact files, commands, and example code shapes.

### Type consistency

- The plan consistently uses:
  - `CustomerTagDefinition`
  - `CustomerPreferenceDefinition`
  - `CustomerTag`
  - `CustomerPreferenceValue`
  - `CustomerMergeLog`
  - `CustomerDetailOut`
  - `CustomerUpdate`

