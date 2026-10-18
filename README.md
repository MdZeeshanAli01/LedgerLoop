# LedgerLoop

LedgerLoop, also branded **Hisaabset** (*Har payment ka clear hisab*), is a
Streamlit-based B2B receivables and retailer-credit decision-support desk. It
helps a distributor finance team understand what is outstanding, what can be
requested now, what needs dispute review, and which follow-up deserves
attention first.

All included data is synthetic. The application is a decision-support
prototype and is not an accounting system, payment gateway, autonomous credit
engine, collections agent, or production-readiness claim.

## What it does

- Imports JSON, CSV, and text-based computer-generated PDF invoices.
- Normalizes legacy and inconsistent source fields.
- Calculates balances with `Decimal` money arithmetic.
- Applies dated receipts as of a selected date.
- Keeps unapplied receipts visible without auto-matching them.
- Separates collectible balances from dispute-review balances.
- Tracks paid, not-due, collectable, under-review, and promised invoices.
- Records received payments, closes settled invoices, and generates official payment vouchers.
- Detects active, kept, and broken payment promises.
- Ranks collectible invoices using the documented ageing, amount, and
  broken-promise formula.
- Builds customer-level repayment history and low-is-good risk ratings.
- Suggests purchasing terms without automatically approving credit.
- Records negotiated next-order recovery agreements with a historical baseline.
- Produces reviewable drafts and reproducible JSON, CSV, and evidence exports.
- Provides a local Finance Lead login for the demo workflow.

## Repository structure

```text
LedgerLoop/
├── app/
│   ├── __init__.py
│   └── app.py                         Streamlit UI and session orchestration
├── backend/                           FastAPI production foundation
├── data/
│   ├── fixture.json                   Default six-invoice fixture
│   ├── extra_synthetic.json           Compact edge-case fixture
│   ├── real_world_synthetic.json      Full synthetic workflow fixture
│   └── source_documents/              Supplied PDF, image, and ZIP references
├── deploy/
│   ├── aws/                           AWS deployment assets and instructions
│   └── docker/                        Streamlit Dockerfile
├── docs/
│   ├── CONTEXT.md                     Business rules and scope
│   ├── MBA_GUIDE.md                   Business-oriented explanation
│   ├── PROJECT_REQUIREMENTS.md        Original requirements and acceptance criteria
│   ├── TECHNICAL_HANDOFF.md           Canonical engineering handoff
│   ├── TECHNICAL_PRESENTATION_GUIDE.md Architecture and presentation guide
│   ├── assumptions.md                 Observed facts and assumptions
│   └── reference/                     Supplied case and product documents
├── src/                               Pure domain and integration modules
├── tests/                             Python regression and integration tests
├── web/                               React experiment retained separately
├── app.py                             Compatibility launcher
├── requirements.txt                   Python dependencies
└── Dockerfile                         Historical root Dockerfile reference
```

The domain source of truth is kept separate from Streamlit rendering:

- `src/loader.py` — parsing, normalization, and validation.
- `src/rules.py` — balances, ageing, promises, states, and priority.
- `src/disputes.py` — dispute splits and explanations.
- `src/retailer.py` — customer history, risk, complaints, and recommendations.
- `src/negotiated.py` — negotiated recovery and baseline calculations.
- `src/drafts.py` — reviewable follow-up drafts.
- `src/export.py` — reproducible results and evidence exports.
- `app/app.py` — UI and session-state orchestration only.

## Run locally

Use Python 3.10 or later. From the repository root:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8501
```

The root `app.py` is a compatibility launcher for existing Streamlit and VS
Code configurations. The implementation is in `app/app.py`; both launch paths
load the same application.

Open:

```text
http://localhost:8501
```

The health endpoint is:

```text
http://localhost:8501/_stcore/health
```

To run the implementation path directly:

```powershell
python -m streamlit run app/app.py --server.port 8501
```

## Demo login

The current local workflow includes a Finance Lead authentication screen. It
requires a deployment-managed password hash and is not enterprise SSO.

The login page supports configured Finance Lead aliases. There is no login
bypass or quick-login action. For production,
replace this local session gate with Cognito/OIDC and remove any source-level
local authentication.

Generate a password hash without placing the password in source code:

```powershell
$env:HISAABSET_AUTH_PASSWORD_HASH = "<salt_hex>$<pbkdf2_digest_hex>"
```

Store this value in the local environment, Streamlit secrets, or AWS Secrets
Manager. If it is missing or malformed, authentication fails closed.

## Main workflow

1. Start the app and sign in.
2. Use **Add new bill** for manual invoices or source uploads.
3. Use the sidebar to load JSON, CSV, or a text-based PDF.
4. Select the `as_of` date and optional customer filter.
5. Review **Your bills** for priority, disputes, promises, paid invoices,
   not-yet-due invoices, and unapplied receipts.
6. Open invoice detail to edit review fields in session state.
7. Use **Customers** for history, risk, complaints, recommendations, and
   negotiated recovery.
8. Review drafts before any permitted communication action.
9. Export evidence and result files from the relevant workflow.

The default fixture is [`data/fixture.json`](./data/fixture.json). The broader
synthetic fixture is [`data/real_world_synthetic.json`](./data/real_world_synthetic.json).
The compact validation pack is [`data/extra_synthetic.json`](./data/extra_synthetic.json).

## Core financial safeguards

- Detailed receipts replace the aggregate received amount when present.
- Future-dated receipts are excluded until the selected `as_of` date.
- Unapplied receipts are never silently allocated.
- Outstanding balances are floored at zero; overpayments remain visible.
- Disputed amounts remain visible and can be held for operational review.
- New retailers receive **Insufficient history** until three invoices are
  completed.
- Retailer risk and invoice priority are separate concepts.
- Recommendations are not approvals.
- Negotiated recovery starts from `baseline_collected`; historic receipts
  cannot satisfy a newly created target.
- Missing PDF fields are reported for review rather than invented.

Read [`docs/TECHNICAL_HANDOFF.md`](./docs/TECHNICAL_HANDOFF.md) before changing
any domain calculation or workflow invariant.

## PDF uploads

PDF support is for one text-based, computer-generated invoice per upload.
`pdfplumber` is used first and `pypdf` is used as a fallback. The importer
extracts the required invoice fields and sends them through normal loader
validation.

Scanned/image-only PDFs require OCR and are not currently supported. A missing
due date is a review condition; the application does not guess one. The
received amount is entered manually because an invoice PDF normally describes
the sale, not later payments.

## Exports

The application writes runtime artifacts under `output/`:

```text
output/result.json
output/result.csv
output/negotiated_recovery.json
output/evidence_log.md
output/starting_state.json
```

These files are ignored by Git. JSON and CSV exports preserve calculated
components, dates, explanations, approval evidence, recovery baselines, and
separate balance values.

## Email safety

The current code contains a human-approved Amazon SES integration for
controlled testing. Test mode is enabled by default. A finance user must
review the exact figures before the send action is enabled.

Do not enable live delivery until the SES sender, recipient policy, IAM task
role, bounce handling, and durable communication audit policy are approved.
Use the normal AWS credential chain and environment variables; never put AWS
keys, passwords, or app secrets in source code, fixtures, or chat.

## Tests and validation

Run the full Python suite:

```powershell
python -m pytest -q
python -m compileall -q app src backend tests
git diff --check
```

The suite covers loader validation, balance rules, receipts, disputes,
promises, priority, drafts, exports, PDF extraction, retailer risk,
negotiated recovery, authentication, and synthetic end-to-end scenarios.

## Backend foundation

The separate [`backend/`](./backend/) package is an initial FastAPI
production foundation. It currently includes:

- SQLAlchemy models for invoices, receipts, and audit events.
- SQLite local development support and PostgreSQL configuration.
- Organization-scoped invoice access.
- Cognito/OIDC JWT validation hooks.
- Role checks for `finance_admin`, `finance_manager`, `collector`, and `auditor`.
- Health endpoint and fixture seeding.
- A non-root backend container.

Run it locally:

```powershell
python -m uvicorn backend.main:app --reload --port 8000
python -m backend.seed
```

The backend is not a production launch claim. Production still requires
versioned migrations, managed PostgreSQL, S3 storage, Cognito configuration,
secrets management, complete API integration, monitoring, backups, retention
controls, and an independent security review.

## Deployment options

### Streamlit Community Cloud

For a fast demonstration deployment, use the repository’s root compatibility
launcher:

```text
Repository: MdZeeshanAli01/LedgerLoop
Branch: main
Main file path: app.py
```

The latest changes must be merged into `main` before selecting it. Do not use
`streamlit_app.py`; it is not part of this project.

### AWS production architecture

The intended AWS architecture is:

```text
CloudFront
    ↓
HTTPS Application Load Balancer
    ↓
ECS Fargate Streamlit service
    ↓
ECR image and CloudWatch logs
```

The repository currently contains a secret-free image build and ECS task
definition foundation in [`deploy/aws/`](./deploy/aws/). The deployment script
can build, push, and render a task definition after a valid deployment
identity is configured:

```powershell
aws sts get-caller-identity
.\deploy\aws\deploy.ps1 -Region ap-south-1 -Tag v1
```

AWS deployment is **live** on AWS ECS on Fargate in `ap-south-1` (Mumbai) with continuous 24/7 self-healing hosting (`desiredCount: 1`, container health checks):
- **Live Endpoint:** `http://3.110.130.28:8501`
- **Healthcheck:** `http://3.110.130.28:8501/_stcore/health` (HTTP 200 OK)

Use a dedicated deployment identity or AWS SSO. Never use root credentials,
never create keys for ECS task roles, and never commit AWS credentials.
Previously exposed keys must be disabled and rotated.

Read [`deploy/aws/README.md`](./deploy/aws/README.md) for the current
deployment prerequisites and safety checks.

## Documentation

- [`docs/TECHNICAL_HANDOFF.md`](./docs/TECHNICAL_HANDOFF.md) — canonical
  architecture, data contracts, invariants, workflows, and scenarios.
- [`docs/PROJECT_REQUIREMENTS.md`](./docs/PROJECT_REQUIREMENTS.md) — original
  requirements and acceptance criteria.
- [`docs/CONTEXT.md`](./docs/CONTEXT.md) — scope and business rules.
- [`docs/MBA_GUIDE.md`](./docs/MBA_GUIDE.md) — business and presentation guide.
- [`docs/assumptions.md`](./docs/assumptions.md) — observed facts and assumptions.
- [`docs/TECHNICAL_PRESENTATION_GUIDE.md`](./docs/TECHNICAL_PRESENTATION_GUIDE.md)
  — architecture defense and presentation reference.

## Security boundary

All supplied data is synthetic. Do not place secrets in the repository. Do not
use root AWS access keys. The app may calculate, explain, recommend, prepare,
and export; a responsible finance user must approve consequential actions.
