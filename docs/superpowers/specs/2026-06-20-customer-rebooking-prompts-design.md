# Customer Rebooking Prompts - Design Spec

Date: 2026-06-20
Status: Draft for review

## Goal

Add a staff-first retention workflow that identifies customers who are due to return, shows them in admin/manager action lists, and lets staff explicitly trigger rebooking outreach through the existing notification outbox.

This is the first slice of a broader Customer Retention and Loyalty epic. It builds on the current customer CRM, appointment history, tags/preferences, and notification outbox without adding fully automated marketing campaigns.

## Non-goals

- Loyalty points, wallets, gift cards, or rewards.
- Automatic background outreach without staff action.
- Bulk marketing campaigns.
- Customer-facing preference or opt-out UI.
- Service-specific cadence rules in phase 1.
- Real SMTP, SMS, or Zalo provider integration. Existing provider wiring remains the boundary.
- Advanced segmentation dashboards.

## Current State

Already implemented in the repo:

- `Customer` records are linked to appointments through `appointments.customer_id`.
- Public booking creates or reuses customers by normalized phone.
- Admin and manager can view customer list/detail screens.
- Customer CRM v2 adds editable profile data, tags, preferences, appointment CRM hydration, and merge handling.
- Notifications use a durable outbox in `notifications` with a provider abstraction.

Current gap:

- Staff can see customer history, but the product does not identify which customers are due for follow-up.
- There is no staff action queue for retention work.
- Notification sending is event-driven for appointment reminders/cancel/reschedule only, not rebooking outreach.

## Product Shape

Rebooking prompts are staff-owned tasks, not automatic campaigns.

The system computes a due date from the customer's last completed appointment in a branch. When a customer is due and has no future scheduled appointment in that branch, the customer appears in a rebooking list for staff.

Staff can:

- review the due customer
- open the customer detail page
- mark as contacted
- snooze the prompt
- dismiss the prompt
- trigger a rebooking notification

The notification action writes rows to the existing `notifications` outbox and lets the existing dispatcher/provider layer handle delivery. If only log providers are configured, the flow remains safe and auditable without pretending external delivery is available.

## Roles and Scope

### Admin

- Sees due prompts across all branches.
- Can filter by branch.
- Can mark, snooze, dismiss, and trigger outreach for any prompt.
- Can see retention state on any customer detail page.

### Manager

- Sees due prompts only for their branch.
- Can mark, snooze, dismiss, and trigger outreach for branch-visible prompts.
- Can see retention state on branch-visible customer detail pages.

### Master

- No retention queue access in phase 1.

## Due Rules

Phase 1 uses one global cadence:

- default cadence: `21 days`
- a prompt becomes due when:
  - customer is active
  - customer has at least one completed appointment in the branch
  - latest completed appointment start time is older than `cadence_days`
  - customer has no scheduled future appointment in the same branch
  - prompt is not snoozed into the future
  - prompt is not dismissed for the same latest completed appointment

The due rule is branch-specific. A customer can be due in one branch and not due in another if their completed appointment history differs by branch.

Future cadence rules can be added later by branch or service category, but phase 1 should not add those tables.

## Data Model

### New enum `CustomerRebookingPromptStatus`

Values:

- `open`
- `contacted`
- `snoozed`
- `dismissed`

### New table `customer_rebooking_prompts`

Columns:

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `customer_id` | FK customers(id) ON DELETE CASCADE | indexed |
| `branch_id` | FK branches(id) ON DELETE CASCADE | indexed |
| `last_completed_appointment_id` | FK appointments(id) ON DELETE SET NULL | snapshot of the appointment that produced this prompt |
| `last_completed_at` | timestamptz | snapshot used for due calculations |
| `due_at` | timestamptz | first time prompt should appear |
| `status` | enum | `open`, `contacted`, `snoozed`, `dismissed` |
| `snoozed_until` | timestamptz nullable | only meaningful for `snoozed` |
| `contacted_at` | timestamptz nullable | set when staff marks contacted or sends outreach |
| `dismissed_at` | timestamptz nullable | set when dismissed |
| `created_by_staff_id` | FK staff(id) nullable | null for system-created prompts |
| `updated_by_staff_id` | FK staff(id) nullable | last staff actor |
| `created_at` / `updated_at` | timestamptz | |

Indexes and constraints:

- index `(branch_id, status, due_at)`
- index `(customer_id, branch_id)`
- unique `(customer_id, branch_id, last_completed_appointment_id)` where `last_completed_appointment_id IS NOT NULL`

The unique constraint prevents duplicate prompts for the same customer's same last completed branch visit. If the customer completes a new appointment later, a new prompt can be created for that newer appointment.

## Prompt Generation

Prompt generation should live in a service, not in route code:

- `backend/app/services/rebooking_prompts.py`

Core operations:

- `enqueue_due_rebooking_prompts(session, *, now=None, cadence_days=None)`
- `list_rebooking_prompts(session, *, branch_id=None, status=None, query=None, limit=50, offset=0)`
- `get_rebooking_prompt(session, prompt_id, *, branch_id=None)`
- `mark_contacted(session, prompt, actor_id)`
- `snooze_prompt(session, prompt, actor_id, snoozed_until)`
- `dismiss_prompt(session, prompt, actor_id)`
- `send_rebooking_prompt(session, prompt, actor_id)`
- `reopen_expired_snoozes(session, *, now=None)`

Generation can run in two ways:

1. Scheduler job every 30 minutes, gated by settings.
2. Admin manual endpoint for immediate recalculation during testing/operations.

The query should group completed appointments by `(customer_id, branch_id)` and find the latest completed appointment. It should exclude customers with a future scheduled appointment in the same branch.

The same scheduled job should reopen snoozed prompts when `snoozed_until <= now()` by setting `status='open'` and clearing `snoozed_until`.

## Notification Integration

Add a new notification kind:

- `rebooking_prompt`

The current notification outbox is appointment-centered: `notifications.appointment_id` is non-null. Rebooking outreach is customer-centered, so phase 1 must extend the outbox instead of inventing a fake appointment.

Modify `notifications`:

- make `appointment_id` nullable
- add `customer_id` nullable FK to `customers(id)` with index
- add `rebooking_prompt_id` nullable FK to `customer_rebooking_prompts(id)` with index
- keep existing appointment notification rows unchanged
- require rebooking notification rows to have `customer_id` and `rebooking_prompt_id`

Existing appointment reminders/cancel/reschedule logic should continue to write `appointment_id`. The reminder partial unique index still applies only to rows where `kind='reminder_24h'`; it should not constrain `rebooking_prompt` rows.

Recipient/channel matrix:

| Recipient | rebooking_prompt |
|---|---|
| guest | email + sms + zalo_zns |
| staff | none |

Templates:

- `rebooking_prompt.guest.email`
- `rebooking_prompt.guest.sms`
- `rebooking_prompt.guest.zalo_zns`

Payload fields:

- `client_name`
- `branch_name`
- `last_visit_local`
- `booking_link`
- `phone`

Do not include `booking_reference` for rebooking prompts. There is no new appointment yet, and the outbox should be linked to `customer_id` / `rebooking_prompt_id`.

Sending is explicit:

- staff clicks send on an open/snoozed/contacted prompt
- service writes guest notification rows to the outbox
- prompt moves to `contacted`
- `contacted_at` and `updated_by_staff_id` are updated

If the guest has no usable address for a channel, follow the existing notification behavior: write a `skipped` row for audit when practical.

## API Surface

### Admin

- `GET /api/admin/rebooking-prompts`
- `POST /api/admin/rebooking-prompts/run`
- `POST /api/admin/rebooking-prompts/{prompt_id}/contacted`
- `POST /api/admin/rebooking-prompts/{prompt_id}/snooze`
- `POST /api/admin/rebooking-prompts/{prompt_id}/dismiss`
- `POST /api/admin/rebooking-prompts/{prompt_id}/send`

### Manager

- `GET /api/manager/rebooking-prompts`
- `POST /api/manager/rebooking-prompts/{prompt_id}/contacted`
- `POST /api/manager/rebooking-prompts/{prompt_id}/snooze`
- `POST /api/manager/rebooking-prompts/{prompt_id}/dismiss`
- `POST /api/manager/rebooking-prompts/{prompt_id}/send`

Manager routes must scope prompts to `staff.branch_id`.

### Customer Detail Hydration

Extend existing admin/manager customer detail output with a compact retention block:

```json
{
  "retention": {
    "branch_id": 1,
    "last_completed_at": "2026-06-01T10:00:00Z",
    "days_since_last_completed": 21,
    "next_appointment_at": null,
    "prompt_status": "open",
    "prompt_due_at": "2026-06-22T10:00:00Z"
  }
}
```

Admin customer detail can include all branch retention states or the most urgent one. Phase 1 should use the most urgent one to keep the payload simple.

## Frontend

Add one staff page:

- `frontend/src/pages/staff/RebookingPromptsPage.tsx`

Routes:

- manager: `/staff/rebooking`
- admin: `/staff/admin/rebooking`

Navigation:

- add a staff nav entry near Customers/CRM

List row should show:

- customer name
- phone/email availability
- branch
- last completed service/date
- days since last completed visit
- assigned CRM tags/preferences summary when available
- current prompt status
- actions: open customer, mark contacted, snooze, dismiss, send

Customer detail should show a small retention block using the same operational style as the CRM blocks. No marketing-style dashboard is needed.

## Settings

Add settings:

```env
REBOOKING_PROMPTS_ENABLED=true
REBOOKING_PROMPT_CADENCE_DAYS=21
REBOOKING_PROMPT_SCHEDULER_MINUTES=30
```

Use backend settings so tests and production can disable the scheduler independently.

## Error Handling

- If a prompt is not visible to the current role/branch, return `404`.
- If a prompt already belongs to a newer completed appointment, list endpoints should return the newer prompt only.
- Sending a prompt without any usable guest contact should still mark the action auditable and return a clear response with skipped channels.
- Snooze requires a future timestamp.
- Dismiss is scoped to the current `last_completed_appointment_id`; a later completed appointment can create a new prompt.

## Testing

Backend tests:

- prompt generation creates one prompt per due `(customer_id, branch_id)`
- prompt generation excludes customers with future scheduled appointments
- prompt generation respects snoozed/dismissed state
- manager list is branch-scoped
- admin list can see all branches
- contacted/snooze/dismiss mutations update status and actor fields
- send action writes notification outbox rows and marks prompt contacted
- customer detail includes retention state

Frontend:

- existing lint/build gate
- add component tests only if a frontend test harness exists in the same slice
- otherwise manual QA:
  - manager sees only branch prompts
  - admin branch filter works
  - send moves prompt to contacted
  - snooze removes prompt from open list until future date
  - customer detail retention block matches the list row

## Migration Strategy

One Alembic revision:

- add `customer_rebooking_prompt_status` enum
- create `customer_rebooking_prompts`
- add indexes and unique constraint
- add `rebooking_prompt` to the notification kind enum
- alter `notifications.appointment_id` nullable
- add `notifications.customer_id`
- add `notifications.rebooking_prompt_id`

For PostgreSQL enum migration, update `notification_kind` with `ALTER TYPE ... ADD VALUE` before any code writes `rebooking_prompt`.

No historical prompt backfill is needed in the migration. The first scheduled/manual generation run can create prompts from existing completed appointments.

## Implementation Notes

- Keep due-customer calculation in `backend/app/services/rebooking_prompts.py`; routers should stay thin.
- Reuse `customer_detail_out` and CRM output helpers rather than duplicating tag/preference shaping.
- Reuse the existing notification outbox and dispatcher. Do not introduce a second delivery path.
- Keep templates VI-only unless the notification system gains multi-language templates in a separate slice.
- Avoid service-specific cadence in v1; design the service so cadence can become a strategy later.

## Success Criteria

- Staff can find customers due for rebooking without manually scanning customer history.
- Manager visibility is branch-safe.
- Admin can trigger prompt generation and see prompts across branches.
- Staff can mark, snooze, dismiss, and send outreach from the action list.
- Notification outbox rows provide an audit trail for outreach attempts.
- Backend tests and frontend lint/build remain green.
