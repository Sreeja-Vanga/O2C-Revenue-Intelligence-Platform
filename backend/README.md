# O2C Revenue Intelligence API

Flask REST backend for the React/Vite client. The application reads database
settings from the project-root `.env` and uses the existing MySQL schema. It
does not create tables or persist detection runs. Detection results are held
in process memory and are separate from the seeded `exception` records.

## Install and run

From the project root in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
pip install -r .\backend\requirements.txt
python -m backend.app
```

The API listens on `http://127.0.0.1:5000` by default. Configure
`VITE_API_BASE_URL=http://127.0.0.1:5000/api` for the frontend if needed.
Flask-CORS allows `http://localhost:5173` and `http://127.0.0.1:5173` by
default; override with comma-separated `CORS_ORIGINS`.

Run the backend tests from the project root:

```powershell
python -m pytest .\backend\tests -v
```

## Response envelope

All routes return JSON in this shape:

```json
{"success": true, "message": "Data retrieved successfully", "data": {}}
```

Errors use `success: false`, a useful `message`, and `data: null`. Numeric
`Decimal` values become JSON numbers; dates and datetimes are ISO-8601 strings.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Backend and MySQL connection status |
| GET | `/api/dashboard/overview` | Volume, revenue, open balance, and exception KPIs |
| GET | `/api/dashboard/anomaly-summary` | Stored exception counts by anomaly code and severity |
| GET | `/api/dashboard/revenue-summary` | Invoice, collection, outstanding, credit, leakage totals |
| GET | `/api/dashboard/lifecycle-summary` | Quote, order, shipment, and invoice counts by status |
| GET | `/api/exceptions` | Paginated exception list; filters: `anomaly_code`, `severity`, `status`, `date_from`, `date_to`, `search`; sorting: `sort_by`, `sort_order` |
| GET | `/api/exceptions/<exception_id>` | Full exception row |
| GET | `/api/exceptions/<exception_id>/source` | Exception and linked source transaction records |
| PUT | `/api/exceptions/<exception_id>/status` | Update status; JSON body: `{"status":"ACKNOWLEDGED"}` |
| GET | `/api/exceptions/summary` | Stored exception totals grouped by type, severity, and status |
| POST | `/api/detection/run` | Run all seven source-table detection rules |
| GET | `/api/detection/results` | Latest in-memory detection run |
| GET | `/api/detection/summary` | Latest detected counts, severities, and estimated exposure |
| GET | `/api/analytics/revenue-leakage` | Stored positive recorded variance grouped by anomaly type |
| GET | `/api/analytics/order-performance` | Order counts/value by status |
| GET | `/api/analytics/invoice-performance` | Invoice status balances and overdue metrics |
| GET | `/api/analytics/payment-performance` | Payment, allocation, and unapplied totals |
| GET | `/api/analytics/trends` | Monthly invoice, payment, and exception series |
| GET | `/api/analytics/invoice-aging` | Outstanding invoice amounts grouped by age |
| GET | `/api/analytics/outstanding-receivables` | Open invoice balance by account |
| GET | `/api/analytics/dispute-analysis` | Dispute amounts/statuses and unapplied approved credits |
| GET | `/api/analytics/lifecycle-performance` | Quote conversion, order fulfillment, and O2C timing metrics |
| GET | `/api/analytics/reconciliation` | Independent source-table reconciliation findings by anomaly type |
| GET | `/api/analytics/reconciliation/details` | Independent line-level reconciliation findings from source tables |
| GET | `/api/accounts[?filters]` | Paginated, filterable accounts; detail includes related documents |
| GET | `/api/quotes[?filters]` | Paginated quotes; detail includes quote lines |
| GET | `/api/orders[?filters]` | Paginated sales orders; detail includes order lines |
| GET | `/api/shipments[?filters]` | Paginated shipments; detail includes shipment lines |
| GET | `/api/invoices[?filters]` | Paginated invoices; detail includes invoice lines |
| GET | `/api/payments[?filters]` | Paginated payments; detail includes allocations |
| GET | `/api/disputes[?filters]` | Paginated disputes |
| GET | `/api/events[?filters]` | Paginated status event history |
| GET | `/api/events/entity/<entity_type>/<entity_id>` | Event history for one entity |
| POST | `/api/synthetic-data/jobs` | Start generation in a new isolated MySQL sandbox (`profile`: `small` or `demo`) |
| GET | `/api/synthetic-data/jobs/<job_id>` | Poll sandbox generation status and table counts |
| GET | `/api/resource-schema/<resource>` | Read actual transaction columns used by the management form |
| GET | `/api/capabilities` | Read whether transaction write operations are enabled |
| GET | `/api/reports/financial.xlsx` | Download a multi-sheet Excel financial and reconciliation report |

### Write controls and safeguards

Transaction `POST`, `PUT`/`PATCH`, and `DELETE` endpoints are disabled by
default. Set `TRANSACTION_WRITES_ENABLED=true` in the project-root `.env` to
enable them for a trusted local environment. IDs are generated under a
MySQL advisory lock; status changes append to the existing immutable
`status_event` history. Foreign-key and schema constraints reject changes
that would break referential integrity. `status_event` rows cannot be
updated or deleted. Records with recorded status history cannot be deleted.
There is no user authentication or role-based authorization in this project;
keep the Flask server bound to localhost and do not enable writes on a
network-exposed deployment until an authentication/authorization layer is
added.

Synthetic data jobs create a uniquely named `o2c_ri_sandbox_*` database and
never target `DB_NAME`. The sandbox setup extracts only `CREATE TABLE` and
append-only trigger DDL from `database/schema.sql`; it does not execute the
script's database selection or `DROP` statements. Small and demo profiles
run the project generator modules in dependency order. A failed job retains
its sandbox for inspection; the application does not automatically drop
databases. Run the backend only with a MySQL account that is authorized to
create sandbox databases when using this feature.
The running API continues to use the database configured by `DB_NAME`;
to inspect a generated sandbox in the UI, restart a separate backend process
with that sandbox's database name in its environment.

The Excel report contains summary, revenue leakage, order performance,
invoice aging, receivables, payment/invoice performance, disputes, and
independent source-table reconciliation findings. It is generated from
current database results at download time.

Transaction list endpoints accept `page`, `per_page` (maximum 200), `sort_by`,
`sort_order`, supported resource-specific exact-match filters, `date_from`,
`date_to` where available, and `search` where available. Transaction endpoints
are read-only; there are no APIs for modifying generated transaction data.

### KPI definitions

- Dashboard record counts are scalar counts from each respective table;
  separate scalar subqueries prevent one-to-many joins from multiplying totals.
- `total_revenue` and `total_invoiced_amount` are `SUM(invoice.total_amount)`.
- `total_outstanding_amount` is `SUM(GREATEST(invoice.open_amount, 0))`.
- `total_collected_amount` is `SUM(payment.amount)` excluding `VOID` payments.
- `credit_amount` is `SUM(invoice.credit_amount)`.
- Dashboard and revenue-summary leakage, and analytics leakage, use
  `SUM(GREATEST(exception.variance_amount, 0))`; records without a stored
  monetary variance contribute zero. This uses the existing exception ledger,
  not detection output.
- Detection estimated leakage is computed independently per rule. Price
  variance multiplies absolute unit-price difference by ordered quantity;
  shipment/billing overages use excess quantity times unit price; payment and
  dispute rules use unreconciled amounts; closed unpaid orders use outstanding
  invoice balances; status skips have zero monetary exposure.
- Invoice overdue metrics count `ISSUED`/`PARTIALLY_PAID` invoices with
  `due_date < CURRENT_DATE` and positive `open_amount`.
- Payment collection rate is non-void payment amounts divided by non-void
  invoice totals. Invoice/payment timing metrics use the earliest linked date
  per order or invoice to avoid multiplying amounts across one-to-many joins.

### Detection rules

Each detection rule reads only source transaction/event tables:
`PRICE_VARIANCE`, `SHIPMENT_QUANTITY`, `BILLING_MISMATCH`,
`CASH_APPLICATION`, `DISPUTE_LEAKAGE`, `ORDER_CLOSED_UNPAID`, and
`STATUS_TRANSITION_SKIP`. The status rule flags the verified
`SALES_ORDER: SHIPPED -> CLOSED` transition skipping `DELIVERED`; it does not
assume undocumented lifecycle transitions. Findings include anomaly/entity
identity, severity, expected and actual values, variance, explanation, and
supporting entity details. Results are not inserted into `exception` or any
other table.
