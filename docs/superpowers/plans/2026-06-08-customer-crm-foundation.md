# Customer CRM Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a normalized customer domain, link appointments to customers, and expose staff-facing customer list/detail workflows.

**Architecture:** Customers are first-class SQLModel rows with a normalized phone key. Appointments keep their current client snapshot fields but gain `customer_id`; public booking resolves or creates a customer before inserting the appointment. Staff customer APIs return searchable summaries and detail/history payloads for admin and manager routes, then the frontend adds list/detail pages in the existing staff layout.

**Tech Stack:** FastAPI, SQLModel, Alembic, PostgreSQL/SQLite tests, React, Vite, TypeScript.

---

## Task 1: Backend Customer Foundation

**Files:**
- Create: `backend/app/models/customer.py`
- Create: `backend/app/services/customers.py`
- Modify: `backend/app/models/appointment.py`
- Modify: `backend/app/models/__init__.py`
- Create: `backend/alembic/versions/<rev>_customer_crm_foundation.py`
- Test: `backend/tests/test_customer_crm.py`

- [ ] Write failing tests for customer creation/reuse during public booking.
- [ ] Add `Customer` model with `full_name`, `phone`, `phone_normalized`, `email`, `notes`, timestamps.
- [ ] Add `Appointment.customer_id` nullable in the model and non-null through migration/backfill.
- [ ] Add service helpers: `normalize_phone`, `resolve_customer_for_booking`, customer summary/detail builders.
- [ ] Write Alembic migration: create customers, backfill from appointments, add `customer_id`, add indexes.
- [ ] Verify backend tests pass.

## Task 2: Booking Linkage

**Files:**
- Modify: `backend/app/routers/public.py`
- Modify: `backend/app/services/appointment_out.py`
- Modify: `backend/app/schemas/public.py`
- Test: `backend/tests/test_customer_crm.py`

- [ ] Update public booking to resolve or create a customer.
- [ ] Persist `appointment.customer_id`.
- [ ] Include `customer_id` in appointment response payloads.
- [ ] Verify repeated phone bookings reuse one customer.

## Task 3: Staff Customer APIs

**Files:**
- Modify: `backend/app/schemas/admin.py`
- Modify: `backend/app/schemas/manager.py`
- Modify: `backend/app/routers/admin.py`
- Modify: `backend/app/routers/manager.py`
- Test: `backend/tests/test_customer_crm.py`

- [ ] Add customer list/search output schemas.
- [ ] Add customer detail/history output schemas.
- [ ] Add admin customer list/detail/notes endpoints.
- [ ] Add manager customer list/detail/notes endpoints scoped to branch appointments.
- [ ] Verify completed spend excludes canceled appointments.

## Task 4: Staff Customer UI

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/layouts/StaffLayout.tsx`
- Modify: `frontend/src/i18n/messages.ts`
- Create: `frontend/src/pages/staff/CustomerListPage.tsx`
- Create: `frontend/src/pages/staff/CustomerDetailPage.tsx`

- [ ] Add customer API types.
- [ ] Add shared staff customer list page with role-aware endpoint selection.
- [ ] Add shared staff customer detail page with history and notes editing.
- [ ] Add staff navigation tabs for admin and manager.
- [ ] Verify frontend lint/build pass.

## Task 5: Docs and Verification

**Files:**
- Modify: `README.md`
- Modify: `docs/backlog/2026-06-05-customer-crm-foundation-backlog.md`

- [ ] Update README feature list.
- [ ] Mark backlog tickets as implemented or summarize implementation status.
- [ ] Run full backend test suite.
- [ ] Run frontend lint and build.
