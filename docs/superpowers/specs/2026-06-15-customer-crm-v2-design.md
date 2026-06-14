# Customer CRM v2 — Design Spec

Date: 2026-06-15
Status: Approved (design)

## Goal

Expand Zenail's customer CRM from a basic history/profile surface into a real staff workflow:

1. Full customer profile editing.
2. Structured tag catalog with customer tag assignments.
3. Structured preference catalog with customer preference values.
4. CRM data rendered directly inside admin and manager appointment surfaces.
5. Automatic customer merge when an admin changes a phone number to one that already belongs to another customer.

This slice is intentionally focused on staff operations. It does not include marketing, loyalty, retention campaigns, or guest-facing CRM.

## Non-goals

- Loyalty points, gift cards, wallets, or credits.
- Customer segmentation dashboards.
- Follow-up campaigns, reminders beyond the existing notification system, or retention automation.
- Manual merge review queues.
- Customer self-service profile editing.
- Full reporting over tags/preferences in phase 1.

## Current State

Already implemented in the repo:

- `Customer` domain model linked to `Appointment.customer_id`.
- Public booking reuses or creates customers by normalized phone.
- Staff customer list/detail pages exist.
- Customer detail already shows appointment history, completed spend, upcoming appointment, and free-text notes.

Current gap:

- No structured CRM metadata beyond free-text notes.
- No controlled editing of core identity beyond notes.
- No tag or preference taxonomy.
- No CRM context on appointment screens.
- No merge policy when the phone dedupe key changes.

## Architecture

```
+------------------------+       +----------------------------+
| admin / manager CRM UI |<----->| CRM API surface            |
| - customer profile     |       | - customer patch           |
| - catalog management   |       | - tag/pref definition CRUD |
| - appointment CRM      |       | - hydrated appointment DTO |
+-----------+------------+       +-------------+--------------+
            |                                        |
            v                                        v
+------------------------+       +----------------------------+
| CRM service layer      |       | Merge service              |
| - definition scope     |       | - detect phone collision   |
| - customer assignment  |       | - move relations           |
| - appointment shaping  |       | - record merge log         |
+-----------+------------+       +-------------+--------------+
            |                                        |
            +--------------------+-------------------+
                                 |
                                 v
                     +-----------------------------+
                     | SQLModel tables             |
                     | - customers                 |
                     | - tag definitions           |
                     | - preference definitions    |
                     | - customer_tags             |
                     | - customer_preference_vals  |
                     | - customer_merge_logs       |
                     +-----------------------------+
```

The new CRM features live beside the current customer service layer instead of being embedded ad hoc into appointment routes. Appointment routes consume CRM-shaped output but do not own CRM rules.

## Roles and Permissions

### Admin

- Edit customer `full_name`, `phone`, `email`, `notes`.
- Create/update global tag definitions.
- Create/update branch-local tag definitions for any branch.
- Create/update global preference definitions.
- Create/update branch-local preference definitions for any branch.
- Assign/unassign customer tags.
- Edit customer preference values.
- Trigger auto-merge implicitly via phone edit.

### Manager

- Edit customer `full_name`, `email`, `notes`.
- Cannot edit `phone`.
- Create/update branch-local tag definitions for their own branch only.
- Create/update branch-local preference definitions for their own branch only.
- Assign/unassign customer tags visible in their branch scope.
- Edit customer preference values visible in their branch scope.

### Master

- No CRM management access in this slice.

## Data Model

### Existing `customers` changes

Add:

- `merged_into_customer_id` nullable FK to `customers.id`
- `is_active` boolean default `true`

Rules:

- Normal list/search endpoints exclude inactive merged customers.
- Historical appointment rows keep pointing at the surviving customer after merge.

### `customer_tag_definitions`

Columns:

- `id`
- `name`
- `slug`
- `scope` enum: `global | branch`
- `branch_id` nullable FK branches
- `is_active` boolean default `true`
- `created_by_staff_id` FK staff
- `created_at`
- `updated_at`

Constraints:

- unique `(scope, branch_id, slug)`
- global rows require `branch_id IS NULL`
- branch rows require `branch_id IS NOT NULL`

### `customer_preference_definitions`

Columns:

- `id`
- `name`
- `slug`
- `scope` enum: `global | branch`
- `branch_id` nullable FK branches
- `value_type` enum: `text | boolean | single_select`
- `options_json` nullable JSON
- `is_active` boolean default `true`
- `created_by_staff_id` FK staff
- `created_at`
- `updated_at`

Constraints:

- unique `(scope, branch_id, slug)`
- `options_json` required only when `value_type='single_select'`

### `customer_tags`

Columns:

- `customer_id`
- `tag_definition_id`
- `assigned_by_staff_id`
- `created_at`

Constraints:

- unique `(customer_id, tag_definition_id)`

### `customer_preference_values`

Columns:

- `customer_id`
- `preference_definition_id`
- `value_text` nullable
- `value_bool` nullable
- `value_option` nullable
- `updated_by_staff_id`
- `created_at`
- `updated_at`

Constraints:

- unique `(customer_id, preference_definition_id)`
- exactly one value column should be populated based on `value_type`

### `customer_merge_logs`

Columns:

- `id`
- `source_customer_id`
- `target_customer_id`
- `trigger` enum: `admin_phone_edit`
- `performed_by_staff_id`
- `snapshot_json`
- `created_at`

Purpose:

- durable audit trail for automatic merges
- stores pre-merge source state and conflict details

## Scope Model

Hybrid taxonomy:

- Global definitions are available across all branches.
- Branch-local definitions are available only within their branch.

Rendering rule on customer surfaces:

- Admin sees all assigned global definitions plus all assigned branch-local definitions.
- Manager sees all assigned global definitions plus branch-local definitions relevant to their branch scope.

Rendering rule on appointment surfaces:

- Show all assigned global definitions.
- Show branch-local definitions only for the appointment's `branch_id`.

## Merge Semantics

Auto-merge triggers only when:

- actor is admin
- phone edit changes normalized phone
- new normalized phone already belongs to another active customer

### Survivor rule

Use a deterministic rule for phase 1:

- survivor = lower `customer.id`
- source = higher `customer.id`

This avoids ambiguous merges and makes testing straightforward.

### Merge actions

Within one DB transaction:

1. Lock both customer rows.
2. Repoint all `appointments.customer_id` from source to survivor.
3. Repoint or dedupe `customer_tags`.
4. Repoint or resolve `customer_preference_values`.
5. Merge notes.
6. Mark source as inactive and set `merged_into_customer_id`.
7. Insert `customer_merge_logs` row.

### Conflict handling

Tags:

- Keep union of both sets.

Preference values:

- If only one side has a value, keep it.
- If both have values:
  - keep survivor value in the live row
  - store source value in `snapshot_json`

Notes:

- If both non-empty, append source notes to survivor notes with a timestamped separator.

### Response behavior after merge

For the edit request that triggered merge:

- return the surviving customer detail payload
- include merge metadata:
  - `merged_from_customer_id`
  - `merge_happened: true`

For future reads of an inactive merged customer:

- return `404` from normal list/search
- return `409` for direct detail fetch with:
  - `detail="Customer merged"`
  - `merged_into_customer_id`

This keeps normal UX simple while still making stale direct links intelligible.

## API Changes

### Customer detail/edit

Admin:

- `GET /api/admin/customers/{customer_id}`
- `PATCH /api/admin/customers/{customer_id}`

Manager:

- `GET /api/manager/customers/{customer_id}`
- `PATCH /api/manager/customers/{customer_id}`

Patch payload:

- `full_name`
- `phone` admin only
- `email`
- `notes`
- `tag_ids`
- `preferences`

`preferences` shape:

```json
[
  { "definition_id": 12, "value_text": "Prefers late afternoon" },
  { "definition_id": 13, "value_bool": true },
  { "definition_id": 14, "value_option": "gel-only" }
]
```

### Tag definition management

Admin:

- `GET /api/admin/customer-tag-definitions`
- `POST /api/admin/customer-tag-definitions`
- `PATCH /api/admin/customer-tag-definitions/{id}`

Manager:

- `GET /api/manager/customer-tag-definitions`
- `POST /api/manager/customer-tag-definitions`
- `PATCH /api/manager/customer-tag-definitions/{id}`

### Preference definition management

Admin:

- `GET /api/admin/customer-preference-definitions`
- `POST /api/admin/customer-preference-definitions`
- `PATCH /api/admin/customer-preference-definitions/{id}`

Manager:

- `GET /api/manager/customer-preference-definitions`
- `POST /api/manager/customer-preference-definitions`
- `PATCH /api/manager/customer-preference-definitions/{id}`

### Appointment payload hydration

Extend existing admin and manager appointment DTOs with:

- `customer_summary`
  - `id`
  - `full_name`
  - `phone`
  - `email`
  - `notes`
- `customer_tags`
- `customer_preferences`

Do not introduce a second CRM lookup request for appointment rows in phase 1. Hydrate in the existing backend response so the frontend can render directly.

## Frontend Changes

### Customer list page

Current page:

- basic identity
- spend
- latest visit
- notes preview

New page:

- visible tags shown as chips
- visible preference summary shown inline
- merged customers hidden
- filters remain search-first in phase 1; no advanced facet filtering yet

### Customer detail page

Replace the current notes-only edit surface with:

- identity editor
- tag assignment section
- structured preference editor
- notes section
- merge result banner when admin phone edit merges records

### Appointment pages

Apply to admin and manager appointment surfaces:

- appointment list cards render full CRM block in compact form
- appointment detail/modal renders full CRM block with tags, preferences, notes, and customer link

“Full CRM block everywhere” in this spec means all current admin/manager appointment surfaces show CRM context, not only the customer detail page.

### Catalog screens

Add lightweight management pages for:

- tag definitions
- preference definitions

Placement:

- under staff CRM/customer navigation, not under generic system settings

## Validation Rules

- Phone normalization stays the primary identity rule.
- Manager patch requests must reject `phone`.
- Manager can only create/update branch-local definitions in their branch.
- Global definitions are admin-only.
- Inactive merged customers cannot receive new assignments.
- `single_select` preference values must match allowed option slugs.
- Definition slugs are stable once created; display name can be edited.

## Error Handling

- Invalid manager phone edit attempt: `403`
- Branch scope violation for definition management: `403`
- Duplicate slug in same scope: `409`
- Merge target conflict during concurrent edit: `409`
- Direct fetch of merged customer: `409` with `merged_into_customer_id`

## Testing

Backend:

- definition CRUD permission tests
- customer patch permission tests
- appointment payload hydration tests
- admin phone edit auto-merge tests
- merge conflict resolution tests for tags/preferences/notes
- merged customer visibility tests

Frontend:

- existing lint/build gate
- targeted component tests if a frontend test harness is introduced in the same slice
- otherwise manual QA for:
  - admin edit phone triggers merge banner
  - manager cannot edit phone
  - tags/preferences visible on customer and appointment screens
  - branch-local definitions respect scope

## Migration Strategy

Migration adds new CRM tables and customer merge columns only. No data backfill is required for tags/preferences because they are net-new concepts.

Seed/demo data should include:

- a few global tag definitions
- a few branch-local tag definitions
- a few preference definitions across all three `value_type` variants
- at least one customer with assignments for UI verification

## Implementation Notes

- Reuse the existing `backend/app/services/customers.py` as the entry point for shaping CRM output, but split taxonomy and merge logic into focused helpers instead of growing one large service file.
- Keep appointment routers thin; CRM hydration should happen in shared output builders.
- Preserve current list/detail routes and extend them rather than replacing the route layout.
- Do not couple this slice to notification sending, retention, or marketing.
