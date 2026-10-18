# LedgerLoop

LedgerLoop is a synthetic-data B2B receivables follow-up desk for the C28
Fynd × NMIMS Hyderabad engineering case.

## Project requirements

See [`PROJECT_REQUIREMENTS.md`](./PROJECT_REQUIREMENTS.md) for the consolidated
requirements, acceptance criteria, and phased development checklist derived from
the supplied C28 documents.

For a business-oriented explanation of the product, workflow, rules, dispute
handling, promises, scoring, drafts, exports, and MBA discussion questions, see
[`docs/MBA_GUIDE.md`](./docs/MBA_GUIDE.md).

For the complete technical architecture, data contracts, calculation logic,
workflow, safety boundaries, test coverage, assumptions, and AI handoff context,
see [`docs/TECHNICAL_HANDOFF.md`](./docs/TECHNICAL_HANDOFF.md). This is the
canonical document to provide to a new developer or AI model before modifying
the project.

## Run the application

Use Python 3.10 or later:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The default input is [`data/fixture.json`](./data/fixture.json). The sidebar also
accepts a JSON, CSV, or computer-generated PDF upload. PDF uploads are converted
to the existing invoice JSON schema and then passed through the normal loader
validation. Scanned image PDFs require a future OCR phase.

PDF extraction currently supports one text-based invoice per upload and uses
`pdfplumber` for layout-preserving text extraction, with `pypdf` as a fallback.
Only the six LedgerLoop fields are loaded from a PDF: customer, invoice number,
invoice amount, due date, invoice date, and already received amount. The
received amount is entered manually because an invoice PDF normally describes
the sale, not later payments. Review extracted values and extraction errors
before using the result for collection decisions.

For broader usability testing, [`data/real_world_synthetic.json`](./data/real_world_synthetic.json)
contains 12 deliberately varied invoice scenarios: partial and full payment,
open disputes, replacement delivery, credit notes, active/kept/broken promises,
negotiated settlement, overpayment, a future invoice, high-risk ageing, and
unapplied/future receipts. It is synthetic only and can be uploaded from the
Hisaabset sidebar without changing the default fixture.

## Retailer credit recommendations

The Customers page now includes a separate low-is-good retailer risk rating.
It is calculated from completed payment timing, late days, outstanding balance,
broken promises, and verified retailer-fault complaints. Retailers with fewer
than three completed invoices are shown as **Insufficient history** rather than
being treated as low risk.

Hisaabset also shows a suggested purchasing limit and upfront/credit split:
new retailers start at 50% upfront and 50% credit; reliable payment history
can suggest 45%/55% terms, and five or more verified on-time payments can
suggest 40%/60% terms. Ratings and terms are recommendations only. A
distributor finance manager must approve or override them, and complaints are
not risk penalties until validated.

## Negotiated next-order recovery

The Customers page supports a separate negotiated recovery agreement for a
previous invoice. The finance manager can record:

- Actual BEP and minimum recovery floor
- BEP plus an agreed amount, exact BEP, BEP multiplier, or custom target
- Next-order upfront/credit split
- Credit period, negotiation note, and finance approval

Hisaabset tracks recovered, remaining, and excess amounts. It marks a next
order as eligible only after the agreed target is reached or exceeded, and
still shows that finance approval is required. Agreements below BEP require a
reason. This does not change invoice balances or automatically approve,
block, or dispatch a new order.

Recovery targets begin at the amount already collected when the agreement is
created. Previous collections remain visible in invoice history but do not
count toward the newly negotiated target. Only payments received after the
agreement baseline reduce its remaining recovery amount.

The export action also writes `output/negotiated_recovery.json` with the
agreement, recovery status, and approval evidence.

## Run tests

```powershell
python -m pytest -q
```

The suite covers loader validation, balances, ageing, disputes, promises,
priority scoring, drafts, exports, UI delegation, and an end-to-end synthetic
fixture. The starter C28 regression verifies ₹46,000 outstanding, ₹36,000
collectible, ₹10,000 under review, one paid invoice, and the expected priority
order.

## Workflow

1. Load the fixture or upload a compatible file.
2. Select an `as_of` date and optionally filter customers.
3. Review priority, dispute, promise, paid, not-due, and unapplied-receipt views.
4. Open invoice detail to edit dispute or promise fields in session state.
5. Review and edit the template-only customer drafts.
6. Export `output/result.json`, `output/result.csv`,
   `output/negotiated_recovery.json`, and `output/evidence_log.md`.

Every draft is labelled `DRAFT - not sent`. There is no send action or external
service integration.

## Approved email sending

Hisaabset now supports a human-approved Amazon SES email workflow. The draft
shows the exact collectable amount in its subject/body, and the finance user
must check **I reviewed the exact figures and approve this email** before the
send button becomes available. The initial test contact for Aarav General Store
is `unnamedinsect424@gmail.com`.

Email delivery is deliberately disabled by default. Configure AWS credentials
through the normal AWS credential chain, then set these environment variables
only when ready:

```powershell
$env:HISAABSET_EMAIL_SENDER = "unnamedinsect424@gmail.com"
$env:AWS_REGION = "ap-south-1"
$env:HISAABSET_EMAIL_TEST_MODE = "false"
python -m streamlit run app.py --server.port 8501
```

The sender must be verified in Amazon SES. In SES sandbox mode, the recipient
must also be verified. Never place an AWS secret key, SES credential, or app
password in source code, a fixture, or chat. If test mode remains enabled,
approval validates the message but no email is delivered.

## Evidence and limitations

- [`CONTEXT.md`](./CONTEXT.md) records the engineering scope and business rules.
- [`docs/assumptions.md`](./docs/assumptions.md) separates observed fixture facts
  from design assumptions and known gaps.
- [`data/extra_synthetic.json`](./data/extra_synthetic.json) demonstrates partial
  payment, an unapplied receipt, a detailed dispute, a broken promise, a future
  receipt, and invalid input.
- Output files are generated locally and are ignored as runtime artifacts.
- All data is synthetic. No cash recovery, live revenue, market demand, or
  production readiness is claimed.
- MBA pricing, growth, customer research, and pitch work are outside the
  engineering scope. An MBA-entry snapshot should be added only when the MBA
  team actually joins.

## Production foundation

The original Streamlit workflow remains available for the seeded demo. A
separate production API foundation now lives in [`backend/`](./backend/):

- PostgreSQL-compatible durable invoice, receipt, and audit models.
- Organization-scoped queries and unique invoice/receipt constraints.
- Cognito/OIDC JWT validation hooks.
- Roles for `finance_admin`, `finance_manager`, `collector`, and `auditor`.
- Append-only audit-event recording for mutating API actions.
- A health endpoint and non-root backend container.
- Explicit fixture seeding for the initial demo organization.

Run the API locally with:

```powershell
python -m uvicorn backend.main:app --reload --port 8000
python -m backend.seed
```

The API is intentionally not treated as complete production authorization by
default. Configure `LEDGERLOOP_OIDC_ISSUER`, `LEDGERLOOP_OIDC_AUDIENCE`, and
`LEDGERLOOP_OIDC_JWKS_URL` before enabling authenticated access. Production
deployment still requires managed PostgreSQL, secret management, migrations,
TLS/ALB, backups, monitoring, and a formal Cognito user-pool/group policy.
