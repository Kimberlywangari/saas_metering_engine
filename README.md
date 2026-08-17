# SaaS Subscription & Tenant Metering Engine

A Django-based backend for metering per-tenant API usage against
subscription-tier quotas, with atomic usage tracking, account status
enforcement, and both a JSON API and a browser-facing dashboard.

## Features

- **Two related models**: `SubscriptionTier` (plan definitions) and
  `TenantAccount` (customer accounts), linked via a `PROTECT`ed
  one-to-many foreign key.
- **Database-level integrity**: `CheckConstraint`s prevent negative
  pricing and non-positive API limits from ever being persisted, even by
  code that bypasses application-level validation.
- **Race-safe usage metering**: usage counters are incremented atomically
  at the database level using `F()` expressions, so concurrent requests
  for the same tenant cannot undercount usage.
- **Plain Django views**: no Django REST Framework — `JsonResponse` from
  standard `django.views.View` subclasses for the API, plus function-based
  views using `render`/`redirect` for the browser-facing dashboard.
- **Custom admin**: usage-ratio column, colored status badges, and an MRR
  summary banner computed via `Decimal`-safe aggregation.
- **Public tenant dashboard**: a browser-viewable page listing every
  tenant's company name, tier, usage vs. quota, and status, with a button
  per row to record a test API call live.
- **Environment-driven settings**: secrets and environment-specific
  behavior are read from a `.env` file / real environment variables, never
  hardcoded, and `config/settings/` is split into `base.py`, `dev.py`, and
  `prod.py`.

---

## 1. Installation

### Prerequisites

- Python 3.11 or newer
- `pip`

### Steps

```bash
# 1. Clone or unpack the project, then move into it
cd saas_metering_engine

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 3. Install the project (and dev/test extras) via pyproject.toml
pip install -e ".[dev]"

# 4. Copy the environment template and adjust as needed
cp .env.example .env
```

The default `.env` values are sufficient to run locally against SQLite —
no further edits are required for development.

---

## 2. Database Migrations

Migrations apply cleanly from a completely empty database:

```bash
# Apply all migrations (creates db.sqlite3 in dev)
python manage.py migrate

# (Optional) create an admin user to log into /admin/
python manage.py createsuperuser
```

To regenerate migrations after changing `apps/subscriptions/models.py`:

```bash
python manage.py makemigrations subscriptions
python manage.py migrate
```

---

## 3. Running the Project

```bash
python manage.py runserver
```

- Django admin: `http://127.0.0.1:8000/admin/`
- Tenant dashboard: `http://127.0.0.1:8000/api/dashboard/`
- Metered API endpoint: `http://127.0.0.1:8000/api/meter/`

By default `manage.py` uses `config.settings.dev`. To run against
production settings (which validate that `SECRET_KEY`, `ALLOWED_HOSTS`,
and `DATABASE_URL` are all set, and will refuse to start otherwise):

```bash
DJANGO_SETTINGS_MODULE=config.settings.prod python manage.py runserver
```

---

## 4. Running Tests

The suite covers models (constraints, relationships, decimal precision),
services (quota enforcement, status checks, atomic concurrency), and views
(status codes and JSON payloads) — 40 tests in total.

```bash
# Using Django's built-in test runner
python manage.py test apps.subscriptions

# Verbose output
python manage.py test apps.subscriptions -v 2

# Run a single test file, class, or method
python manage.py test apps.subscriptions.tests.test_views
python manage.py test apps.subscriptions.tests.test_views.MeteredEndpointViewTests
python manage.py test apps.subscriptions.tests.test_views.MeteredEndpointViewTests.test_returns_429_when_quota_is_hit
```

---

## 5. Seeding Sample Data

A quick way to get a tenant and tier to experiment with:

```bash
python manage.py shell -c "
from decimal import Decimal
from apps.subscriptions.models import SubscriptionTier, TenantAccount

tier = SubscriptionTier.objects.create(
    name='PRO', monthly_price=Decimal('49.99'), api_call_limit=1000
)
tenant = TenantAccount.objects.create(
    company_name='Acme Corp', billing_email='billing@acme.example', tier=tier
)
print('tenant_id:', tenant.id)
"
```

---

## 6. API Reference & Sample `curl` Calls

All endpoints are mounted under `/api/`.

### `POST` or `GET /api/meter/`

Records one metered API call against the tenant identified by the
`X-Tenant-ID` header.

```bash
curl -X POST http://127.0.0.1:8000/api/meter/ \
  -H "X-Tenant-ID: 1"
```

**200 OK** — call allowed:
```json
{"allowed": true, "remaining_calls": 999}
```

**429 Too Many Requests** — daily quota exceeded:
```json
{"allowed": false, "reason": "Daily API quota exceeded"}
```

**403 Forbidden** — account is `PAST_DUE` or `CANCELED`:
```json
{"allowed": false, "reason": "Account is inactive or past due"}
```

**400 Bad Request** — missing or non-integer `X-Tenant-ID` header:
```json
{"error": "X-Tenant-ID header is required"}
```

### `GET /api/tenants/<tenant_id>/usage/`

Returns a usage snapshot for the given tenant.

```bash
curl http://127.0.0.1:8000/api/tenants/1/usage/
```

Or via header instead of URL parameter:

```bash
curl http://127.0.0.1:8000/api/tenants/usage/ \
  -H "X-Tenant-ID: 1"
```

**200 OK**:
```json
{
  "company_name": "Acme Corp",
  "tier_name": "PRO",
  "daily_quota": 1000,
  "current_usage": 1,
  "percentage_consumed": 0.1,
  "status": "ACTIVE"
}
```

---

## 7. Browser-Facing Dashboard

Unlike the JSON endpoints above, these two routes render HTML for a human
visiting in a browser — no headers or `curl` required.

### `GET /api/dashboard/`

Lists every tenant with their company name, tier, usage/quota, status
(color-coded), and a "+1 API Call" button per row.

### `POST /api/tenants/<tenant_id>/record/`

Triggered by the dashboard's per-row button. Records one API call for
that tenant (via the same `record_api_call` service function used by the
`/api/meter/` endpoint), then redirects back to `/api/dashboard/` so the
updated usage count is visible immediately.

---

## 8. Project Structure

```
saas_metering_engine/
├── .env.example
├── .gitignore
├── manage.py
├── pyproject.toml
├── README.md
├── config/
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   └── settings/
│       ├── base.py     # shared settings, reads .env
│       ├── dev.py       # local dev overrides (SQLite, permissive hosts)
│       └── prod.py      # production overrides (fails fast on missing secrets)
└── apps/
    └── subscriptions/
        ├── migrations/
        ├── templates/
        │   └── subscriptions/
        │       └── dashboard.html   # browser-facing tenant dashboard
        ├── tests/
        │   ├── test_model.py
        │   ├── test_services.py
        │   └── test_views.py
        ├── admin.py      # custom list displays, MRR summary
        ├── models.py     # SubscriptionTier, TenantAccount
        ├── services.py   # record_api_call, reset_daily_usage, update_tenant_status
        ├── urls.py
        └── views.py      # MeteredEndpointView, TenantUsageStatusView,
                           # dashboard_view, record_call_view
```

---

## 9. Design Notes

- **Why `F()` expressions for usage increments**: reading
  `current_api_usage`, adding 1 in Python, and saving it back is vulnerable
  to lost updates under concurrent requests (two requests can both read the
  same starting value before either writes). Using
  `TenantAccount.objects.filter(pk=...).update(current_api_usage=F(...) + 1)`
  pushes the increment into a single atomic `UPDATE` statement at the
  database level.
- **Why `on_delete=PROTECT`** on `TenantAccount.tier`: subscription tiers
  should never be deletable while tenants are actively billed against
  them; attempting to do so raises `ProtectedError` instead of silently
  cascading or nulling out billing data.
- **Why the admin MRR figure is quantized**: SQLite has no native decimal
  type, so Django's `Sum()` aggregation over a `DecimalField` on SQLite can
  surface floating-point noise (e.g. `49.9900000000000`). The admin
  explicitly re-quantizes the aggregated total to 2 decimal places so the
  figure displays as a clean currency value on any backend.
- **Why the metered endpoint is CSRF-exempt, but the dashboard is not**:
  `X-Tenant-ID` header-based metering (`/api/meter/`) is a
  machine-to-machine API contract, not a browser session submitting an
  HTML form, so Django's cookie-based CSRF protection does not apply.
  `/api/dashboard/`'s "+1 API Call" button, by contrast, is a real HTML
  `<form>` submitted from a browser session, so it correctly includes
  `{% csrf_token %}` and is *not* exempted.
- **Known gap — no billing lifecycle automation**: `TenantAccount.status`
  only changes when explicitly set via `update_tenant_status()`, the
  admin, or the shell. There is no scheduled job or payment-provider
  webhook wired up to automatically transition an account to `PAST_DUE`
  or `CANCELED` — that integration is intentionally out of scope for this
  engine, which focuses on metering and enforcement, not billing.