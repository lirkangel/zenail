# Notifications — Design Spec

Date: 2026-05-09
Status: Approved (design)

## Goal

Send transactional notifications to guests, masters, and managers for three events:

1. **Reminder 24h** before appointment start (guest only).
2. **Cancelled** appointment (guest + assigned master + branch managers).
3. **Rescheduled** appointment (guest + assigned master).

Booking confirmation is **out of scope** — guest already sees booking reference on the success screen.

Channels: email, SMS (VN gateway, e.g. eSMS/SpeedSMS), Zalo ZNS. Master/manager receive **email only**.

## Non-goals

- Booking confirmation messages.
- Marketing/loyalty notifications.
- Per-user notification preferences / opt-out UI.
- Real provider integrations in the first cut — providers are stubbed behind a `LogProvider` until credentials exist.
- Observability dashboards (structured logs only).
- Multi-language templates — VI only in phase 1.

## Architecture

```
+-------------------+       +----------------------+       +------------------+
| routers (admin/   | call  | NotificationService  | write | notifications    |
|  manager) cancel/ |------>| .on_cancelled(...)   |------>| table (outbox)   |
|  reschedule       |       | .on_rescheduled(...) |       +--------+---------+
+-------------------+       +----------------------+                |
                                                                    | poll
                            +----------------------+                v
                            | APScheduler (in app) |       +------------------+
                            |  enqueue_reminders   |------>| dispatch_pending |
                            |  (every 5m)          |       |  (every 1m)      |
                            +----------------------+       +--------+---------+
                                                                    |
                                                                    v
                                                        +-----------+-----------+
                                                        | NotificationProvider  |
                                                        | (log | smtp | esms |  |
                                                        |  zalo)                |
                                                        +-----------------------+
```

Components:

- **`app/notifications/providers/`** — `base.NotificationProvider` interface plus concrete adapters. Phase 1 ships only `LogProvider`; SMTP/eSMS/Zalo classes are stubs raising `NotImplementedError`.
- **`app/notifications/templates/`** — Jinja-rendered text files keyed by `template_key`, e.g. `reminder_24h.guest.sms.vi.txt`.
- **`app/services/notifications.py`** — domain entry points (`on_cancelled`, `on_rescheduled`, `enqueue_reminder`). Resolves recipients, picks templates per channel, writes outbox rows. Pure DB writes; never calls providers directly.
- **`app/notifications/scheduler.py`** — APScheduler `AsyncIOScheduler` started in FastAPI lifespan. Two jobs: `enqueue_reminders` (5 min) and `dispatch_pending` (1 min).
- **`app/models/notification.py`** — SQLModel for the `notifications` outbox.
- **Hooks** in `app/routers/admin.py` and `app/routers/manager.py` at appointment cancel and reschedule endpoints.

## Data model

### New table `notifications`

| Column | Type | Notes |
|---|---|---|
| `id` | int PK | |
| `appointment_id` | FK appointments(id) ON DELETE CASCADE | indexed |
| `kind` | enum `reminder_24h \| cancelled \| rescheduled` | |
| `recipient_role` | enum `guest \| master \| manager` | |
| `recipient_address` | varchar(200) | snapshot of phone/email at enqueue time |
| `channel` | enum `email \| sms \| zalo_zns` | |
| `template_key` | varchar(64) | e.g. `reminder_24h.guest.sms` |
| `payload_json` | JSON | render context (client name, time, branch, ref…) |
| `status` | enum `pending \| sent \| failed \| skipped` | default `pending` |
| `scheduled_at` | timestamptz | earliest send time |
| `sent_at` | timestamptz nullable | |
| `attempt_count` | int default 0 | |
| `last_error` | text nullable | |
| `created_at` / `updated_at` | timestamptz | |

Indexes / constraints:

- Index `(status, scheduled_at)` for dispatcher.
- **Partial unique** on `(appointment_id, recipient_role, channel)` WHERE `kind='reminder_24h'` — idempotency for reminders only. `cancelled` / `rescheduled` may have multiple rows (e.g. repeated reschedules).

### Modified table `appointments`

Add column `client_email varchar(200) NULL`. Optional booking field; if absent, the email channel for guest is recorded as `status='skipped'`.

### Migrations

One Alembic revision: create `notifications` table + enums + indexes, add `client_email` column.

## Recipient & channel matrix

| Recipient | reminder_24h | cancelled | rescheduled |
|---|---|---|---|
| guest | email + sms + zns | email + sms + zns | email + sms + zns |
| master | — | email | email |
| manager (all of branch) | — | email | — |

Resolution:

- **guest**: phone from `appointment.client_phone` (sms / zns); email from `appointment.client_email` if non-null else channel skipped.
- **master**: `staff.email` of `appointment.master_id`.
- **manager**: all `Staff` rows where `role='manager'` AND `branch_id = appointment.branch_id`. Empty set is fine — produces zero rows.

Recipients without a usable address produce a row with `status='skipped'` and `last_error` describing why. We still write the row for audit.

## Templates

Path: `app/notifications/templates/{template_key}.{lang}.txt`. Phase 1 ships only `lang=vi`. Template keys follow `{kind}.{recipient_role}.{channel}`. Each template is a Jinja text file rendered against `payload_json`.

Required keys for phase 1:

- `reminder_24h.guest.email`, `reminder_24h.guest.sms`, `reminder_24h.guest.zalo_zns`
- `cancelled.guest.email`, `cancelled.guest.sms`, `cancelled.guest.zalo_zns`
- `cancelled.master.email`
- `cancelled.manager.email`
- `rescheduled.guest.email`, `rescheduled.guest.sms`, `rescheduled.guest.zalo_zns`
- `rescheduled.master.email`

Email templates produce a single string with subject as the first line and an empty line before the body, parsed at send time. SMS / ZNS templates produce a single short string. ZNS will eventually require a server-registered template id; the `template_key → ZNS template id` mapping lives in settings (`zalo_zns_template_ids`).

Render context (`payload_json`) includes: `client_name`, `branch_name`, `master_name`, `procedures` (list of names), `start_local` (formatted in branch timezone), `booking_reference`, plus event-specific fields (`old_start_local` for reschedule, `cancel_reason` for cancel if provided).

## Flows

### Cancel

1. Router updates `appointment.status='cancelled'` in current DB transaction.
2. `notification_service.on_cancelled(appointment, session)`:
   - Marks all existing `pending` notifications for that appointment as `skipped` with `last_error='superseded by cancel'`.
   - Inserts new rows: guest×3 channels, master×email, managers×email. `scheduled_at = now()`.
3. Transaction commits. Dispatcher picks up rows on next tick.

### Reschedule

1. Router updates `appointment.start_time` / `end_time`.
2. `notification_service.on_rescheduled(appointment, old_start, session)`:
   - Deletes pending rows with `kind='reminder_24h'` for this appointment.
   - Marks pending `kind='rescheduled'` rows for this appointment as `skipped` (newest data wins; we'll re-insert).
   - Inserts new `rescheduled` rows: guest×3, master×email, with `scheduled_at = now()`.
   - Inserts a fresh `reminder_24h` set (guest×3) with `scheduled_at = max(now(), new_start - 24h)`.

### Reminder enqueue (`enqueue_reminders`)

```sql
SELECT a.* FROM appointments a
WHERE a.status = 'scheduled'
  AND a.start_time BETWEEN now() + interval '23 hours'
                       AND now() + interval '24 hours'
  AND NOT EXISTS (
      SELECT 1 FROM notifications n
       WHERE n.appointment_id = a.id AND n.kind = 'reminder_24h'
  );
```

For each row, insert guest reminder rows with `scheduled_at = a.start_time - 24h`. The 1-hour window with a 5-minute interval gives 12 attempts per appointment; the partial unique index is the safety net.

### Dispatch (`dispatch_pending`)

```sql
SELECT * FROM notifications
WHERE status = 'pending'
  AND scheduled_at <= now()
  AND attempt_count < 3
ORDER BY scheduled_at
LIMIT 100
FOR UPDATE SKIP LOCKED;
```

For each row:

- Resolve provider from registry by channel.
- `await provider.send(row)` → `ProviderResult(ok, error)`.
- On success: `status='sent'`, `sent_at=now()`.
- On `ProviderTransientError` or unexpected exception: `attempt_count += 1`, set `last_error`, push `scheduled_at` by backoff `[1m, 5m, 15m]`, keep `status='pending'`. After third failure, set `status='failed'`.
- On `ProviderPermanentError`: set `status='failed'`, `last_error`, no retry.

`FOR UPDATE SKIP LOCKED` is Postgres-specific. For SQLite (tests) we omit the clause via dialect check.

## Settings (env)

```
NOTIFICATIONS_ENABLED=true
NOTIFICATION_PROVIDER_EMAIL=log     # log | smtp
NOTIFICATION_PROVIDER_SMS=log       # log | esms
NOTIFICATION_PROVIDER_ZNS=log       # log | zalo

# SMTP (when provider=smtp)
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM="Zenail <noreply@zenail.local>"

# eSMS (when provider=esms)
ESMS_API_KEY=
ESMS_SECRET_KEY=
ESMS_BRANDNAME=

# Zalo ZNS (when provider=zalo)
ZALO_OA_ACCESS_TOKEN=
# JSON map: {"reminder_24h.guest.zalo_zns": "<template_id>", ...}
ZALO_ZNS_TEMPLATE_IDS={}
```

Defaults (`log` providers, enabled=true) ship safely: nothing leaves the box, but the dispatcher loop still runs and rows transition to `sent`.

## Admin endpoint

`POST /api/admin/notifications/run-dispatcher` — admin-only, runs `dispatch_pending` once synchronously and returns `{processed: N, sent: x, failed: y, skipped: z}`. Handy for manual smoke tests so we don't have to wait for the 1-minute tick.

## Frontend changes

- `BookingForm`: optional "Email (tuỳ chọn)" field. Validated as email if non-empty. Wired into `POST /api/appointments` payload as `client_email`.
- No new staff UI surface in phase 1 — notification rows are visible only via DB / logs.

## Error handling

- **Transient errors** (network, 5xx, rate limit): retried up to 3 times with backoff `1m / 5m / 15m`.
- **Permanent errors** (bad number, unverified ZNS template, expired token): `status='failed'` immediately.
- **Unknown exceptions**: treated as transient, full traceback logged.
- **Hard-deleted appointment**: cascades delete notifications (FK).
- **Branch with no manager**: zero manager rows, no error.
- **Master without email**: defensive `status='skipped'`, though staff schema requires email.
- **Guest without email**: row written with `status='skipped'`, never dispatched.
- **Reschedule into <24h window**: reminder `scheduled_at = now()` so it fires on the next dispatcher tick.
- **Concurrent dispatchers**: `FOR UPDATE SKIP LOCKED` keeps work disjoint. `enqueue_reminders` collisions are absorbed by the partial unique index.
- **Test env**: `NOTIFICATIONS_ENABLED=false` keeps the scheduler from starting; service can still be exercised directly to assert outbox writes.

## Logging

Structured log per dispatched row:
```
notification.dispatched id=<id> kind=<k> channel=<c> status=<s>
  attempt=<n> error=<...>
```

Sufficient to debug from `docker compose logs backend`. No metrics/dashboard in phase 1.

## Testing strategy

Unit tests (`backend/tests/test_notifications_service.py`):

- `on_cancelled` produces correct row counts, with/without `client_email`, with/without managers.
- `on_rescheduled` removes pending reminders and inserts fresh ones; reminder `scheduled_at` matches `new_start - 24h` or `now()` when within 24h.
- Recipient resolution: missing master email → skipped row with reason; branch without manager → no manager rows.
- Template rendering: snapshot 1–2 templates with a fixed payload.
- `LogProvider.send` returns ok and never raises.

Scheduler / dispatcher tests (`backend/tests/test_notifications_scheduler.py`) — call functions directly, do not start APScheduler:

- `enqueue_reminders` only enqueues for `scheduled` appointments inside the 23–24h window.
- Idempotent across two calls.
- Skips `cancelled` appointments.
- `dispatch_pending` happy path: `pending + scheduled_at <= now` → provider called, row marked `sent`.
- Transient error → `attempt_count++`, `scheduled_at` pushed by backoff, still pending.
- Permanent error → `failed` with one attempt.
- After three transient failures → `failed`.

Integration tests (FastAPI test client, SQLite):

- `POST /api/admin/appointments/{id}/cancel` writes `cancelled` notification rows.
- `PATCH /api/admin/appointments/{id}` reschedule writes `rescheduled` rows + replaces pending reminder.
- `POST /api/admin/notifications/run-dispatcher` flips pending rows to `sent` (via `LogProvider`).
- Booking with `client_email` accepted; without email, guest email row is `skipped`.

Frontend: existing lint/build only; manual check that the optional email field renders and is sent.

CI: unchanged. `NOTIFICATIONS_ENABLED=false` in `tests/conftest.py`. Default providers `log` everywhere.

Manual smoke after deploy:

1. Create a booking with `client_email`.
2. Cancel it via admin UI.
3. `POST /api/admin/notifications/run-dispatcher`.
4. `docker compose logs backend` shows 5 `LogProvider sending …` lines.
5. `SELECT status, count(*) FROM notifications GROUP BY status` — all `sent`.

## Deliverables

- 1 Alembic migration: `notifications` table + `appointments.client_email`.
- `app/models/notification.py`.
- `app/notifications/` package: `providers/{base,log,smtp_stub,esms_stub,zalo_stub}.py`, `templates/*.vi.txt`, `service.py`, `scheduler.py`, `registry.py`.
- Hooks in `app/routers/admin.py` and `app/routers/manager.py`.
- Endpoint `POST /api/admin/notifications/run-dispatcher`.
- Settings + `.env.example` update.
- Frontend: optional email field on `BookingForm` + booking API client type.
- Tests as above.

## Open items deferred to later phases

- Wire real SMTP / eSMS / Zalo ZNS adapters.
- Same-day (1–2h) reminder.
- Booking confirmation notifications.
- Staff UI to view notification history per appointment.
- Localised templates (EN).
- Per-user opt-out flags.
