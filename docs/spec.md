Below is a **Cursor-ready project spec** you can paste as-is. It’s written like an engineering task brief: clear scope, architecture, DB schema, routes, templates, and acceptance criteria.

---

# SPEC: Local Upwork Payout Manager (FastAPI + SSR + Bootstrap + SQLite)

## 0) Summary

Build a locally hosted web app to track Upwork jobs, worker allocations/splits, connect investment deductions, and payouts. It must support changing calculation rules over time **without altering historical results**, via **versioned settings** linked to each job.

**Tech**: FastAPI, Jinja2 server-rendered templates, Bootstrap 5, SQLite, SQLAlchemy ORM, Alembic migrations.
**Auth**: Optional simple admin password (single-user). No worker logins.

---

## 1) Core Features

1. Manage **Workers** (create/update/archive).
2. Manage **Jobs** (Upwork URL + identifiers).
3. Record **Receipts** (income entries per job; multiple allowed).
4. Define **Worker Allocations** per job (percent or fixed splits).
5. Record **Payments** to workers (partial/full; linked to job optionally).
6. Dashboard summaries (totals + dues).
7. **Settings Versions**:

   * Admin can create new settings versions and activate them.
   * Each job stores the settings version used at creation time.
   * Settings changes affect **only new jobs** unless manually reassigned.
8. Optional: **Finalize Job** to snapshot calculations for audit stability.

---

## 2) Non-Functional Requirements

* Runs locally on localhost (or LAN), single SQLite DB file.
* Bootstrap styling (no SPA).
* All pages server-rendered (Jinja2).
* Calculations consistent and reproducible.
* Deleting is soft-delete (archiving) where possible.

---

## 3) Calculation Rules (Versioned)

### 3.1 Definitions

* `total_received(job)` = SUM(Receipt.amount) for the job.
* `connect_deduction(job)`:

  * fixed: `connect_value`
  * percent: `total_received * connect_value`
* `platform_fee(job)` (optional; for admin’s cut):

  * none OR percent (configurable)
  * computed on either gross or net (configurable)
* `net_distributable(job)` = `total_received - connect_deduction - platform_fee`
* Allocation earned:

  * percent: `net_distributable * share_value`
  * fixed: `share_value`
* Worker totals:

  * earned = SUM(allocation earned)
  * paid = SUM(payments.amount_paid)
  * due = earned - paid

### 3.2 “History must not change”

* Implement `SettingsVersion` table.
* Each Job has `settings_version_id`.
* Computations for a job **always use the job’s settings_version**, not the active one.
* SettingsVersion records are immutable after creation (clone to modify).

### 3.3 Optional Job Snapshot (Recommended)

Add `JobCalculationSnapshot` created when a job is “finalized”.

* Store computed values and per-worker earnings in JSON.
* If snapshot exists, show snapshot results (not re-computed), unless “unfinalized”.

---

## 4) Data Model (SQLite / SQLAlchemy)

### 4.1 tables

#### workers

* id (PK)
* worker_code (unique, e.g. W01)
* name
* contact (nullable)
* notes (nullable)
* is_archived (bool, default false)
* created_at, updated_at

#### settings_versions

* id (PK)
* name (text)
* is_active (bool, default false)  # only one active
* rules_json (text)                # JSON string
* notes (nullable)
* created_at

**rules_json schema (example)**

```json
{
  "currency_default": "USD",
  "connect_default": { "mode": "percent", "value": 0.05 },
  "platform_fee": { "enabled": true, "mode": "percent", "value": 0.10, "apply_on": "net" },
  "rounding": { "mode": "2dp" },
  "require_percent_allocations_sum_to_1": true
}
```

#### jobs

* id (PK)
* job_code (unique like J01)
* title
* client_name (nullable)
* job_post_url (required)
* upwork_job_id (nullable)
* upwork_contract_id (nullable)
* upwork_offer_id (nullable)
* job_type (enum text: fixed/hourly)
* status (enum text: draft/active/completed/archived)
* start_date (nullable)
* end_date (nullable)

**versioning**

* settings_version_id (FK → settings_versions.id)

**overrides** (job-specific rule overrides)

* connect_override_mode (nullable: fixed_amount/percent_of_received)
* connect_override_value (nullable numeric)
* platform_fee_override_enabled (nullable bool)
* platform_fee_override_mode (nullable)
* platform_fee_override_value (nullable numeric)
* platform_fee_override_apply_on (nullable: gross/net)

**flags**

* is_finalized (bool default false)

* created_at, updated_at

#### receipts

* id (PK)
* job_id (FK)
* received_date (date)
* amount_received (numeric)
* source (text: milestone/weekly/bonus/manual)
* upwork_transaction_id (nullable)
* notes (nullable)

#### job_allocations

* id (PK)
* job_id (FK)
* worker_id (FK nullable) # null means “YOU/admin share” optional
* label (text)            # “YOU”, or role like Dev/Design
* role (nullable)
* share_type (text: percent/fixed_amount)
* share_value (numeric)   # percent as 0.50, fixed as money
* notes (nullable)

#### payments

* id (PK)
* payment_code (unique e.g. P0001)
* worker_id (FK)
* job_id (FK nullable but preferred)
* amount_paid (numeric)
* paid_date (date)
* method (nullable)
* reference (nullable)
* notes (nullable)

#### job_calculation_snapshots (optional)

* id (PK)
* job_id (FK unique)
* settings_version_id (FK)
* snapshot_json (text)  # includes totals + per-allocation earned breakdown
* finalized_at (datetime)

---

## 5) Routes & Pages (Server Rendered)

### 5.1 Dashboard

* `GET /`
  Shows:
* totals: total_received, total_connects, total_platform_fee, total_paid, total_due
* top due workers list
* recent jobs list

### 5.2 Workers

* `GET /workers`
* `GET /workers/new`
* `POST /workers/new`
* `GET /workers/{id}`
* `GET /workers/{id}/edit`
* `POST /workers/{id}/edit`
* `POST /workers/{id}/archive`

Worker detail includes:

* allocations/earnings grouped by job
* payments list
* computed totals (earned/paid/due)

### 5.3 Jobs

* `GET /jobs`
* `GET /jobs/new`
* `POST /jobs/new`

  * auto-attach active settings_version
* `GET /jobs/{id}`
* `GET /jobs/{id}/edit`
* `POST /jobs/{id}/edit`
* `POST /jobs/{id}/archive`

Job detail includes:

* Upwork URL button + identifiers
* receipts CRUD
* allocations CRUD
* payments list + add payment shortcut
* computed breakdown (or snapshot if finalized)
* settings version name + view rules

### 5.4 Receipts (nested)

* `POST /jobs/{id}/receipts/new`
* `POST /receipts/{receipt_id}/delete` (or soft delete)

### 5.5 Allocations (nested)

* `POST /jobs/{id}/allocations/new`
* `POST /allocations/{alloc_id}/edit`
* `POST /allocations/{alloc_id}/delete`

Validation:

* If any allocation uses percent and require_sum_to_1 is true → enforce sum == 1.0 (allow tiny epsilon).
* Fixed allocations total must be ≤ net_distributable (or warn).

### 5.6 Payments

* `GET /payments`
* `GET /payments/new`
* `POST /payments/new`
* `POST /payments/{id}/delete` (optional)

### 5.7 Settings Versions

* `GET /settings`

  * show active version + list versions
* `GET /settings/new`
* `POST /settings/new`

  * creates a new settings version (not active by default)
* `POST /settings/{id}/activate`

  * ensures only one is_active
* `GET /settings/{id}`

  * view rules_json (read-only)
* `POST /settings/{id}/clone`

  * clone existing version to new one, allow edits before saving

**Rule**: No editing of an existing version. Only clone.

### 5.8 Finalize (optional but recommended)

* `POST /jobs/{id}/finalize`

  * create snapshot_json and set is_finalized true
* `POST /jobs/{id}/unfinalize`

  * remove snapshot, set is_finalized false

If finalized:

* block edits to receipts/allocations unless unfinalized.

---

## 6) Templates (Bootstrap 5)

### Required templates

* `base.html` (navbar: Dashboard, Jobs, Workers, Payments, Settings)
* `dashboard.html`
* `workers/list.html`, `workers/detail.html`, `workers/form.html`
* `jobs/list.html`, `jobs/detail.html`, `jobs/form.html`
* `payments/list.html`, `payments/form.html`
* `settings/list.html`, `settings/detail.html`, `settings/form.html`, `settings/clone_form.html`

UI details:

* Upwork URL displayed as **Open in Upwork** button.
* Use flash messages for validation errors/success.
* Tables for receipts/allocations/payments on job detail.
* Show computed totals in cards.

---

## 7) Services / Business Logic Layer

Create `app/services/calculations.py` with pure functions:

* `get_job_totals(job, receipts, settings_version) -> dict`
* `compute_allocations(job, allocations, totals, settings_version) -> list`
* `compute_worker_totals(worker_id) -> dict`
* `get_dashboard_totals() -> dict`

Ensure calculations:

* prefer Decimal arithmetic
* consistent rounding based on settings

---

## 8) Implementation Notes

* Use SQLAlchemy session per request.
* Use Alembic migrations.
* Store JSON as TEXT in SQLite, parse with `json.loads`.
* Money: use Decimal fields (or Numeric) + consistent quantize when rounding enabled.

---

## 9) Acceptance Criteria

1. New job automatically links to the currently active settings version.
2. Changing settings (creating + activating new version) affects **only jobs created after** activation.
3. A job always uses its own `settings_version_id` for calculations.
4. Workers page accurately shows earned/paid/due based on allocations & payments.
5. Job page shows a clear breakdown:

   * total received
   * connect deduction
   * platform fee (if enabled)
   * net distributable
   * allocations earned
   * payments made
   * remaining due
6. If finalized (optional), the job shows snapshot values and does not change until unfinalized.

---

## 10) Deliverables

* Working FastAPI app with SSR templates.
* SQLite DB + Alembic migrations.
* CRUD for Workers, Jobs, Receipts, Allocations, Payments, Settings Versions.
* Calculation service with tests (basic unit tests recommended).

---

If you want, I can also provide a **prompt specifically tailored for Cursor** (“build the project starting from this spec”) including a file tree + step-by-step implementation order.
