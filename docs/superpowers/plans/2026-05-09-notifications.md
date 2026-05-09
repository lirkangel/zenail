# Notifications Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship transactional notifications (reminder 24h, canceled, rescheduled) for guests, masters, and managers across email/SMS/Zalo ZNS, with an outbox table and APScheduler-driven dispatcher, while shipping initial providers as no-op `LogProvider` stubs.

**Architecture:** New `app/notifications/` package owns providers, templates, service, and scheduler. Domain events from `app/services/appointment_service.py` (new) write rows to a new `notifications` outbox table. Two APScheduler jobs run inside the FastAPI process: `enqueue_reminders` (every 5 min) and `dispatch_pending` (every 1 min). Tests bypass the scheduler and call functions directly.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, Alembic, Postgres (prod) + SQLite (tests), Pydantic v2, Jinja2 (already a transitive dep through FastAPI), APScheduler 3.x (new dep), Vite + React + TypeScript on the frontend.

**Spec:** `docs/superpowers/specs/2026-05-09-notifications-design.md`. Read it first.

**Conventions used in this plan:**
- Imports at top of files only when shown in code blocks; otherwise add them next to existing imports.
- Each task ends with a commit. Use Conventional Commits (`feat:`, `test:`, `chore:`).
- Run tests from `backend/` with `uv run pytest`. Run frontend lint/build from `frontend/` with `npm run lint` / `npm run build`.
- All UTC datetimes use `datetime.now(timezone.utc)` — never `datetime.utcnow()` (matches existing model defaults that we leave alone).

**Spec note kept verbatim:** the existing enum `AppointmentStatus.canceled` uses one `l`. All new code, table values, template keys, identifiers must use `canceled` to match.

---

## File map

### Created

- `backend/app/models/notification.py` — `Notification` SQLModel + `NotificationKind`, `NotificationRecipientRole`, `NotificationChannel`, `NotificationStatus` enums.
- `backend/alembic/versions/<rev>_notifications_and_client_email.py` — single migration creating `notifications` + adding `appointments.client_email`.
- `backend/app/notifications/__init__.py`
- `backend/app/notifications/providers/__init__.py`
- `backend/app/notifications/providers/base.py` — `NotificationProvider` ABC + `ProviderResult`, `ProviderTransientError`, `ProviderPermanentError`.
- `backend/app/notifications/providers/log.py` — `LogProvider`, the only working provider in phase 1.
- `backend/app/notifications/providers/smtp_stub.py`, `esms_stub.py`, `zalo_stub.py` — classes that raise `NotImplementedError`.
- `backend/app/notifications/registry.py` — channel → provider lookup driven by settings.
- `backend/app/notifications/templates.py` — Jinja loader + `render(template_key, lang, payload)`.
- `backend/app/notifications/templates/{vi}/*.txt` — Vietnamese phase-1 templates (10 files).
- `backend/app/services/notifications.py` — `on_canceled`, `on_rescheduled`, `enqueue_reminder`, recipient resolution, payload builder.
- `backend/app/services/appointment_service.py` — `cancel(appt, session)` and `reschedule(appt, new_start, new_end, session)` helpers that wrap status/time mutations and fire notifications.
- `backend/app/notifications/scheduler.py` — `enqueue_reminders()`, `dispatch_pending()`, plus `start_scheduler(app)` / `stop_scheduler(app)` for lifespan.
- `backend/tests/test_notifications_service.py`
- `backend/tests/test_notifications_scheduler.py`
- `backend/tests/test_appointment_service.py`
- `backend/tests/test_admin_notifications_endpoint.py`

### Modified

- `backend/pyproject.toml` — add `apscheduler` to dependencies.
- `backend/app/core/config.py` — new notification settings.
- `backend/.env.example` — document new env vars.
- `backend/app/models/__init__.py` — export `Notification`.
- `backend/app/models/appointment.py` — add nullable `client_email`.
- `backend/app/schemas/public.py` — `AppointmentCreate` and `AppointmentOut` get `client_email`.
- `backend/app/services/appointment_out.py` — propagate `client_email` if it builds responses (verify during Task 10).
- `backend/app/routers/public.py` — pass `client_email` from `AppointmentCreate` into the `Appointment` row.
- `backend/app/routers/admin.py` — call `appointment_service.cancel/reschedule` from `update_appointment` and `decide_reschedule_request`. Add `POST /api/admin/notifications/run-dispatcher`.
- `backend/app/routers/manager.py` — call `appointment_service.cancel/reschedule` from `update_appointment` and `decide_reschedule_request`.
- `backend/app/main.py` — wire `lifespan` that starts/stops the scheduler when `settings.notifications_enabled`.
- `backend/tests/conftest.py` — set `notifications_enabled=False` env so the scheduler does not start during the FastAPI lifespan.
- `frontend/src/api/types.ts` — add `client_email?: string | null` to the booking create payload type and to `Appointment`.
- `frontend/src/pages/guest/BookConfirmPage.tsx` — add the optional email input.

---

## Task 1: Add APScheduler dependency + new settings (no behavior change)

**Files:**
- Modify: `backend/pyproject.toml`
- Modify: `backend/app/core/config.py`
- Modify: `backend/.env.example`

- [ ] **Step 1: Add the dependency**

In `backend/pyproject.toml`, append `"apscheduler",` to the `dependencies` array (alphabetical order: between `alembic` and `email-validator`). The full block becomes:

```toml
dependencies = [
  "fastapi",
  "uvicorn[standard]",
  "SQLAlchemy",
  "sqlmodel",
  "alembic",
  "apscheduler",
  "psycopg[binary]",
  "python-jose[cryptography]",
  "passlib",
  "pydantic",
  "pydantic-settings",
  "email-validator",
  "python-multipart",
]
```

- [ ] **Step 2: Lock + install**

Run from `backend/`:
```bash
uv sync
```
Expected: APScheduler resolved into the lockfile; no errors.

- [ ] **Step 3: Extend Settings**

Replace the body of `backend/app/core/config.py` with:

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://zenail:zenail@localhost:5432/zenail"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expires_minutes: int = 60 * 24 * 7
    cors_origins: str = "http://localhost:5173"
    currency_code: str = "VND"

    # Notifications
    notifications_enabled: bool = True
    notification_default_lang: str = "vi"
    notification_provider_email: str = "log"   # log | smtp
    notification_provider_sms: str = "log"     # log | esms
    notification_provider_zns: str = "log"     # log | zalo

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_pass: str = ""
    smtp_from: str = "Zenail <noreply@zenail.local>"

    esms_api_key: str = ""
    esms_secret_key: str = ""
    esms_brandname: str = ""

    zalo_oa_access_token: str = ""
    # JSON map: {"reminder_24h.guest.zalo_zns": "<template_id>", ...}
    zalo_zns_template_ids_json: str = "{}"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
```

- [ ] **Step 4: Document env vars**

Append to `backend/.env.example`:

```
# Notifications (phase 1: providers default to no-op log)
NOTIFICATIONS_ENABLED=true
NOTIFICATION_DEFAULT_LANG=vi
NOTIFICATION_PROVIDER_EMAIL=log
NOTIFICATION_PROVIDER_SMS=log
NOTIFICATION_PROVIDER_ZNS=log
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASS=
SMTP_FROM=Zenail <noreply@zenail.local>
ESMS_API_KEY=
ESMS_SECRET_KEY=
ESMS_BRANDNAME=
ZALO_OA_ACCESS_TOKEN=
ZALO_ZNS_TEMPLATE_IDS_JSON={}
```

- [ ] **Step 5: Quick sanity check**

```bash
uv run python -c "from app.core.config import settings; print(settings.notifications_enabled, settings.notification_provider_email)"
```
Expected: `True log`.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/uv.lock backend/app/core/config.py backend/.env.example
git commit -m "chore(notifications): add APScheduler dep and notification settings"
```

---

## Task 2: Notification model + Alembic migration

**Files:**
- Create: `backend/app/models/notification.py`
- Modify: `backend/app/models/appointment.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/<new_rev>_notifications_and_client_email.py`

- [ ] **Step 1: Add `client_email` to the appointment model**

In `backend/app/models/appointment.py`, add the column right after `client_phone` (around line 27):

```python
    client_email: str | None = Field(
        default=None,
        sa_column=Column(String(200), nullable=True),
    )
```

- [ ] **Step 2: Create the notification model**

Write `backend/app/models/notification.py`:

```python
import enum
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlmodel import Field, SQLModel


class NotificationKind(str, enum.Enum):
    reminder_24h = "reminder_24h"
    canceled = "canceled"
    rescheduled = "rescheduled"


class NotificationRecipientRole(str, enum.Enum):
    guest = "guest"
    master = "master"
    manager = "manager"


class NotificationChannel(str, enum.Enum):
    email = "email"
    sms = "sms"
    zalo_zns = "zalo_zns"


class NotificationStatus(str, enum.Enum):
    pending = "pending"
    sent = "sent"
    failed = "failed"
    skipped = "skipped"


class Notification(SQLModel, table=True):
    __tablename__ = "notifications"

    id: int | None = Field(default=None, primary_key=True)

    appointment_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    kind: NotificationKind = Field(
        sa_column=Column(Enum(NotificationKind, name="notification_kind"), nullable=False)
    )
    recipient_role: NotificationRecipientRole = Field(
        sa_column=Column(
            Enum(NotificationRecipientRole, name="notification_recipient_role"),
            nullable=False,
        )
    )
    recipient_address: str = Field(sa_column=Column(String(200), nullable=False))
    channel: NotificationChannel = Field(
        sa_column=Column(Enum(NotificationChannel, name="notification_channel"), nullable=False)
    )
    template_key: str = Field(sa_column=Column(String(64), nullable=False))
    payload_json: dict[str, Any] = Field(
        default_factory=dict,
        sa_column=Column(JSON, nullable=False),
    )
    status: NotificationStatus = Field(
        default=NotificationStatus.pending,
        sa_column=Column(
            Enum(NotificationStatus, name="notification_status"),
            nullable=False,
        ),
    )

    scheduled_at: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False, index=True))
    sent_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    attempt_count: int = Field(default=0, sa_column=Column(Integer, nullable=False))
    last_error: str | None = Field(default=None, sa_column=Column(Text, nullable=True))

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(
            DateTime(timezone=True), nullable=False, onupdate=datetime.utcnow
        ),
    )
```

- [ ] **Step 3: Export from the models package**

In `backend/app/models/__init__.py`, append the import:

```python
from app.models.notification import (  # noqa: F401
    Notification,
    NotificationKind,
    NotificationRecipientRole,
    NotificationChannel,
    NotificationStatus,
)
```

(Only add lines that don't already exist. If the file uses `__all__`, append the new names there too.)

- [ ] **Step 4: Generate the Alembic revision**

From `backend/`:
```bash
uv run alembic revision -m "notifications and client_email"
```
Expected: a new file under `backend/alembic/versions/<rev>_notifications_and_client_email.py`. Replace its body with:

```python
"""notifications and client_email

Revision ID: <auto>
Revises: b2d9f9c4a7a1
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa


revision = "<auto>"
down_revision = "b2d9f9c4a7a1"
branch_labels = None
depends_on = None


notification_kind = sa.Enum(
    "reminder_24h", "canceled", "rescheduled", name="notification_kind"
)
notification_recipient_role = sa.Enum(
    "guest", "master", "manager", name="notification_recipient_role"
)
notification_channel = sa.Enum(
    "email", "sms", "zalo_zns", name="notification_channel"
)
notification_status = sa.Enum(
    "pending", "sent", "failed", "skipped", name="notification_status"
)


def upgrade() -> None:
    op.add_column(
        "appointments",
        sa.Column("client_email", sa.String(length=200), nullable=True),
    )

    notification_kind.create(op.get_bind(), checkfirst=True)
    notification_recipient_role.create(op.get_bind(), checkfirst=True)
    notification_channel.create(op.get_bind(), checkfirst=True)
    notification_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "appointment_id",
            sa.Integer(),
            sa.ForeignKey("appointments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", notification_kind, nullable=False),
        sa.Column("recipient_role", notification_recipient_role, nullable=False),
        sa.Column("recipient_address", sa.String(length=200), nullable=False),
        sa.Column("channel", notification_channel, nullable=False),
        sa.Column("template_key", sa.String(length=64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column(
            "status",
            notification_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_notifications_appointment_id", "notifications", ["appointment_id"]
    )
    op.create_index(
        "ix_notifications_status_scheduled_at",
        "notifications",
        ["status", "scheduled_at"],
    )
    op.create_index(
        "uq_notifications_reminder_idem",
        "notifications",
        ["appointment_id", "recipient_role", "channel"],
        unique=True,
        postgresql_where=sa.text("kind = 'reminder_24h'"),
        sqlite_where=sa.text("kind = 'reminder_24h'"),
    )


def downgrade() -> None:
    op.drop_index("uq_notifications_reminder_idem", table_name="notifications")
    op.drop_index("ix_notifications_status_scheduled_at", table_name="notifications")
    op.drop_index("ix_notifications_appointment_id", table_name="notifications")
    op.drop_table("notifications")
    notification_status.drop(op.get_bind(), checkfirst=True)
    notification_channel.drop(op.get_bind(), checkfirst=True)
    notification_recipient_role.drop(op.get_bind(), checkfirst=True)
    notification_kind.drop(op.get_bind(), checkfirst=True)
    op.drop_column("appointments", "client_email")
```

Replace `<auto>` in the `revision = "<auto>"` line with the actual id Alembic generated in the filename.

- [ ] **Step 5: Run migration up + down to verify**

```bash
uv run alembic upgrade head
uv run alembic downgrade -1
uv run alembic upgrade head
```
Expected: each command exits 0; `notifications` table exists after final upgrade.

- [ ] **Step 6: Add a model-level smoke test**

Create `backend/tests/test_notifications_model.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal

from sqlmodel import Session

from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
)


def _branch(db: Session) -> Branch:
    b = Branch(name="B", timezone="UTC", open_time="08:00", close_time="20:00")
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def test_notification_row_roundtrip(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc),
        price=Decimal("0"),
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    n = Notification(
        appointment_id=appt.id,
        kind=NotificationKind.canceled,
        recipient_role=NotificationRecipientRole.guest,
        recipient_address="0900",
        channel=NotificationChannel.sms,
        template_key="canceled.guest.sms",
        scheduled_at=datetime.now(timezone.utc),
    )
    db_session.add(n)
    db_session.commit()
    db_session.refresh(n)

    assert n.id is not None
    assert n.status == NotificationStatus.pending
    assert n.attempt_count == 0
```

(If `Branch`'s required fields differ from what I wrote, adjust to match `app/models/branch.py`. Run the test first; if it fails on missing fields, fix the fixture, not the production model.)

- [ ] **Step 7: Run the test**

```bash
uv run pytest tests/test_notifications_model.py -v
```
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add backend/app/models/notification.py backend/app/models/__init__.py \
        backend/app/models/appointment.py \
        backend/alembic/versions/*_notifications_and_client_email.py \
        backend/tests/test_notifications_model.py
git commit -m "feat(notifications): add notifications outbox table and client_email column"
```

---

## Task 3: Provider interface, LogProvider, stubs, registry

**Files:**
- Create: `backend/app/notifications/__init__.py` (empty)
- Create: `backend/app/notifications/providers/__init__.py` (empty)
- Create: `backend/app/notifications/providers/base.py`
- Create: `backend/app/notifications/providers/log.py`
- Create: `backend/app/notifications/providers/smtp_stub.py`
- Create: `backend/app/notifications/providers/esms_stub.py`
- Create: `backend/app/notifications/providers/zalo_stub.py`
- Create: `backend/app/notifications/registry.py`

- [ ] **Step 1: Write the provider interface**

`backend/app/notifications/providers/base.py`:

```python
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.models.notification import Notification


class ProviderTransientError(Exception):
    """Retry with backoff."""


class ProviderPermanentError(Exception):
    """Do not retry."""


@dataclass
class ProviderResult:
    ok: bool
    detail: str = ""


class NotificationProvider(ABC):
    @abstractmethod
    async def send(self, notification: Notification, body: str, *, subject: str | None = None) -> ProviderResult: ...
```

- [ ] **Step 2: Write LogProvider**

`backend/app/notifications/providers/log.py`:

```python
from __future__ import annotations

import logging

from app.models.notification import Notification
from app.notifications.providers.base import NotificationProvider, ProviderResult


_logger = logging.getLogger("zenail.notifications")


class LogProvider(NotificationProvider):
    async def send(
        self,
        notification: Notification,
        body: str,
        *,
        subject: str | None = None,
    ) -> ProviderResult:
        _logger.info(
            "notification.log_provider_send id=%s channel=%s template=%s to=%s subject=%r body=%r",
            notification.id,
            notification.channel.value,
            notification.template_key,
            notification.recipient_address,
            subject,
            body,
        )
        return ProviderResult(ok=True, detail="logged")
```

- [ ] **Step 3: Write the three stub providers**

Each in its own file. `smtp_stub.py`:

```python
from app.models.notification import Notification
from app.notifications.providers.base import NotificationProvider, ProviderResult


class SmtpProvider(NotificationProvider):
    async def send(self, notification: Notification, body: str, *, subject: str | None = None) -> ProviderResult:
        raise NotImplementedError("SMTP provider not wired in phase 1")
```

`esms_stub.py` (same shape, class `EsmsProvider`, message `eSMS provider not wired in phase 1`).

`zalo_stub.py` (same shape, class `ZaloZnsProvider`, message `Zalo ZNS provider not wired in phase 1`).

- [ ] **Step 4: Write the registry**

`backend/app/notifications/registry.py`:

```python
from __future__ import annotations

from app.core.config import settings
from app.models.notification import NotificationChannel
from app.notifications.providers.base import NotificationProvider
from app.notifications.providers.esms_stub import EsmsProvider
from app.notifications.providers.log import LogProvider
from app.notifications.providers.smtp_stub import SmtpProvider
from app.notifications.providers.zalo_stub import ZaloZnsProvider


def _build_email_provider() -> NotificationProvider:
    if settings.notification_provider_email == "smtp":
        return SmtpProvider()
    return LogProvider()


def _build_sms_provider() -> NotificationProvider:
    if settings.notification_provider_sms == "esms":
        return EsmsProvider()
    return LogProvider()


def _build_zns_provider() -> NotificationProvider:
    if settings.notification_provider_zns == "zalo":
        return ZaloZnsProvider()
    return LogProvider()


def get_provider(channel: NotificationChannel) -> NotificationProvider:
    if channel == NotificationChannel.email:
        return _build_email_provider()
    if channel == NotificationChannel.sms:
        return _build_sms_provider()
    if channel == NotificationChannel.zalo_zns:
        return _build_zns_provider()
    raise ValueError(f"Unknown channel: {channel}")
```

- [ ] **Step 5: Smoke check the registry**

```bash
uv run python -c "from app.notifications.registry import get_provider; from app.models.notification import NotificationChannel as C; print(type(get_provider(C.email)).__name__)"
```
Expected: `LogProvider` (with default `notification_provider_email=log`).

- [ ] **Step 6: Commit**

```bash
git add backend/app/notifications/
git commit -m "feat(notifications): provider interface, LogProvider, stubs, and registry"
```

---

## Task 4: Templates and renderer

**Files:**
- Create: `backend/app/notifications/templates.py`
- Create: `backend/app/notifications/templates/vi/*.txt` (10 files listed below)

- [ ] **Step 1: Write the renderer**

`backend/app/notifications/templates.py`:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape


_TEMPLATE_DIR = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(str(_TEMPLATE_DIR)),
    autoescape=select_autoescape([]),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)


class TemplateRenderError(Exception):
    pass


def render(template_key: str, lang: str, payload: dict[str, Any]) -> tuple[str | None, str]:
    """Return (subject, body). Email templates put the subject on line 1 and an empty line before the body."""
    template_path = f"{lang}/{template_key}.txt"
    try:
        template = _env.get_template(template_path)
    except Exception as exc:  # jinja2.TemplateNotFound, etc.
        raise TemplateRenderError(f"Missing template: {template_path}") from exc
    rendered = template.render(**payload).strip("\n")
    if "\n\n" in rendered and template_key.endswith(".email"):
        subject, body = rendered.split("\n\n", 1)
        return subject.strip(), body.strip()
    return None, rendered
```

- [ ] **Step 2: Write the 10 templates**

All under `backend/app/notifications/templates/vi/`. Each file uses `{{ var }}` Jinja syntax. Render context provides: `client_name`, `branch_name`, `master_name`, `procedures` (list of strings), `start_local`, `booking_reference`, and for reschedule: `old_start_local`.

`reminder_24h.guest.email.txt`:
```
[Zenail] Nhắc lịch ngày mai

Xin chào {{ client_name }},
Nhắc bạn có lịch hẹn vào {{ start_local }} tại {{ branch_name }} với thợ {{ master_name }}.
Mã đặt lịch: {{ booking_reference }}.
Hẹn gặp bạn!
```

`reminder_24h.guest.sms.txt`:
```
[Zenail] {{ client_name }}, ban co lich {{ start_local }} tai {{ branch_name }} voi {{ master_name }}. Ma: {{ booking_reference }}.
```

`reminder_24h.guest.zalo_zns.txt`:
```
{{ client_name }} có lịch lúc {{ start_local }} tại {{ branch_name }} với {{ master_name }}. Mã: {{ booking_reference }}.
```

`canceled.guest.email.txt`:
```
[Zenail] Lịch hẹn đã huỷ

Xin chào {{ client_name }}, lịch hẹn vào {{ start_local }} tại {{ branch_name }} đã được huỷ.
Mã đặt lịch: {{ booking_reference }}.
Vui lòng đặt lịch mới khi cần.
```

`canceled.guest.sms.txt`:
```
[Zenail] Lich hen {{ start_local }} tai {{ branch_name }} da huy. Ma: {{ booking_reference }}.
```

`canceled.guest.zalo_zns.txt`:
```
Lịch hẹn {{ start_local }} tại {{ branch_name }} đã huỷ. Mã: {{ booking_reference }}.
```

`canceled.master.email.txt`:
```
[Zenail] Lịch khách bị huỷ

Lịch của khách {{ client_name }} ({{ start_local }}) đã huỷ. Mã: {{ booking_reference }}.
```

`canceled.manager.email.txt`:
```
[Zenail] Slot trống

Lịch của {{ client_name }} ({{ start_local }}, thợ {{ master_name }}) đã huỷ. Slot có thể fill.
```

`rescheduled.guest.email.txt`:
```
[Zenail] Lịch hẹn đã dời

Xin chào {{ client_name }}, lịch hẹn của bạn đã được dời từ {{ old_start_local }} sang {{ start_local }} tại {{ branch_name }} với thợ {{ master_name }}.
Mã đặt lịch: {{ booking_reference }}.
```

`rescheduled.guest.sms.txt`:
```
[Zenail] Lich hen doi: {{ old_start_local }} -> {{ start_local }} tai {{ branch_name }}. Ma: {{ booking_reference }}.
```

`rescheduled.guest.zalo_zns.txt`:
```
Lịch hẹn dời từ {{ old_start_local }} sang {{ start_local }} tại {{ branch_name }}. Mã: {{ booking_reference }}.
```

`rescheduled.master.email.txt`:
```
[Zenail] Lịch khách dời

Khách {{ client_name }}: {{ old_start_local }} -> {{ start_local }}. Mã: {{ booking_reference }}.
```

- [ ] **Step 3: Test the renderer**

Append to a new `backend/tests/test_notifications_templates.py`:

```python
from app.notifications.templates import render


def test_email_template_splits_subject_and_body():
    subject, body = render(
        "reminder_24h.guest.email",
        "vi",
        {
            "client_name": "An",
            "branch_name": "Zenail Central",
            "master_name": "Linh",
            "procedures": ["Manicure"],
            "start_local": "10:00 09/05/2026",
            "booking_reference": "ABC123",
        },
    )
    assert subject == "[Zenail] Nhắc lịch ngày mai"
    assert "An" in body
    assert "ABC123" in body


def test_sms_template_returns_no_subject():
    subject, body = render(
        "reminder_24h.guest.sms",
        "vi",
        {
            "client_name": "An",
            "branch_name": "Zenail Central",
            "master_name": "Linh",
            "procedures": ["Manicure"],
            "start_local": "10:00 09/05/2026",
            "booking_reference": "ABC123",
        },
    )
    assert subject is None
    assert "ABC123" in body
```

- [ ] **Step 4: Run**

```bash
uv run pytest tests/test_notifications_templates.py -v
```
Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add backend/app/notifications/templates.py backend/app/notifications/templates/ \
        backend/tests/test_notifications_templates.py
git commit -m "feat(notifications): add VI templates and Jinja renderer"
```

---

## Task 5: NotificationService — recipient resolution + outbox writes

**Files:**
- Create: `backend/app/services/notifications.py`
- Create: `backend/tests/test_notifications_service.py`

- [ ] **Step 1: Write the failing test for `on_canceled` row counts**

`backend/tests/test_notifications_service.py`:

```python
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

import pytest
from sqlmodel import Session, select

from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
    Procedure,
    Staff,
)
from app.models.enums import StaffRole
from app.services import notifications as notif_service


def _seed(db: Session, *, client_email: str | None = None, with_manager: bool = True) -> Appointment:
    branch = Branch(
        name="Zenail Central",
        timezone="Asia/Ho_Chi_Minh",
        open_time=time(8, 0),
        close_time=time(20, 0),
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)

    master = Staff(
        full_name="Linh",
        email="linh@zenail.local",
        password_hash="x",
        role=StaffRole.master,
        branch_id=branch.id,
    )
    db.add(master)
    if with_manager:
        db.add(
            Staff(
                full_name="Mgr",
                email="mgr@zenail.local",
                password_hash="x",
                role=StaffRole.manager,
                branch_id=branch.id,
            )
        )
    db.commit()
    db.refresh(master)

    proc = Procedure(name="Manicure", duration_minutes=60, price=Decimal("100000"))
    db.add(proc)
    db.commit()
    db.refresh(proc)

    appt = Appointment(
        branch_id=branch.id,
        master_id=master.id,
        procedure_id=proc.id,
        client_name="An",
        client_phone="0900000000",
        client_email=client_email,
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
        price=Decimal("100000"),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def test_on_canceled_with_email_creates_full_row_set(db_session: Session) -> None:
    appt = _seed(db_session, client_email="an@example.com")
    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(select(Notification)).all()
    by_role = {(r.recipient_role, r.channel) for r in rows}
    assert (NotificationRecipientRole.guest, NotificationChannel.email) in by_role
    assert (NotificationRecipientRole.guest, NotificationChannel.sms) in by_role
    assert (NotificationRecipientRole.guest, NotificationChannel.zalo_zns) in by_role
    assert (NotificationRecipientRole.master, NotificationChannel.email) in by_role
    assert (NotificationRecipientRole.manager, NotificationChannel.email) in by_role
    # All rows are pending and tied to the appointment.
    assert {r.kind for r in rows} == {NotificationKind.canceled}
    assert all(r.status == NotificationStatus.pending for r in rows)


def test_on_canceled_without_email_skips_guest_email(db_session: Session) -> None:
    appt = _seed(db_session, client_email=None)
    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(
        select(Notification).where(
            Notification.recipient_role == NotificationRecipientRole.guest,
            Notification.channel == NotificationChannel.email,
        )
    ).all()
    assert len(rows) == 1
    assert rows[0].status == NotificationStatus.skipped
    assert "no email" in (rows[0].last_error or "")


def test_on_canceled_without_manager_writes_no_manager_row(db_session: Session) -> None:
    appt = _seed(db_session, client_email="an@example.com", with_manager=False)
    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(
        select(Notification).where(Notification.recipient_role == NotificationRecipientRole.manager)
    ).all()
    assert rows == []


def test_on_canceled_marks_existing_pending_as_skipped(db_session: Session) -> None:
    appt = _seed(db_session, client_email="an@example.com")
    # Pre-existing reminder pending row.
    notif_service.enqueue_reminder(appt, db_session)
    db_session.commit()

    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    reminder_rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert reminder_rows
    assert all(r.status == NotificationStatus.skipped for r in reminder_rows)
```

- [ ] **Step 2: Run — expect failures**

```bash
uv run pytest tests/test_notifications_service.py -v
```
Expected: import error (`notif_service`) or attribute error.

- [ ] **Step 3: Implement the service**

`backend/app/services/notifications.py`:

```python
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select as sa_select
from sqlmodel import Session

from app.core.config import settings
from app.models.appointment import Appointment
from app.models.appointment_procedure import AppointmentProcedure
from app.models.branch import Branch
from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
)
from app.models.enums import StaffRole
from app.models.procedure import Procedure
from app.models.staff import Staff


UTC = timezone.utc

# Channel mapping per recipient role per kind.
_CHANNELS: dict[
    tuple[NotificationKind, NotificationRecipientRole], list[NotificationChannel]
] = {
    (NotificationKind.reminder_24h, NotificationRecipientRole.guest): [
        NotificationChannel.email,
        NotificationChannel.sms,
        NotificationChannel.zalo_zns,
    ],
    (NotificationKind.canceled, NotificationRecipientRole.guest): [
        NotificationChannel.email,
        NotificationChannel.sms,
        NotificationChannel.zalo_zns,
    ],
    (NotificationKind.canceled, NotificationRecipientRole.master): [NotificationChannel.email],
    (NotificationKind.canceled, NotificationRecipientRole.manager): [NotificationChannel.email],
    (NotificationKind.rescheduled, NotificationRecipientRole.guest): [
        NotificationChannel.email,
        NotificationChannel.sms,
        NotificationChannel.zalo_zns,
    ],
    (NotificationKind.rescheduled, NotificationRecipientRole.master): [NotificationChannel.email],
}


def _format_local(dt: datetime, branch: Branch) -> str:
    from zoneinfo import ZoneInfo

    return dt.astimezone(ZoneInfo(branch.timezone)).strftime("%H:%M %d/%m/%Y")


def _build_payload(
    *,
    appointment: Appointment,
    branch: Branch,
    master: Staff,
    procedures: list[str],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "client_name": appointment.client_name,
        "branch_name": branch.name,
        "master_name": master.full_name if master else "",
        "procedures": procedures,
        "start_local": _format_local(appointment.start_time, branch),
        "booking_reference": appointment.booking_reference,
    }
    if extra:
        payload.update(extra)
    return payload


def _resolve_guest_address(channel: NotificationChannel, appt: Appointment) -> str | None:
    if channel == NotificationChannel.email:
        return appt.client_email or None
    return appt.client_phone or None


def _resolve_master_address(master: Staff | None) -> str | None:
    return master.email if master and master.email else None


def _resolve_managers(session: Session, branch_id: int) -> list[Staff]:
    return list(
        session.scalars(
            sa_select(Staff).where(
                Staff.role == StaffRole.manager,
                Staff.branch_id == branch_id,
                Staff.is_active.is_(True),
            )
        ).all()
    )


def _load_context(session: Session, appt: Appointment) -> tuple[Branch, Staff, list[str]]:
    branch = session.get(Branch, appt.branch_id)
    master = session.get(Staff, appt.master_id)
    procedure_names: list[str] = []
    rows = session.scalars(
        sa_select(AppointmentProcedure).where(AppointmentProcedure.appointment_id == appt.id)
    ).all()
    for r in rows:
        if r.name_snapshot:
            procedure_names.append(r.name_snapshot)
    if not procedure_names and appt.procedure_id:
        proc = session.get(Procedure, appt.procedure_id)
        if proc:
            procedure_names = [proc.name]
    return branch, master, procedure_names


def _insert_row(
    session: Session,
    *,
    appt: Appointment,
    kind: NotificationKind,
    role: NotificationRecipientRole,
    channel: NotificationChannel,
    address: str | None,
    payload: dict[str, Any],
    scheduled_at: datetime,
) -> Notification:
    template_key = f"{kind.value}.{role.value}.{channel.value}"
    if not address:
        n = Notification(
            appointment_id=appt.id,
            kind=kind,
            recipient_role=role,
            recipient_address="",
            channel=channel,
            template_key=template_key,
            payload_json=payload,
            status=NotificationStatus.skipped,
            scheduled_at=scheduled_at,
            last_error=f"no {channel.value} address available",
        )
    else:
        n = Notification(
            appointment_id=appt.id,
            kind=kind,
            recipient_role=role,
            recipient_address=address,
            channel=channel,
            template_key=template_key,
            payload_json=payload,
            status=NotificationStatus.pending,
            scheduled_at=scheduled_at,
        )
    session.add(n)
    return n


def _supersede_pending(session: Session, appointment_id: int, reason: str) -> None:
    pending = session.scalars(
        sa_select(Notification).where(
            Notification.appointment_id == appointment_id,
            Notification.status == NotificationStatus.pending,
        )
    ).all()
    for row in pending:
        row.status = NotificationStatus.skipped
        row.last_error = reason
        session.add(row)


def on_canceled(appointment: Appointment, session: Session) -> list[Notification]:
    branch, master, procedures = _load_context(session, appointment)
    payload = _build_payload(
        appointment=appointment, branch=branch, master=master, procedures=procedures
    )
    _supersede_pending(session, appointment.id, "superseded by cancel")

    now = datetime.now(UTC)
    out: list[Notification] = []

    for channel in _CHANNELS[(NotificationKind.canceled, NotificationRecipientRole.guest)]:
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.canceled,
                role=NotificationRecipientRole.guest,
                channel=channel,
                address=_resolve_guest_address(channel, appointment),
                payload=payload,
                scheduled_at=now,
            )
        )

    out.append(
        _insert_row(
            session,
            appt=appointment,
            kind=NotificationKind.canceled,
            role=NotificationRecipientRole.master,
            channel=NotificationChannel.email,
            address=_resolve_master_address(master),
            payload=payload,
            scheduled_at=now,
        )
    )

    for mgr in _resolve_managers(session, appointment.branch_id):
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.canceled,
                role=NotificationRecipientRole.manager,
                channel=NotificationChannel.email,
                address=mgr.email,
                payload=payload,
                scheduled_at=now,
            )
        )
    return out


def on_rescheduled(
    appointment: Appointment, old_start: datetime, session: Session
) -> list[Notification]:
    branch, master, procedures = _load_context(session, appointment)
    extra = {"old_start_local": _format_local(old_start, branch)}
    payload = _build_payload(
        appointment=appointment, branch=branch, master=master, procedures=procedures, extra=extra
    )

    # Drop pending reminder rows; will be re-created.
    pending_reminders = session.scalars(
        sa_select(Notification).where(
            Notification.appointment_id == appointment.id,
            Notification.kind == NotificationKind.reminder_24h,
            Notification.status == NotificationStatus.pending,
        )
    ).all()
    for row in pending_reminders:
        session.delete(row)

    # Skip pending rescheduled rows so the newest data wins.
    pending_resched = session.scalars(
        sa_select(Notification).where(
            Notification.appointment_id == appointment.id,
            Notification.kind == NotificationKind.rescheduled,
            Notification.status == NotificationStatus.pending,
        )
    ).all()
    for row in pending_resched:
        row.status = NotificationStatus.skipped
        row.last_error = "superseded by newer reschedule"

    now = datetime.now(UTC)
    out: list[Notification] = []

    for channel in _CHANNELS[(NotificationKind.rescheduled, NotificationRecipientRole.guest)]:
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.rescheduled,
                role=NotificationRecipientRole.guest,
                channel=channel,
                address=_resolve_guest_address(channel, appointment),
                payload=payload,
                scheduled_at=now,
            )
        )

    out.append(
        _insert_row(
            session,
            appt=appointment,
            kind=NotificationKind.rescheduled,
            role=NotificationRecipientRole.master,
            channel=NotificationChannel.email,
            address=_resolve_master_address(master),
            payload=payload,
            scheduled_at=now,
        )
    )

    out.extend(enqueue_reminder(appointment, session))
    return out


def enqueue_reminder(appointment: Appointment, session: Session) -> list[Notification]:
    branch, master, procedures = _load_context(session, appointment)
    payload = _build_payload(
        appointment=appointment, branch=branch, master=master, procedures=procedures
    )
    target = appointment.start_time - timedelta(hours=24)
    now = datetime.now(UTC)
    scheduled_at = max(target, now)

    out: list[Notification] = []
    for channel in _CHANNELS[(NotificationKind.reminder_24h, NotificationRecipientRole.guest)]:
        out.append(
            _insert_row(
                session,
                appt=appointment,
                kind=NotificationKind.reminder_24h,
                role=NotificationRecipientRole.guest,
                channel=channel,
                address=_resolve_guest_address(channel, appointment),
                payload=payload,
                scheduled_at=scheduled_at,
            )
        )
    return out
```

- [ ] **Step 4: Run the canceled tests**

```bash
uv run pytest tests/test_notifications_service.py -v
```
Expected: all four `on_canceled` tests PASS.

- [ ] **Step 5: Add reschedule + reminder unit tests**

Append to `backend/tests/test_notifications_service.py`:

```python
def test_on_rescheduled_replaces_pending_reminder(db_session: Session) -> None:
    appt = _seed(db_session, client_email="an@example.com")
    notif_service.enqueue_reminder(appt, db_session)
    db_session.commit()

    old_start = appt.start_time
    appt.start_time = appt.start_time + timedelta(days=1)
    appt.end_time = appt.end_time + timedelta(days=1)
    db_session.add(appt)
    db_session.commit()

    notif_service.on_rescheduled(appt, old_start, db_session)
    db_session.commit()

    reminders = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    # Old pending rows deleted; new ones inserted.
    assert all(r.status == NotificationStatus.pending for r in reminders)
    expected_scheduled = appt.start_time - timedelta(hours=24)
    for r in reminders:
        assert abs((r.scheduled_at - expected_scheduled).total_seconds()) < 5


def test_on_rescheduled_within_24h_schedules_now(db_session: Session) -> None:
    appt = _seed(db_session, client_email="an@example.com")
    appt.start_time = datetime.now(timezone.utc) + timedelta(hours=2)
    appt.end_time = appt.start_time + timedelta(hours=1)
    db_session.add(appt)
    db_session.commit()

    old_start = appt.start_time + timedelta(hours=1)
    notif_service.on_rescheduled(appt, old_start, db_session)
    db_session.commit()

    reminders = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert reminders
    now = datetime.now(timezone.utc)
    for r in reminders:
        assert r.scheduled_at <= now + timedelta(seconds=5)


def test_master_without_email_is_skipped(db_session: Session) -> None:
    appt = _seed(db_session, client_email="an@example.com")
    master = db_session.get(Staff, appt.master_id)
    master.email = ""  # defensive — schema requires email but exercise the branch
    db_session.add(master)
    db_session.commit()

    notif_service.on_canceled(appt, db_session)
    db_session.commit()

    rows = db_session.exec(
        select(Notification).where(Notification.recipient_role == NotificationRecipientRole.master)
    ).all()
    assert len(rows) == 1
    assert rows[0].status == NotificationStatus.skipped
```

- [ ] **Step 6: Run all service tests**

```bash
uv run pytest tests/test_notifications_service.py -v
```
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/notifications.py backend/tests/test_notifications_service.py
git commit -m "feat(notifications): NotificationService with recipient resolution and outbox writes"
```

---

## Task 6: Dispatcher (`dispatch_pending`)

**Files:**
- Create: `backend/app/notifications/scheduler.py` (will grow in Task 7 and Task 8)
- Modify: `backend/tests/test_notifications_scheduler.py` (created here)

- [ ] **Step 1: Write failing dispatcher tests**

`backend/tests/test_notifications_scheduler.py`:

```python
import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from time import time as _time

import pytest
from sqlmodel import Session, select

from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
)
from app.notifications import scheduler as sched
from app.notifications.providers.base import (
    NotificationProvider,
    ProviderPermanentError,
    ProviderResult,
    ProviderTransientError,
)


class _OkProvider(NotificationProvider):
    async def send(self, notification, body, *, subject=None):
        return ProviderResult(ok=True)


class _TransientProvider(NotificationProvider):
    async def send(self, notification, body, *, subject=None):
        raise ProviderTransientError("boom")


class _PermanentProvider(NotificationProvider):
    async def send(self, notification, body, *, subject=None):
        raise ProviderPermanentError("dead")


def _branch(db: Session) -> Branch:
    from datetime import time

    b = Branch(name="B", timezone="UTC", open_time=time(8, 0), close_time=time(20, 0))
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


def _make_pending(db: Session, *, scheduled_at: datetime) -> Notification:
    branch = _branch(db)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
        price=Decimal("0"),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    n = Notification(
        appointment_id=appt.id,
        kind=NotificationKind.canceled,
        recipient_role=NotificationRecipientRole.guest,
        recipient_address="x@example.com",
        channel=NotificationChannel.email,
        template_key="canceled.guest.email",
        payload_json={
            "client_name": "A",
            "branch_name": "B",
            "master_name": "M",
            "procedures": [],
            "start_local": "now",
            "booking_reference": "REF",
        },
        scheduled_at=scheduled_at,
    )
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


def test_dispatcher_marks_sent_on_success(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _OkProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.sent
    assert n.sent_at is not None


def test_dispatcher_skips_future_rows(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) + timedelta(hours=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _OkProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.pending


def test_dispatcher_transient_error_increments_attempt(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _TransientProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.pending
    assert n.attempt_count == 1
    assert n.scheduled_at > datetime.now(timezone.utc)
    assert "boom" in (n.last_error or "")


def test_dispatcher_permanent_error_marks_failed(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _PermanentProvider())

    asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.failed
    assert n.attempt_count == 1


def test_dispatcher_three_transient_failures_marks_failed(db_session: Session, monkeypatch) -> None:
    n = _make_pending(db_session, scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=1))
    monkeypatch.setattr(sched, "get_provider", lambda channel: _TransientProvider())

    for _ in range(3):
        # Force the row's scheduled_at into the past on each cycle so the dispatcher picks it up.
        db_session.refresh(n)
        n.scheduled_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db_session.add(n)
        db_session.commit()
        asyncio.run(sched.dispatch_pending(session_factory=lambda: db_session))

    db_session.refresh(n)
    assert n.status == NotificationStatus.failed
    assert n.attempt_count == 3
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_notifications_scheduler.py -v
```
Expected: import error (`app.notifications.scheduler` does not exist).

- [ ] **Step 3: Implement the dispatcher**

`backend/app/notifications/scheduler.py`:

```python
from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Iterable

from sqlalchemy import text
from sqlmodel import Session, select

from app.db.sqlmodel import session_scope
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.notification import (
    Notification,
    NotificationKind,
    NotificationStatus,
)
from app.notifications.providers.base import (
    ProviderPermanentError,
    ProviderTransientError,
)
from app.notifications.registry import get_provider
from app.notifications.templates import render
from app.core.config import settings


_logger = logging.getLogger("zenail.notifications")
UTC = timezone.utc

_BACKOFF = [timedelta(minutes=1), timedelta(minutes=5), timedelta(minutes=15)]
_MAX_ATTEMPTS = 3
_BATCH = 100


SessionFactory = Callable[[], Session]


def _is_postgres(session: Session) -> bool:
    try:
        return session.bind.dialect.name == "postgresql"
    except AttributeError:
        return False


def _select_pending(session: Session) -> list[Notification]:
    now = datetime.now(UTC)
    stmt = (
        select(Notification)
        .where(
            Notification.status == NotificationStatus.pending,
            Notification.scheduled_at <= now,
            Notification.attempt_count < _MAX_ATTEMPTS,
        )
        .order_by(Notification.scheduled_at)
        .limit(_BATCH)
    )
    if _is_postgres(session):
        stmt = stmt.with_for_update(skip_locked=True)
    return list(session.scalars(stmt).all())


async def dispatch_pending(*, session_factory: SessionFactory | None = None) -> dict:
    factory = session_factory or session_scope
    counts = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}
    own_session = session_factory is None

    if own_session:
        with factory() as session:  # type: ignore[misc]
            counts.update(await _dispatch_with_session(session))
    else:
        session = factory()
        counts.update(await _dispatch_with_session(session))
    return counts


async def _dispatch_with_session(session: Session) -> dict:
    counts = {"processed": 0, "sent": 0, "failed": 0, "skipped": 0}
    rows = _select_pending(session)
    for row in rows:
        counts["processed"] += 1
        try:
            subject, body = render(row.template_key, settings.notification_default_lang, row.payload_json)
        except Exception as exc:
            row.status = NotificationStatus.failed
            row.last_error = f"template error: {exc}"
            row.attempt_count += 1
            session.add(row)
            counts["failed"] += 1
            session.commit()
            continue

        provider = get_provider(row.channel)
        try:
            result = await provider.send(row, body, subject=subject)
            if result.ok:
                row.status = NotificationStatus.sent
                row.sent_at = datetime.now(UTC)
                row.attempt_count += 1
                counts["sent"] += 1
            else:
                _apply_transient(row)
                row.last_error = result.detail or "provider returned not-ok"
        except ProviderPermanentError as exc:
            row.status = NotificationStatus.failed
            row.attempt_count += 1
            row.last_error = str(exc)
            counts["failed"] += 1
        except ProviderTransientError as exc:
            _apply_transient(row)
            row.last_error = str(exc)
            if row.status == NotificationStatus.failed:
                counts["failed"] += 1
        except Exception as exc:  # treat unknown as transient
            _apply_transient(row)
            row.last_error = f"unexpected: {exc}"
            if row.status == NotificationStatus.failed:
                counts["failed"] += 1

        session.add(row)
        session.commit()

        _logger.info(
            "notification.dispatched id=%s kind=%s channel=%s status=%s attempt=%s error=%s",
            row.id, row.kind.value, row.channel.value, row.status.value,
            row.attempt_count, row.last_error,
        )
    return counts


def _apply_transient(row: Notification) -> None:
    row.attempt_count += 1
    if row.attempt_count >= _MAX_ATTEMPTS:
        row.status = NotificationStatus.failed
    else:
        # backoff index = attempts already made (0-based)
        delay = _BACKOFF[min(row.attempt_count - 1, len(_BACKOFF) - 1)]
        row.scheduled_at = datetime.now(UTC) + delay
        row.status = NotificationStatus.pending
```

- [ ] **Step 4: Confirm `app.db.sqlmodel.session_scope` exists**

If the project has `get_db` only and no `session_scope`, add a small contextmanager next to `get_db` in `backend/app/db/sqlmodel.py`:

```python
from contextlib import contextmanager
from collections.abc import Iterator

@contextmanager
def session_scope() -> Iterator[Session]:
    with Session(engine) as session:
        yield session
```

(Keep the existing `get_db` generator untouched.)

- [ ] **Step 5: Run dispatcher tests**

```bash
uv run pytest tests/test_notifications_scheduler.py -v
```
Expected: all 5 tests PASS. If `_TransientProvider` test fails because the dispatcher commits the session and `db_session` is the same Session as the test holds, you may need to `session.expire_all()` after `dispatch_pending`. Add that inside the test if needed.

- [ ] **Step 6: Commit**

```bash
git add backend/app/notifications/scheduler.py \
        backend/app/db/sqlmodel.py \
        backend/tests/test_notifications_scheduler.py
git commit -m "feat(notifications): outbox dispatcher with retry/backoff"
```

---

## Task 7: Reminder enqueuer

**Files:**
- Modify: `backend/app/notifications/scheduler.py`
- Modify: `backend/tests/test_notifications_scheduler.py`

- [ ] **Step 1: Write the failing reminder tests**

Append to `backend/tests/test_notifications_scheduler.py`:

```python
def test_enqueue_reminders_creates_rows_inside_window(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        client_email="a@example.com",
        start_time=datetime.now(timezone.utc) + timedelta(hours=23, minutes=30),
        end_time=datetime.now(timezone.utc) + timedelta(hours=24, minutes=30),
        price=Decimal("0"),
    )
    db_session.add(appt)
    db_session.commit()
    db_session.refresh(appt)

    sched.enqueue_reminders(session_factory=lambda: db_session)

    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert len(rows) == 3  # email + sms + zns


def test_enqueue_reminders_idempotent(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        client_email="a@example.com",
        start_time=datetime.now(timezone.utc) + timedelta(hours=23, minutes=30),
        end_time=datetime.now(timezone.utc) + timedelta(hours=24, minutes=30),
        price=Decimal("0"),
    )
    db_session.add(appt)
    db_session.commit()

    sched.enqueue_reminders(session_factory=lambda: db_session)
    sched.enqueue_reminders(session_factory=lambda: db_session)

    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.reminder_24h)
    ).all()
    assert len(rows) == 3


def test_enqueue_reminders_skips_canceled_appointment(db_session: Session) -> None:
    branch = _branch(db_session)
    appt = Appointment(
        branch_id=branch.id,
        master_id=1,
        procedure_id=1,
        client_name="A",
        client_phone="0900",
        start_time=datetime.now(timezone.utc) + timedelta(hours=23, minutes=30),
        end_time=datetime.now(timezone.utc) + timedelta(hours=24, minutes=30),
        price=Decimal("0"),
        status=AppointmentStatus.canceled,
    )
    db_session.add(appt)
    db_session.commit()

    sched.enqueue_reminders(session_factory=lambda: db_session)

    rows = db_session.exec(select(Notification)).all()
    assert rows == []
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_notifications_scheduler.py::test_enqueue_reminders_creates_rows_inside_window -v
```
Expected: AttributeError on `sched.enqueue_reminders`.

- [ ] **Step 3: Implement `enqueue_reminders`**

Append to `backend/app/notifications/scheduler.py`:

```python
def enqueue_reminders(*, session_factory: SessionFactory | None = None) -> int:
    factory = session_factory or session_scope
    if session_factory is None:
        with factory() as session:  # type: ignore[misc]
            return _enqueue_with_session(session)
    return _enqueue_with_session(factory())


def _enqueue_with_session(session: Session) -> int:
    from app.services.notifications import enqueue_reminder

    now = datetime.now(UTC)
    window_start = now + timedelta(hours=23)
    window_end = now + timedelta(hours=24)

    appt_stmt = (
        select(Appointment)
        .where(
            Appointment.status == AppointmentStatus.scheduled,
            Appointment.start_time >= window_start,
            Appointment.start_time <= window_end,
        )
    )
    candidates = list(session.scalars(appt_stmt).all())

    inserted = 0
    for appt in candidates:
        existing = session.scalar(
            select(Notification).where(
                Notification.appointment_id == appt.id,
                Notification.kind == NotificationKind.reminder_24h,
            )
        )
        if existing is not None:
            continue
        rows = enqueue_reminder(appt, session)
        inserted += len(rows)
    session.commit()
    return inserted
```

- [ ] **Step 4: Run reminder tests**

```bash
uv run pytest tests/test_notifications_scheduler.py -v -k reminder
```
Expected: 3 PASS.

- [ ] **Step 5: Run the whole scheduler test file**

```bash
uv run pytest tests/test_notifications_scheduler.py -v
```
Expected: all PASS (8 tests total).

- [ ] **Step 6: Commit**

```bash
git add backend/app/notifications/scheduler.py backend/tests/test_notifications_scheduler.py
git commit -m "feat(notifications): reminder enqueuer with idempotency window"
```

---

## Task 8: Wire scheduler into FastAPI lifespan

**Files:**
- Modify: `backend/app/main.py`
- Modify: `backend/app/notifications/scheduler.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add `start_scheduler` / `stop_scheduler`**

Append to `backend/app/notifications/scheduler.py`:

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler


_scheduler: AsyncIOScheduler | None = None


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    s = AsyncIOScheduler(timezone="UTC")

    async def _enqueue_job() -> None:
        try:
            enqueue_reminders()
        except Exception:
            _logger.exception("enqueue_reminders failed")

    async def _dispatch_job() -> None:
        try:
            await dispatch_pending()
        except Exception:
            _logger.exception("dispatch_pending failed")

    s.add_job(_enqueue_job, "interval", minutes=5, id="enqueue_reminders")
    s.add_job(_dispatch_job, "interval", minutes=1, id="dispatch_pending")
    s.start()
    _scheduler = s


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is None:
        return
    _scheduler.shutdown(wait=False)
    _scheduler = None
```

- [ ] **Step 2: Convert `main.py` to use a lifespan**

Replace `backend/app/main.py` with:

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.notifications.scheduler import start_scheduler, stop_scheduler
from app.routers import admin, auth, manager, master, public


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.notifications_enabled:
        start_scheduler()
    try:
        yield
    finally:
        if settings.notifications_enabled:
            stop_scheduler()


app = FastAPI(title="Zenail CRM API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(public.router, prefix="/api")
app.include_router(master.router, prefix="/api")
app.include_router(manager.router, prefix="/api")
app.include_router(admin.router, prefix="/api")


@app.get("/health")
def health() -> dict:
    return {"ok": True}
```

- [ ] **Step 3: Disable scheduler during tests**

In `backend/tests/conftest.py`, before importing `app`, override settings. Add at the top of the file (above the `from app.main import app` line — move that import below):

```python
import os

os.environ["NOTIFICATIONS_ENABLED"] = "false"
```

If conftest already imports `app` at module top, restructure so the env var is set first.

- [ ] **Step 4: Run all backend tests**

```bash
uv run pytest -v
```
Expected: all green. The scheduler logs should NOT appear in test output (because `notifications_enabled=False`).

- [ ] **Step 5: Manual smoke**

```bash
uv run uvicorn app.main:app --reload
```
Expected: log line `notification.log_provider_send …` does NOT appear (no rows yet); no APScheduler errors. Stop with Ctrl+C; expected: clean shutdown.

- [ ] **Step 6: Commit**

```bash
git add backend/app/main.py backend/app/notifications/scheduler.py backend/tests/conftest.py
git commit -m "feat(notifications): start scheduler in FastAPI lifespan, disable in tests"
```

---

## Task 9: Centralize cancel/reschedule and wire into the four router sites

**Files:**
- Create: `backend/app/services/appointment_service.py`
- Modify: `backend/app/routers/admin.py`
- Modify: `backend/app/routers/manager.py`
- Create: `backend/tests/test_appointment_service.py`

- [ ] **Step 1: Write failing tests for the service helpers**

`backend/tests/test_appointment_service.py`:

```python
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationKind,
    Procedure,
    Staff,
)
from app.models.enums import AppointmentStatus, StaffRole
from app.services import appointment_service


def _seed(db: Session) -> Appointment:
    branch = Branch(
        name="B", timezone="Asia/Ho_Chi_Minh", open_time=time(8, 0), close_time=time(20, 0)
    )
    db.add(branch)
    db.commit()
    db.refresh(branch)

    master = Staff(
        full_name="Linh", email="linh@x", password_hash="x",
        role=StaffRole.master, branch_id=branch.id,
    )
    db.add(master)
    proc = Procedure(name="Manicure", duration_minutes=60, price=Decimal("100000"))
    db.add(proc)
    db.commit()
    db.refresh(master)
    db.refresh(proc)

    appt = Appointment(
        branch_id=branch.id, master_id=master.id, procedure_id=proc.id,
        client_name="A", client_phone="0900", client_email="a@example.com",
        start_time=datetime.now(timezone.utc) + timedelta(days=2),
        end_time=datetime.now(timezone.utc) + timedelta(days=2, hours=1),
        price=Decimal("100000"),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def test_cancel_sets_status_and_emits_notifications(db_session: Session) -> None:
    appt = _seed(db_session)
    appointment_service.cancel(appt, db_session)
    db_session.commit()

    db_session.refresh(appt)
    assert appt.status == AppointmentStatus.canceled
    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.canceled)
    ).all()
    assert rows


def test_reschedule_sets_times_and_emits_notifications(db_session: Session) -> None:
    appt = _seed(db_session)
    old_start = appt.start_time
    new_start = old_start + timedelta(days=1)
    new_end = appt.end_time + timedelta(days=1)

    appointment_service.reschedule(appt, new_start=new_start, new_end=new_end, session=db_session)
    db_session.commit()

    db_session.refresh(appt)
    assert appt.start_time == new_start
    rows = db_session.exec(
        select(Notification).where(Notification.kind == NotificationKind.rescheduled)
    ).all()
    assert rows
```

- [ ] **Step 2: Run — expect failure**

```bash
uv run pytest tests/test_appointment_service.py -v
```
Expected: import error.

- [ ] **Step 3: Implement the service helpers**

`backend/app/services/appointment_service.py`:

```python
from __future__ import annotations

from datetime import datetime

from sqlmodel import Session

from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.services import notifications as notif_service


def cancel(appointment: Appointment, session: Session) -> None:
    if appointment.status != AppointmentStatus.canceled:
        appointment.status = AppointmentStatus.canceled
        session.add(appointment)
    notif_service.on_canceled(appointment, session)


def reschedule(
    appointment: Appointment,
    *,
    new_start: datetime,
    new_end: datetime,
    session: Session,
) -> None:
    old_start = appointment.start_time
    appointment.start_time = new_start
    appointment.end_time = new_end
    session.add(appointment)
    notif_service.on_rescheduled(appointment, old_start, session)
```

- [ ] **Step 4: Run service tests**

```bash
uv run pytest tests/test_appointment_service.py -v
```
Expected: 2 PASS.

- [ ] **Step 5: Wire `admin.update_appointment`**

Replace the body of `update_appointment` in `backend/app/routers/admin.py` (the function spanning roughly lines 79–115) with:

```python
@router.patch("/admin/appointments/{appointment_id}", response_model=AppointmentOut)
def update_appointment(
    appointment_id: int,
    payload: AppointmentUpdate,
    db: Session = Depends(get_db),
    _: Staff = Depends(require_admin),
) -> AppointmentOut:
    appt = db.get(Appointment, appointment_id)
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    will_cancel = (
        payload.status is not None
        and payload.status == AppointmentStatus.canceled
        and appt.status != AppointmentStatus.canceled
    )

    if payload.status is not None and not will_cancel:
        appt.status = payload.status

    new_times: tuple[datetime, datetime] | None = None
    if payload.start_time is not None:
        branch = db.get(Branch, appt.branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        new_start, new_end = appointment_start_end(
            branch=branch,
            start_value=payload.start_time,
            duration_minutes=appointment_duration_minutes(appt),
        )
        ensure_no_conflict(
            db,
            master_id=appt.master_id,
            start_utc=new_start,
            end_utc=new_end,
            exclude_appointment_id=appt.id,
        )
        new_times = (new_start, new_end)

    if new_times is not None:
        appointment_service.reschedule(
            appt, new_start=new_times[0], new_end=new_times[1], session=db
        )

    if will_cancel:
        appointment_service.cancel(appt, db)

    db.commit()
    db.refresh(appt)
    return appointment_to_out(appt)
```

Add the import near the other `app.services` imports:

```python
from app.services import appointment_service
```

(`AppointmentStatus` and `datetime` are already imported in this file.)

- [ ] **Step 6: Wire `admin.decide_reschedule_request`**

In `backend/app/routers/admin.py`, replace the inner `if payload.status == RescheduleRequestStatus.approved:` block (around lines 213–230) with:

```python
    if payload.status == RescheduleRequestStatus.approved:
        branch = db.get(Branch, appt.branch_id)
        if not branch:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found")
        new_start, new_end = appointment_start_end(
            branch=branch,
            start_value=req.proposed_start_time,
            duration_minutes=appointment_duration_minutes(appt),
        )
        ensure_no_conflict(
            db,
            master_id=appt.master_id,
            start_utc=new_start,
            end_utc=new_end,
            exclude_appointment_id=appt.id,
        )
        appointment_service.reschedule(appt, new_start=new_start, new_end=new_end, session=db)
```

- [ ] **Step 7: Wire `manager.update_appointment`**

In `backend/app/routers/manager.py`, replace the function body (roughly lines 74–140) so:

- Cancel branch routes through `appointment_service.cancel`.
- Reschedule branch (when `payload.start_time` or `payload.master_id` change `start_time`/`master`) routes through `appointment_service.reschedule`. Keep the master-change logic local — only call `reschedule` if `start_time` actually changes (matching today's behavior; master swap alone is not in scope for notifications).

Concretely, after the existing conflict-check `appt.master_id = target_master_id`, replace the assignments:
```
appt.start_time = target_start_utc
appt.end_time = target_end_utc
```
with:
```python
if payload.start_time is not None:
    appointment_service.reschedule(
        appt, new_start=target_start_utc, new_end=target_end_utc, session=db
    )
else:
    appt.start_time = target_start_utc
    appt.end_time = target_end_utc
```

For the cancel path, replace:
```
if payload.status == AppointmentStatus.canceled:
    appt.status = AppointmentStatus.canceled
else:
    appt.status = payload.status
```
with:
```python
if payload.status == AppointmentStatus.canceled and appt.status != AppointmentStatus.canceled:
    appointment_service.cancel(appt, db)
elif payload.status is not None:
    appt.status = payload.status
```

Add the import:
```python
from app.services import appointment_service
```

- [ ] **Step 8: Wire `manager.decide_reschedule_request`**

In `backend/app/routers/manager.py`, the approval branch should mirror Task 9 Step 6 — replace direct assignment with `appointment_service.reschedule(appt, new_start=new_start, new_end=new_end, session=db)`.

- [ ] **Step 9: Run all tests**

```bash
uv run pytest -v
```
Expected: all green. If any pre-existing test asserts on appointment status without expecting notifications, it should still pass because the new helpers do not alter response shape.

- [ ] **Step 10: Commit**

```bash
git add backend/app/services/appointment_service.py \
        backend/app/routers/admin.py \
        backend/app/routers/manager.py \
        backend/tests/test_appointment_service.py
git commit -m "feat(notifications): centralize cancel/reschedule and wire all four hook sites"
```

---

## Task 10: Public schema with `client_email` + admin run-dispatcher endpoint

**Files:**
- Modify: `backend/app/schemas/public.py`
- Modify: `backend/app/routers/public.py`
- Modify: `backend/app/services/appointment_out.py`
- Modify: `backend/app/routers/admin.py`
- Create: `backend/tests/test_admin_notifications_endpoint.py`

- [ ] **Step 1: Extend public schemas**

In `backend/app/schemas/public.py`, modify `AppointmentCreate` (around line 45):

```python
class AppointmentCreate(SQLModel):
    branch_id: int
    master_id: int
    procedure_id: int | None = None
    procedure_ids: list[int] = Field(default_factory=list)
    client_name: str
    client_phone: str
    client_email: str | None = None
    start_time: datetime
```

In `AppointmentOut`, add `client_email: str | None = None` (next to `client_phone`).

- [ ] **Step 2: Pass `client_email` from public router**

In `backend/app/routers/public.py`, find where the booking handler builds the `Appointment(...)` row from `AppointmentCreate` and add `client_email=payload.client_email,`.

- [ ] **Step 3: Propagate in `appointment_out`**

In `backend/app/services/appointment_out.py`, find `appointment_to_out(appt)` and include `client_email=appt.client_email,` in the returned `AppointmentOut(...)` constructor (and any other response builders in this file). If the file doesn't expose `client_phone` either, leave it out and skip — the field is optional.

- [ ] **Step 4: Booking integration test**

Append to `backend/tests/test_public_booking.py`:

```python
def test_booking_accepts_client_email(client, db_session) -> None:
    # The existing tests in this file already seed branch + master + procedure;
    # follow the same pattern when constructing the payload.
    # ... seed copy/paste from prior tests, then:
    payload = {
        # standard fields per existing test...
        "client_email": "guest@example.com",
    }
    # Send POST /api/appointments and assert 200, then read DB to confirm appointment.client_email == "guest@example.com".
```

(Implementation note: the existing file shows the seed shape already. Reuse a fixture or copy the helper. The intent of this test is to prove the column round-trips; do not block on the rest of the response shape.)

- [ ] **Step 5: Add the admin run-dispatcher endpoint**

In `backend/app/routers/admin.py`, append:

```python
@router.post("/admin/notifications/run-dispatcher")
async def run_notifications_dispatcher(
    _: Staff = Depends(require_admin),
) -> dict:
    from app.notifications.scheduler import dispatch_pending
    return await dispatch_pending()
```

- [ ] **Step 6: Endpoint test**

`backend/tests/test_admin_notifications_endpoint.py`:

```python
from datetime import datetime, time, timedelta, timezone
from decimal import Decimal

from sqlmodel import Session, select

from app.core.security import create_access_token
from app.models import (
    Appointment,
    Branch,
    Notification,
    NotificationChannel,
    NotificationKind,
    NotificationRecipientRole,
    NotificationStatus,
    Procedure,
    Staff,
)
from app.models.enums import StaffRole


def _seed_admin(db: Session) -> tuple[str, Notification]:
    admin = Staff(
        full_name="Admin", email="admin@zenail.local", password_hash="x",
        role=StaffRole.admin, branch_id=None,
    )
    branch = Branch(name="B", timezone="UTC", open_time=time(8, 0), close_time=time(20, 0))
    db.add(admin)
    db.add(branch)
    db.commit()
    db.refresh(admin)
    db.refresh(branch)
    proc = Procedure(name="X", duration_minutes=60, price=Decimal("0"))
    db.add(proc)
    db.commit()
    db.refresh(proc)

    appt = Appointment(
        branch_id=branch.id, master_id=admin.id, procedure_id=proc.id,
        client_name="A", client_phone="0900", client_email="a@example.com",
        start_time=datetime.now(timezone.utc) + timedelta(days=1),
        end_time=datetime.now(timezone.utc) + timedelta(days=1, hours=1),
        price=Decimal("0"),
    )
    db.add(appt)
    db.commit()
    db.refresh(appt)

    n = Notification(
        appointment_id=appt.id,
        kind=NotificationKind.canceled,
        recipient_role=NotificationRecipientRole.guest,
        recipient_address="a@example.com",
        channel=NotificationChannel.email,
        template_key="canceled.guest.email",
        payload_json={
            "client_name": "A", "branch_name": "B", "master_name": "M",
            "procedures": [], "start_local": "now", "booking_reference": "REF",
        },
        scheduled_at=datetime.now(timezone.utc) - timedelta(seconds=5),
    )
    db.add(n)
    db.commit()
    db.refresh(n)

    token = create_access_token({"sub": str(admin.id), "role": admin.role.value})
    return token, n


def test_run_dispatcher_endpoint_dispatches_pending(client, db_session) -> None:
    token, n = _seed_admin(db_session)
    res = client.post(
        "/api/admin/notifications/run-dispatcher",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["processed"] >= 1

    db_session.refresh(n)
    assert n.status == NotificationStatus.sent
```

(If `create_access_token` lives elsewhere, follow the import used in `auth.py` / existing auth tests.)

- [ ] **Step 7: Run all tests**

```bash
uv run pytest -v
```
Expected: green.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/public.py \
        backend/app/routers/public.py \
        backend/app/services/appointment_out.py \
        backend/app/routers/admin.py \
        backend/tests/test_public_booking.py \
        backend/tests/test_admin_notifications_endpoint.py
git commit -m "feat(notifications): client_email field and admin run-dispatcher endpoint"
```

---

## Task 11: Frontend — optional email field on `BookConfirmPage`

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/pages/guest/BookConfirmPage.tsx`

- [ ] **Step 1: Extend the API type**

In `frontend/src/api/types.ts`, update `Appointment`:

```ts
export type Appointment = {
  id: number
  booking_reference: string
  branch_id: number
  master_id: number
  master_name?: string | null
  procedure_id: number
  procedure_ids: number[]
  procedures: AppointmentProcedure[]
  client_name: string
  client_phone: string
  client_email?: string | null
  start_time: string
  end_time: string
  total_duration_minutes: number
  price: string
  status: 'scheduled' | 'completed' | 'canceled'
}
```

If a separate `BookingCreatePayload` type exists, add `client_email?: string` there too. Otherwise the inline payload object in the page is the surface to extend (Step 2).

- [ ] **Step 2: Add the input + send the field**

In `frontend/src/pages/guest/BookConfirmPage.tsx`:

Change the form-values type and defaults:

```ts
type FormValues = { client_name: string; client_phone: string; client_email: string }
```

```ts
const {
  register,
  handleSubmit,
  formState: { isSubmitting, errors },
} = useForm<FormValues>({ defaultValues: { client_name: '', client_phone: '', client_email: '' } })
```

Inside the submit handler, change the request body:

```ts
body: JSON.stringify({
  branch_id: Number(branchId),
  master_id: Number(masterId),
  procedure_ids: procedureIds.split(',').map((id) => Number(id)),
  client_name: v.client_name,
  client_phone: v.client_phone,
  client_email: v.client_email.trim() === '' ? null : v.client_email.trim(),
  start_time: startTime,
}),
```

Add the input block right under the phone block:

```tsx
<div>
  <label className="mb-1 block text-xs font-medium text-rose-900/80">{t('common.email')}</label>
  <Input
    type="email"
    {...register('client_email', {
      validate: (val) =>
        val === '' || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val) || t('guest.confirm.emailInvalid'),
    })}
  />
  {errors.client_email ? (
    <div className="mt-1 text-xs text-rose-600">{String(errors.client_email.message)}</div>
  ) : null}
</div>
```

- [ ] **Step 3: Add the i18n keys**

In whichever locale file exposes `guest.confirm.*` (search for `guest.confirm.title`), add:

- `common.email` → `Email (tuỳ chọn)` (vi) and `Email (optional)` (en).
- `guest.confirm.emailInvalid` → `Email không hợp lệ` (vi) and `Invalid email` (en).

- [ ] **Step 4: Lint + build**

From `frontend/`:
```bash
npm run lint
npm run build
```
Expected: no errors.

- [ ] **Step 5: Manual UI smoke**

Run `docker compose up --build` (or the existing dev setup), open `http://localhost:5173`, complete a booking with email, and inspect the booking row in Postgres:
```
docker compose exec backend uv run python -c "from app.db.sqlmodel import session_scope; from sqlmodel import select; from app.models import Appointment;\
with session_scope() as s: print([(a.id, a.client_email) for a in s.scalars(select(Appointment).order_by(Appointment.id.desc()).limit(5))])"
```
Expected: most recent row has the email you entered.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/api/types.ts frontend/src/pages/guest/BookConfirmPage.tsx \
        frontend/src/state/i18n.tsx  # adjust path if i18n keys live elsewhere
git commit -m "feat(notifications): optional email field on guest booking form"
```

---

## Task 12: End-to-end smoke verification

**Files:** none (manual verification).

- [ ] **Step 1: Bring stack up clean**

```bash
docker compose down -v
docker compose up --build -d
docker compose exec backend uv run alembic upgrade head
docker compose exec backend uv run python -m app.scripts.seed
```

- [ ] **Step 2: Create a booking with email**

Use the UI at `http://localhost:5173` to complete a booking and supply an email.

- [ ] **Step 3: Cancel via admin**

Log in as `admin@zenail.local`/`admin123`, cancel the booking from the admin appointment view (the existing appointment PATCH path).

- [ ] **Step 4: Run dispatcher**

```bash
curl -X POST http://localhost:8000/api/admin/notifications/run-dispatcher \
  -H "Authorization: Bearer <admin token>"
```

Or wait up to 60 seconds for the in-process scheduler.

- [ ] **Step 5: Inspect logs**

```bash
docker compose logs backend --tail=200 | grep notification.log_provider_send
```
Expected: at least 5 lines (guest×3, master×1, manager×1+).

- [ ] **Step 6: Inspect outbox**

```bash
docker compose exec db psql -U zenail -d zenail -c \
  "SELECT kind, recipient_role, channel, status, count(*) FROM notifications GROUP BY 1,2,3,4 ORDER BY 1,2,3,4;"
```
Expected: every row in `sent` (with the lone exception of any guest row whose channel had no address — those should be `skipped`).

- [ ] **Step 7: Reschedule a different appointment**

Repeat with a reschedule, confirm a new `rescheduled` row set lands and the prior pending reminder (if any) was replaced.

- [ ] **Step 8: Done — record outcome in PR description**

No commit. This is verification only. Move on to PR/merge per `superpowers:finishing-a-development-branch`.

---

## Self-review

- **Spec coverage**: every spec section has a task — outbox model + migration (Task 2), provider abstraction + LogProvider (Task 3), templates (Task 4), service with recipients/channel matrix (Task 5), dispatcher (Task 6), reminder enqueuer (Task 7), scheduler lifespan + test gating (Task 8), all four hook sites including reschedule-request approvals (Task 9), `client_email` schema/API/UI (Tasks 2/10/11), admin run-dispatcher endpoint (Task 10), smoke verification (Task 12).
- **Placeholder scan**: clean — every step shows the actual code or command. The booking integration test (Task 10 Step 4) intentionally references existing seed helpers; if those helpers are not reusable, copy the pattern from the file the test lives in (the file is already the right size to inspect inline).
- **Type consistency**: `on_canceled` (single `l`) used everywhere; `NotificationKind.canceled`, `AppointmentStatus.canceled` match. `appointment_service.cancel` / `reschedule` signatures match across calls. `dispatch_pending` signature is `async (*, session_factory=None) -> dict` everywhere it appears. `enqueue_reminders` signature matches. `Notification.payload_json` is `dict[str, Any]` everywhere.
