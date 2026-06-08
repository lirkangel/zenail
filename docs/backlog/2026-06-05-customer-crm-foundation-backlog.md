# Customer CRM Foundation Backlog

Date: 2026-06-05
Status: Implemented 2026-06-08
Owner: Unassigned

## Parent Epic

### EPIC-CRM-001: Customer CRM Foundation

Build a real customer domain for Zenail so the product stops treating each appointment as a standalone guest record. This epic introduces normalized customer data, customer-to-appointment linking, and staff-facing customer search/detail views.

### Problem

Zenail currently stores guest identity directly on appointments (`client_name`, `client_phone`, `client_email`). That is enough for booking, but not enough for CRM workflows:

- no reliable repeat-customer history
- no customer profile page
- no spend summary by customer
- no staff notes/preferences surface
- no durable foundation for loyalty, retention, or segmentation

### Outcome

After this epic:

- every appointment belongs to a customer record
- public booking resolves an existing customer or creates a new one
- staff can search customers and open a customer profile
- a customer profile shows identity, appointment history, and spend summary

### In Scope

- `Customer` model and migration
- appointment-to-customer relation
- dedupe/resolve rules during booking
- backfill strategy for existing appointments
- staff APIs for customer list/detail
- staff UI for customer list/detail
- tests, seed data, and docs updates

### Out of Scope

- loyalty points
- campaigns / bulk messaging
- retention automation
- gift cards / wallet / credits
- advanced customer segmentation

### Dependencies

- existing booking flow
- existing appointment and notification model
- existing staff auth and role-based routing

### Success Metrics

- new bookings always resolve to a customer record
- existing appointment history remains queryable
- staff can search and open a customer profile in under 3 clicks
- no regression in guest booking flow

---

## Child Tickets

### CRM-101: Add Customer Domain Model and Migration

**Goal**  
Introduce a normalized customer entity in the backend.

**Scope**

- add `Customer` SQLModel
- create Alembic migration
- add indexes and uniqueness strategy
- expose model in `backend/app/models/__init__.py`

**Proposed fields**

- `id`
- `full_name`
- `phone`
- `email` nullable
- `notes` nullable
- `created_at`
- `updated_at`

**Uniqueness / indexing**

- unique normalized phone
- index on lowercased email if present

**Acceptance Criteria**

- migration runs cleanly on empty DB
- model is available in ORM metadata
- phone uniqueness is enforced at DB level

**Dependencies**

- none

**Risk**

- low

**Effort**

- small

---

### CRM-102: Link Appointments to Customers and Backfill Existing Data

**Goal**  
Attach every appointment to a customer record without breaking current data.

**Scope**

- add `customer_id` to appointments
- backfill existing appointments into customers
- dedupe historical appointments by phone first, then email fallback when phone is missing or unusable
- preserve existing appointment fields for compatibility during transition

**Implementation Notes**

- backfill should create customers before enforcing non-null `customer_id`
- `client_name`, `client_phone`, `client_email` stay on appointment for snapshot/history integrity
- customer identity becomes the source of truth for current profile data

**Acceptance Criteria**

- all existing appointments end up with a valid `customer_id`
- duplicate customer rows are minimized using the agreed dedupe rule
- booking and staff appointment views keep working after migration

**Dependencies**

- CRM-101

**Risk**

- medium

**Effort**

- medium

---

### CRM-103: Resolve Customer Identity During Public Booking

**Goal**  
Make public booking create or reuse a customer record automatically.

**Scope**

- update booking write path in backend
- normalize phone before lookup
- if phone matches existing customer, update missing email/name conservatively
- if no match, create customer
- assign `appointment.customer_id`

**Rules**

- phone is primary identity key
- email is secondary enrichment field, not primary lookup key
- do not overwrite existing non-empty customer data with blank input

**Acceptance Criteria**

- new booking creates a customer when none exists
- repeated booking from same phone reuses the same customer
- appointment is persisted with `customer_id`
- existing booking response shape stays compatible

**Dependencies**

- CRM-101
- CRM-102

**Risk**

- medium

**Effort**

- medium

---

### CRM-104: Add Staff Customer Search/List API

**Goal**  
Give staff a way to search customers from the CRM side.

**Scope**

- add staff API endpoint for customer list/search
- support search by phone, name, email
- paginate results
- enforce branch visibility rules if needed by current business model

**Recommended endpoint**

- `GET /api/admin/customers`
- `GET /api/manager/customers`

**Returned fields**

- customer identity summary
- latest appointment date
- visit count
- total spend

**Acceptance Criteria**

- admin can search all customers
- manager can search customers relevant to their branch scope
- response is paginated and stable for UI use

**Dependencies**

- CRM-101
- CRM-102

**Risk**

- medium

**Effort**

- medium

---

### CRM-105: Add Customer Detail API with History and Spend Summary

**Goal**  
Provide the data needed for a useful customer profile page.

**Scope**

- add customer detail endpoint for staff
- include customer core fields
- include appointment history
- include aggregates: visit count, completed spend, latest visit, upcoming appointment

**Recommended endpoint**

- `GET /api/admin/customers/{customer_id}`
- `GET /api/manager/customers/{customer_id}`

**Acceptance Criteria**

- detail endpoint returns a stable shape for frontend use
- completed revenue excludes canceled appointments
- history is ordered newest first

**Dependencies**

- CRM-104

**Risk**

- medium

**Effort**

- medium

---

### CRM-106: Build Staff Customer List and Profile UI

**Goal**  
Add the first staff-facing CRM surfaces on the frontend.

**Scope**

- add customer list page for admin
- add customer list page for manager
- add customer detail page
- wire search input, empty states, loading states, and pagination
- show profile summary, history, spend, and upcoming appointment

**UI Requirements**

- keep it operational, not marketing-styled
- optimize for quick search and scanning
- use the existing staff layout and patterns

**Acceptance Criteria**

- staff can navigate to customer list
- staff can search by phone/name/email
- opening a customer shows profile and appointment history
- frontend lint/build stay green

**Dependencies**

- CRM-104
- CRM-105

**Risk**

- medium

**Effort**

- medium

---

### CRM-107: Add Customer Notes Editing

**Goal**  
Allow staff to store durable customer notes once profiles exist.

**Scope**

- backend patch endpoint for notes
- frontend edit surface on customer profile
- audit-safe behavior: notes are plain free text, no rich editor

**Examples**

- preferred technician
- allergy / product preference
- service preference
- follow-up reminder for staff use

**Acceptance Criteria**

- admin and manager can update notes
- notes persist to the customer record
- notes editing does not affect historical appointment snapshots

**Dependencies**

- CRM-105
- CRM-106

**Risk**

- low

**Effort**

- small

---

### CRM-108: Tests, Seed Data, and Docs for Customer CRM

**Goal**  
Finish the slice properly so it is maintainable.

**Scope**

- backend tests for model, migration assumptions, booking resolution, list/detail APIs
- frontend tests if test framework is added in parallel, otherwise at minimum manual QA checklist
- seed customer-linked appointment data
- update README and relevant backend/frontend docs

**Acceptance Criteria**

- CI remains green
- seed data demonstrates repeat-customer history
- docs explain the new customer model and routes

**Dependencies**

- CRM-101 through CRM-107

**Risk**

- low

**Effort**

- medium

---

## Suggested Delivery Order

1. CRM-101
2. CRM-102
3. CRM-103
4. CRM-104
5. CRM-105
6. CRM-106
7. CRM-107
8. CRM-108

## Suggested Milestones

### Milestone A: Backend Foundation

- CRM-101
- CRM-102
- CRM-103

### Milestone B: CRM Read APIs

- CRM-104
- CRM-105

### Milestone C: Staff UX

- CRM-106
- CRM-107

### Milestone D: Hardening

- CRM-108

## Notes for Future Backlog

Once this epic lands, the next natural parent epic is:

- **Customer Retention and Loyalty**

That future epic can build on this one with:

- loyalty points
- rebooking prompts
- no-show tracking
- birthday/anniversary outreach
- targeted campaigns using the notifications system

## Implementation Notes

Implemented on 2026-06-08.

Landed scope:

- `Customer` model and customer-backed appointments
- public booking customer resolution by normalized phone
- admin and manager customer list/detail APIs
- branch-scoped manager visibility
- customer notes editing
- staff customer list/detail UI
- seed data linked to customers
- README update

Primary files:

- `backend/app/models/customer.py`
- `backend/app/services/customers.py`
- `backend/alembic/versions/d4a7f92c6e11_customer_crm_foundation.py`
- `backend/app/routers/admin.py`
- `backend/app/routers/manager.py`
- `backend/app/routers/public.py`
- `frontend/src/pages/staff/CustomerListPage.tsx`
- `frontend/src/pages/staff/CustomerDetailPage.tsx`
- `backend/tests/test_customer_crm.py`
