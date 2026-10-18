# Hisaabset Technical Handoff and AI Context

**Project:** Hisaabset  
**Repository:** `MdZeeshanAli01/LedgerLoop`  
**Product tagline:** *Har payment ka clear hisab*  
**Application entry point:** `app/app.py`
**Current runtime:** Streamlit on `http://localhost:8501`  
**Live Cloud Deployment:** AWS ECS Fargate on `http://13.126.83.182:8501`  
**Authentication:** Single-role Finance Lead (`admin` / `[credential-rotated]`)  
**Document purpose:** This is the canonical technical and product-context handoff for developers, reviewers, and future AI models.

> Give this document to a new developer or AI together with the repository. It explains the current architecture, data model, business rules, safety boundaries, user workflows, known assumptions, and validation status. It should be updated whenever a core rule or data contract changes.

---

## 1. Product summary

Hisaabset is a synthetic-data B2B distributor receivables and retailer-credit decision-support application. It helps a distributor finance manager:

1. Load invoice and receipt data.
2. Normalize and validate inconsistent input formats.
3. Calculate invoice balances using receipts, credit notes, and negotiated settlements.
4. Separate money that is collectible now from money held for dispute review.
5. Track promises to pay and identify broken promises.
6. Rank collectible invoices for follow-up.
7. Produce human-reviewable customer communication drafts.
8. View retailer-level repayment history and a transparent risk rating.
9. Suggest, but never automatically approve, purchasing power and payment terms.
10. Record a separately negotiated next-order recovery agreement.
11. Track only post-agreement recovery against the new target.
12. Export reproducible results and evidence.

The product is intentionally **decision support**, not an autonomous credit, collections, pricing, or dispatch system. It does not send messages, approve credit, block a retailer, dispatch goods, or move money.

---

## 2. Problem and business vocabulary

### 2.1 Main actors

- **Distributor:** Sells goods to retailers and is exposed to unpaid receivables.
- **Retailer/vendor:** Buys goods from the distributor and repays according to invoice or negotiated terms.
- **Finance manager:** Reviews evidence and approves or overrides recommendations.
- **Collections user:** Reviews prioritized invoices and prepares follow-up.

### 2.2 Important terms

- **Invoice amount:** Original billed amount.
- **Applied receipts:** Payments attributable to the invoice and valid as of the selected date.
- **Credit applied:** Reduction from an approved settlement or credit note.
- **Invoice outstanding:** `invoice amount - applied receipts - credit applied`, floored at zero.
- **Collectable amount:** Outstanding balance that can be requested now.
- **Review amount:** Outstanding balance held because of a dispute or unresolved operational issue.
- **BEP (break-even point):** Amount agreed by the business as the minimum recovery reference for a previous bill. Hisaabset records it; it does not infer it.
- **Recovery target:** Amount the parties agree should be recovered under a new next-order agreement.
- **Recovery baseline:** Amount already collected when the recovery agreement is created. It must not satisfy the newly created target.
- **Retailer risk rating:** A low-is-good 0–100 long-term repayment-risk score.
- **Invoice priority score:** A high-is-urgent invoice-level follow-up score. It is not the retailer risk rating.

---

## 3. Design principles and safety boundaries

### 3.1 Evidence before recommendation

Every calculated output should be traceable to source fields, receipts, the selected `as_of` date, and an explicit formula. Explanations are generated in plain language and exports preserve component values.

### 3.2 Human approval for consequential decisions

The system may suggest:

- payment terms,
- purchasing multiplier,
- upfront/credit split,
- next-order eligibility after a negotiated target,
- a follow-up message.

It must not silently convert a suggestion into an approval or external action. Finance approval requires identity, timestamp, and a note for approved credit decisions and negotiated agreements.

### 3.3 Never invent missing invoice facts

PDF extraction can fail or omit a due date. The application asks the user for missing required fields rather than fabricating a date. Uploaded values must be reviewed before collection decisions.

### 3.4 Keep separate concepts separate

These are deliberately different:

1. Invoice outstanding balance.
2. Dispute review amount.
3. Invoice priority.
4. Retailer historical risk.
5. Negotiated recovery target.
6. Next-order credit recommendation.

Changing one must not accidentally rewrite another.

### 3.5 Safe defaults

- New retailers receive **Insufficient history**, not an excellent score.
- New credit recommendations require manager approval.
- Below-BEP recovery targets require an explanation.
- Overpayments are visible and are not silently applied to another invoice.
- Draft communications are marked `DRAFT - not sent`.
- No external messaging or payment integration exists.

---

## 4. Repository architecture

```text
LedgerLoop/
├── app/
│   └── app.py                     Streamlit UI and session orchestration
├── src/
│   ├── loader.py                  Input contracts, parsing, normalization, validation
│   ├── rules.py                   Invoice balances, ageing, promises, priority
│   ├── disputes.py                Review/collectable split and explanations
│   ├── drafts.py                  Human-reviewable follow-up templates
│   ├── export.py                  JSON/CSV/evidence/negotiated exports
│   ├── pdf_invoice.py             Text-PDF extraction into required invoice fields
│   ├── retailer.py                Retailer history, risk, complaints, credit suggestions
│   └── negotiated.py              Next-order recovery agreement and progress
├── data/
│   ├── fixture.json               Original C28 regression fixture
│   ├── extra_synthetic.json       Additional validation edge cases
│   └── real_world_synthetic.json  Broad realistic scenario dataset
├── tests/                         Unit, integration, regression, and export tests
├── docs/
│   ├── TECHNICAL_HANDOFF.md       This canonical technical context
│   ├── MBA_GUIDE.md               Business-oriented explanation
│   ├── CONTEXT.md                 Earlier engineering scope/context
│   ├── PROJECT_REQUIREMENTS.md    Original requirements and phased plan
│   ├── assumptions.md             Observed facts versus assumptions
│   └── reference/                 Supplied product and case documents
├── README.md                      Setup and feature overview
└── requirements.txt               Runtime/test dependencies
```

### 4.1 Dependency direction

```text
app/app.py
 ├── loader.py
 ├── rules.py ── disputes.py
 ├── drafts.py
 ├── retailer.py ── rules.py
 ├── negotiated.py ── loader.py
 └── export.py ── rules.py, negotiated.py
```

The domain modules are mostly pure functions and dataclasses. Streamlit-specific state and rendering belong in `app/app.py`.

---

## 5. Input data contracts

### 5.1 Canonical invoice model

`src/loader.py` defines `Invoice`:

```python
Invoice(
    invoice_id: str,
    customer: str,
    amount: Decimal,
    due_date: date,
    vendor_name: str | None = None,
    vendor_gstin: str | None = None,
    vendor_address: str | None = None,
    vendor_phone: str | None = None,
    vendor_email: str | None = None,
    received_amount: Decimal = Decimal("0.00"),
    invoice_date: date | None = None,
    disputed: bool = False,
    dispute_status: str = "none",
    disputed_amount: Decimal | None = None,
    dispute_cause: str | None = None,
    dispute_resolution: str = "none",
    replacement_delivered: bool = False,
    credit_amount: Decimal = Decimal("0.00"),
    settlement_agreed: bool = False,
    settlement_amount: Decimal | None = None,
    settlement_note: str | None = None,
    promise_made_date: date | None = None,
    promise_date: date | None = None,
    promise_amount: Decimal | None = None,
)
```

Money is represented with `Decimal`, quantized to two decimal places. Dates are ISO `date` values. Do not replace money calculations with binary floating point.

Vendor contact fields remain in the internal model for compatibility, but the current PDF ingestion intentionally does not populate or export them. The product only requires:

- customer,
- invoice number,
- invoice amount,
- invoice date,
- due date,
- already received amount.

### 5.2 Receipt model

```python
Receipt(
    receipt_id: str,
    invoice_id: str | None,
    customer: str | None,
    amount: Decimal,
    receipt_date: date | None = None,
)
```

An invoice can have either:

- an aggregate `received_amount`, or
- detailed receipt rows.

When detailed receipt rows exist for an invoice, they replace the aggregate value for calculations. This prevents double counting.

Receipts with no invoice ID are retained as unapplied receipts. Future-dated receipts are excluded from an earlier `as_of` calculation.

### 5.3 Supported source shapes

The loader accepts JSON and CSV through the application. JSON supports a records object containing `invoices`, `receipts`, and `as_of`. The original fixture uses legacy names such as `id`, `amount_inr`, `received_inr`, and `due`; `FIELD_MAP` translates them into the canonical model.

Loader responsibilities:

1. Parse dates and money.
2. Apply defaults.
3. Validate required fields.
4. Normalize disputes and promises.
5. Detect duplicate invoice IDs.
6. Return `LoadResult` with valid records, errors, metadata, and the selected as-of date.

Invalid input is reported explicitly through validation errors; it is not converted into a success-shaped result.

---

## 6. End-to-end application workflow

### 6.1 Startup

`app/app.py` calls `_initialize_state()`:

1. Loads the default fixture.
2. Stores `LoadResult` in `st.session_state.load_result`.
3. Stores source name and `as_of_date`.
4. Initializes editable draft state.
5. Initializes negotiated agreements.
6. Writes the starting evaluation snapshot.

The Streamlit server reruns the script on UI interaction, so all mutable application data that must survive a rerun is stored in `st.session_state`.

### 6.2 Source upload or manual entry

The sidebar accepts JSON, CSV, or a text-based computer-generated PDF.

PDF flow:

1. Extract text using `pdfplumber` with layout preservation.
2. Fall back to `pypdf` if no usable text is returned.
3. Extract only required fields.
4. Ask the user to fill missing due date or received amount.
5. Build canonical invoice JSON.
6. Pass it through the same loader validation as ordinary input.
7. Append to the current session dataset.
8. Skip duplicate invoice IDs.

Manual invoice flow collects the same required fields and appends to the same dataset. Therefore manually entered and PDF-uploaded invoices appear together in Customers, Your bills, priority views, drafts, and exports.

### 6.3 As-of recalculation

The user selects an `as_of` date. Every evaluation is recalculated from source data for that date. This affects:

- receipt inclusion,
- future invoice detection,
- days overdue,
- ageing bucket,
- promise status,
- invoice state,
- priority score,
- retailer history.

### 6.4 Main navigation

The top navigation contains:

- **Add new bill:** Manual invoice entry and upload.
- **Your bills:** Invoice-level review, detail editing, tables, filters, and exports.
- **Customers:** Retailer history, risk, credit recommendation, complaints, and negotiated recovery.

The sidebar handles source import, date selection, and customer filtering. Styling is implemented in `_inject_styles()` and `.streamlit/config.toml` to maintain a light, high-contrast, elderly-friendly interface.

---

## 7. Invoice balance and state logic

`src/rules.py` is the authoritative invoice evaluation layer.

### 7.1 Applied receipt calculation

```text
if dated detailed receipts exist:
    applied receipts = sum(receipts for invoice where receipt_date <= as_of)
else:
    applied receipts = invoice.received_amount
```

Receipts without a date are allowed by the source contract and are included by the existing rule when attached to the invoice. Future-dated receipts are excluded.

### 7.2 Credit and settlement calculation

```text
if settlement_agreed and settlement_amount exists:
    credit_applied = invoice.amount - settlement_amount
elif dispute_resolution == "credit_note":
    credit_applied = credit_amount
else:
    credit_applied = 0
```

Outstanding:

```text
raw_balance = invoice.amount - applied_receipts - credit_applied
outstanding = max(0, round_money(raw_balance))
overpaid_amount = max(0, round_money(-raw_balance))
```

An overpayment is exposed as an overpayment, not hidden or silently allocated elsewhere.

### 7.3 Dispute split

`src/disputes.py::split_balance()` returns:

```text
(review_amount, collectable_amount)
```

Rules:

- No dispute: all outstanding is collectable.
- Open/pending dispute: disputed amount is held; the rest is collectable.
- Dispute with no amount: the full outstanding balance is held.
- Replacement agreed but not delivered: disputed amount is held.
- Replacement delivered: balance is collectable.
- Credit note: credit is applied and the remaining balance is collectable.

This prevents the application from requesting payment for the amount currently under operational review.

### 7.4 Invoice states

`invoice_state()` chooses one primary state:

- `Paid` when balance is zero.
- `Under Review` when review amount is positive and collectable amount is zero.
- `Promised` when a promise is active and collectable amount is positive.
- `Not due` when the as-of date is on or before due date.
- `Collectable` otherwise.

Future invoices also carry `is_not_yet_issued` when their invoice date is after the as-of date.

### 7.5 Ageing

```text
days_overdue = max(0, as_of - due_date)
```

Buckets:

| Days overdue | Bucket |
|---:|---|
| 0 or less | Not due |
| 1–30 | 1-30 |
| 31–60 | 31-60 |
| 61–90 | 61-90 |
| 91+ | 90+ |

---

## 8. Promise-to-pay logic

A promise needs `promise_made_date` and `promise_date`. `promise_amount` is optional; when missing, the current collectable amount is used.

Promise receipts are counted only when:

```text
promise_made_date <= receipt_date <= as_of
```

Statuses:

- `none`: no valid promise or no collectable balance.
- `active`: promise date has not passed and the promised amount is not fully received.
- `kept`: promised amount has been received.
- `broken`: promise date has passed and a shortfall remains.

The shortfall is:

```text
promise_shortfall = max(0, promised_amount - promised_paid)
```

Important edge case: a fully paid invoice does not need a promise classification for current collection purposes because its collectable amount is zero.

---

## 9. Invoice priority scoring

Priority is invoice-level urgency. A higher score means higher follow-up urgency.

Constants in `src/rules.py`:

```text
W_AGE = 0.45
W_AMOUNT = 0.35
W_PROMISE = 0.20
AGE_CAP = 90
```

The base score is:

```text
age_score = min(days_overdue, 90) / 90
amount_score = collectable_amount / maximum_collectable_amount
promise_score = promise_shortfall / promised_amount
                only when promise is broken

age_points = 100 × 0.45 × age_score
amount_points = 100 × 0.35 × amount_score
promise_points = 100 × 0.20 × promise_score

base = age_points + amount_points + promise_points
```

After 90 overdue days, escalation is applied:

```text
excess_age = min((days_overdue - 90) / 90, 1)
escalation_factor = 0.25 + 0.50 × excess_age
priority = base + (100 - base) × escalation_factor
```

The result preserves component points and explanation text. A dispute held entirely under review should not be ranked as ordinary collectible cash.

---

## 10. Disputes, settlements, and explanations

Supported dispute causes:

- `damaged_goods`
- `short_delivery`
- `wrong_price`
- `other`

Supported resolutions:

- `none`
- `pending`
- `replace_goods`
- `credit_note`

Validation protects against:

- negative disputed or credit amounts,
- disputed amount exceeding the pre-credit balance,
- credit exceeding disputed amount,
- credit-note resolution without a credit amount,
- replacement or credit-note resolution without a cause,
- settlement without a valid settlement amount,
- settlement amount greater than the current balance.

`disputes.explain()` creates a plain-language audit sentence containing:

- invoice amount,
- receipts applied,
- dispute reason and status,
- outstanding,
- collectable amount,
- review amount,
- settlement,
- due date and ageing,
- promise status,
- score components.

This explanation is included in result exports and is intended to make decisions understandable to a finance user.

---

## 11. Follow-up drafts

`src/drafts.py` generates one draft per customer from evaluated invoices.

Priority of draft content:

1. Broken promise: request confirmation of a new date.
2. Collectable invoices:
   - 1–30 days: friendly reminder.
   - 31–60 days: stronger request with date.
   - 60+ days: urgent request to arrange payment or discuss.
3. All promised or not-due: no message, give next check date.
4. All under review: acknowledge investigation.
5. Otherwise: no action message.

If a customer has both collectable and review amounts, the draft asks for the collectable amount while explicitly saying the review amount is not currently being requested.

Every draft is:

```text
status = "DRAFT - not sent"
```

There is no send button or external integration.

---

## 12. Retailer history, risk, and credit recommendation

`src/retailer.py` aggregates invoice evaluations by customer.

### 12.1 History fields

`RetailerHistory` includes:

- invoice count,
- total billed,
- completed invoice count,
- on-time payment count,
- late payment count,
- average days late,
- outstanding balance,
- broken promise count,
- verified retailer-fault complaint count,
- eligibility flag.

An invoice is completed when paid amount plus applicable credit reaches its invoice amount. Missing completion dates are not treated as on-time.

At least three completed invoices are required before a risk score is assigned.

### 12.2 Low-is-good risk score

The rating is 0–100, where low is good and high is risky:

```text
lateness_points = min(35, late_rate × 35)
age_points = min(25, average_days_late / 90 × 25)
balance_points = min(15, outstanding / total_billed × 15)
promise_points = min(15, broken_promises / completed_invoices × 15)
complaint_points = min(10, verified_retailer_fault_complaints × 5)

rating = round_money(
    lateness_points + age_points + balance_points
    + promise_points + complaint_points
)
```

Categories:

| Score | Category |
---:|---|
| 0–10 | Excellent |
| 11–20 | Very good |
| 21–40 | Good |
| 41–50 | Acceptable |
| 51–60 | Moderate |
| 61–70 | Watchlist |
| 71–80 | High risk |
| 81–90 | Very high risk |
| 91–100 | Critical |

Below three completed invoices:

```text
rating = None
category = "Insufficient history"
eligible = False
```

This avoids the unsafe assumption that a new retailer is automatically safe.

### 12.3 Purchasing recommendations

The recommendation maps risk/history to a reference purchasing multiplier and payment split:

| History/rating | Multiplier | Upfront | Credit |
|---|---:|---:|---:|
| New/insufficient history | 1.0× | 50% | 50% |
| 0–10 | 1.8× | 45% | 55% |
| 11–20 | 1.7× | 45% | 55% |
| 21–30 | 1.5× | 50% | 50% |
| 31–50 | 1.3× | 50% | 50% |
| 51–60 | 1.0× | 60% | 40% |
| 61–70 | 0.9× | 70% | 30% |
| 71–80 | 0.8× | 80% | 20% |
| 81–100 | review/full payment | 100% | 0% |

Five or more verified on-time completed payments can support a stronger 40% upfront / 60% credit suggestion. This is still a suggestion, not an approval.

### 12.4 Complaints

Complaint statuses:

- `open`
- `verified_distributor_fault`
- `verified_retailer_fault`
- `inconclusive`
- `inspection_required`
- `closed`

Governance:

- First damaged-goods complaint: accept and investigate.
- Second: distributor validation and explanation required.
- Third or later active complaint: inspection required.
- Verified retailer fault can affect risk.
- Distributor fault does not penalize the retailer.
- No complaint automatically closes the business relationship.

---

## 13. Negotiated next-order recovery

This feature is separate from invoice priority and retailer risk. It records a finance-manager-approved agreement about what must be recovered before or alongside a future order.

### 13.1 Agreement model

`RecoveryAgreement` stores:

- agreement ID,
- retailer,
- previous invoice ID,
- actual BEP,
- recovery floor,
- target type,
- agreed target,
- upfront percentage,
- credit percentage,
- credit period,
- `baseline_collected`,
- agreement date,
- negotiation note,
- status,
- approval identity/time/note.

Target types:

```text
BEP_PLUS_AMOUNT  = actual BEP + agreed additional amount
EXACT_BEP        = actual BEP
BEP_MULTIPLIER   = actual BEP × multiplier
CUSTOM_AMOUNT    = explicit custom amount
```

### 13.2 Target calculation

```python
target = calculate_target(
    target_type,
    bep,
    additional_amount=...,
    multiplier=...,
    custom_amount=...,
)
```

The UI is context-aware:

- Exact BEP asks only for actual BEP, payment split, credit period, and optional note.
- BEP plus amount asks for the extra amount.
- Multiplier asks for the multiplier.
- Custom amount asks for the custom target.

The form first selects a real previous invoice and displays:

- invoice amount,
- collected amount,
- invoice outstanding,
- due date,
- invoice status,
- dispute state,
- promise state.

### 13.3 Validation

Agreement validation rejects:

- missing IDs or retailer,
- negative BEP, floor, baseline, or target,
- payment percentages not totaling 100%,
- non-positive credit period,
- invalid multiplier use,
- target below recovery floor,
- target below BEP without a note,
- approved agreement without manager, timestamp, and approval note.

Approval uses `approve_agreement()` and changes the status to `approved`.

### 13.4 The baseline rule

This is the most important recovery invariant.

When an agreement is created:

```text
baseline_collected = total collected for the selected invoice at agreement creation
```

Later progress:

```text
total_collected_now = detailed receipts if present else invoice.received_amount
recovered_toward_agreement =
    max(0, total_collected_now - baseline_collected)
```

Historical collections are therefore visible but cannot satisfy a new agreement.

Example:

```text
Invoice amount                 ₹10,000
Collected before agreement     ₹4,000
Invoice outstanding             ₹6,000
New exact-BEP target            ₹2,000
New payment after agreement         ₹0

Recovered toward target             ₹0
Target remaining                 ₹2,000
Invoice outstanding             ₹6,000
Invoice balance after target     ₹4,000
```

The UI intentionally exposes these as separate labels:

- `Collected before agreement`
- `Recovered`
- `Target remaining`
- `Invoice outstanding`
- `Invoice balance after target payment`

This prevents the historical ₹4,000 from being mistaken for recovery against the new ₹2,000 target.

### 13.5 Recovery statuses

```text
agreement_draft
pending_finance_approval
approved
partially_recovered
target_reached
target_exceeded
missed
cancelled
```

Progress fields:

- recovered amount after baseline,
- target remaining,
- excess amount,
- invoice outstanding,
- invoice balance after target,
- current status,
- next-order eligibility.

Next-order eligibility is true only when the target is reached or exceeded. This does not automatically authorize the order.

### 13.6 What this feature does not do

- It does not change the source invoice’s normal balance calculation.
- It does not automatically reassign excess recovery to another invoice.
- It does not calculate BEP from product economics.
- It does not approve a retailer’s credit.
- It does not dispatch goods.
- It does not authorize a payment.

The finance manager must enter the negotiated BEP, target, payment split, and approval evidence.

---

## 14. PDF extraction design

`src/pdf_invoice.py` supports text-based, computer-generated invoices.

Extraction backends:

1. `pdfplumber` with `layout=True` as primary.
2. `pypdf` as fallback when layout extraction returns no text.

The parser uses label-aware patterns for:

- invoice number,
- invoice date,
- due date,
- total amount,
- customer/client.

It also exposes table extraction for audit/future line-item work, but the current application does not import arbitrary line items.

PDFs often contain vendor GSTIN, address, phone, email, tax lines, and totals. The parser deliberately returns only the required six fields. This prevents irrelevant vendor information from contaminating customer/invoice forms.

Limitations:

- Scanned image PDFs require OCR and are not supported.
- One text-based invoice per upload is the supported flow.
- A missing due date is a review/error condition; it is not guessed.
- Received amount normally cannot be inferred from an invoice PDF and is entered manually.

---

## 15. Streamlit state and UI behavior

Important state keys:

```text
load_result
source_name
as_of_date
reviewed_drafts
draft_text
negotiated_agreements
```

When a new source is appended:

1. Existing invoices and receipts are preserved.
2. Duplicate invoice IDs are skipped.
3. Source name is combined.
4. Draft review state is reset.
5. Negotiated agreements are reset because the selected data context changed.

When a manual invoice is added:

1. The form validates required fields.
2. The new invoice is appended to `load_result.invoices`.
3. It becomes visible in all normal calculations.
4. Duplicate IDs are rejected/skipped.

When an invoice detail is edited:

1. A candidate invoice is built from UI inputs.
2. Dispute and settlement fields are validated.
3. The existing invoice is replaced in session state only after validation.
4. The next Streamlit rerun recalculates all evaluations.

The app has a custom light theme, high-contrast controls, visible table toolbar labels, top navigation, rounded cards, and large controls intended to be usable by elderly or less technical users.

---

## 16. Exports and auditability

The export action writes:

```text
output/result.json
output/result.csv
output/negotiated_recovery.json
output/evidence_log.md
```

### 16.1 `result.json` and `result.csv`

Each invoice record includes source fields plus:

- applied receipts,
- credit applied,
- outstanding,
- overpaid amount,
- ageing,
- review/collectable split,
- state,
- promise status,
- promise shortfall,
- broken-promise flag,
- score and component points,
- explanation.

### 16.2 `negotiated_recovery.json`

Each agreement record includes:

- agreement inputs,
- approval evidence,
- baseline,
- recovered amount,
- target remaining,
- excess,
- invoice outstanding,
- invoice balance after target,
- recovery status,
- next-order eligibility.

### 16.3 Evidence log

The evidence log records starting state, negotiated scope, tests supplied, state counts, validation errors, and observed-versus-assumed boundaries.

Exports convert `Decimal` to fixed two-decimal strings and dates/timestamps to ISO strings to remain JSON-safe and reproducible.

---

## 17. Synthetic scenarios

`data/real_world_synthetic.json` intentionally covers:

- partial payment,
- fully paid invoice,
- open dispute,
- replacement requested,
- replacement delivered,
- credit note,
- active promise,
- kept promise,
- broken promise,
- negotiated settlement,
- overpayment,
- future invoice,
- high-risk ageing,
- unapplied receipt,
- future receipt.

The test suite validates that these scenarios remain distinguishable. Do not simplify the fixture to only happy-path paid/unpaid invoices; the edge cases are part of the product requirements.

---

## 18. Testing and current validation

Run:

```powershell
python -m pytest -q
python -m compileall -q app src tests
git diff --check
```

Current verified result at the time this document was written:

- **76 tests passed**
- Python compilation passed
- `git diff --check` passed
- Streamlit health endpoint returned `HTTP 200 ok`
- Intended single app port: `8501`

Important regression tests include:

- original C28 balances and priority order,
- duplicate and invalid input,
- date and money validation,
- disputes and credit notes,
- settlement reductions,
- promise states,
- PDF extraction,
- retailer risk bands,
- complaint controls,
- synthetic scenario behaviors,
- negotiated target types,
- finance approval,
- partial/exact/excess recovery,
- historical baseline not satisfying a new recovery target,
- JSON-safe negotiated export.

When changing a core calculation, add a failing regression test first, then update the smallest relevant domain function and rerun the full suite.

---

## 19. Known assumptions and limitations

1. All data is synthetic; no production-readiness claim is made.
2. BEP is entered by the finance manager; the application does not derive product cost or margin.
3. Retailer risk requires three completed invoices.
4. Receipt rows supersede aggregate received amount when present.
5. Missing receipt dates are accepted by the current contract; future enhancement may require a stricter policy.
6. Scanned PDFs require a future OCR phase.
7. PDF extraction is designed for common computer-generated invoice layouts, not arbitrary documents.
8. The app is session-based; there is no production database or multi-user persistence.
9. Approval is recorded in application state/export, not integrated with an identity provider.
10. There is no payment gateway, ERP, WhatsApp, email, or dispatch integration.
11. Streamlit emits `use_container_width` deprecation warnings in the current version; these are unrelated to domain correctness.
12. Existing in-memory agreements created before `baseline_collected` was introduced may have a zero baseline. Restarting Streamlit clears session state and newly created agreements capture the correct baseline.

---

## 20. Safe extension guide

### Add a new invoice field

1. Add it to `Invoice`.
2. Add parsing and validation in `loader.py`.
3. Add manual UI input in `app/app.py`.
4. Add PDF extraction only if the field is reliably present.
5. Add the field to exports.
6. Add focused loader/UI/export tests.
7. Document whether it changes balances or only provides context.

### Change a balance rule

1. Add a failing `rules.py` test for the exact scenario.
2. Confirm interaction with detailed receipts, credit notes, settlements, disputes, and overpayments.
3. Update `rules.py`, not a UI-only workaround.
4. Update `disputes.py` explanations if user-visible meaning changes.
5. Update exports and documentation.
6. Run the full suite.

### Change retailer risk or credit terms

1. Preserve the distinction between invoice priority and retailer risk.
2. Keep low-is-good risk semantics unless the UI and all documentation are changed together.
3. Do not treat insufficient history as excellent.
4. Keep recommendations separate from approval.
5. Add boundary tests for every rating band.

### Change negotiated recovery

1. Preserve the baseline invariant.
2. Keep invoice outstanding and recovery target remaining as separate values.
3. Do not use historical collections as new-agreement recovery.
4. Validate payment split totals and below-BEP reasons.
5. Add tests for zero, partial, exact, and excess post-agreement payments.
6. Update `negotiated_record()` and UI labels together.

### Add persistence

The current session-state approach is intentionally simple. A production persistence layer should introduce:

- immutable invoice/receipt records,
- agreement versioning,
- audit events,
- user identity and roles,
- optimistic concurrency,
- database migrations,
- tenant isolation,
- encryption and access controls.

Do not silently replace session state with a database without preserving the current calculation semantics and tests.

---

## 21. Guidance for a future AI model

Before editing this project, the AI should understand these invariants:

1. The product is Hisaabset, although the repository is named LedgerLoop.
2. The app is a Streamlit decision-support tool, not an autonomous collections or credit engine.
3. `src/rules.py` is the source of truth for invoice balances and priority.
4. `src/retailer.py` is the source of truth for retailer history/risk/recommendations.
5. `src/negotiated.py` is the source of truth for next-order recovery.
6. Detailed receipts replace aggregate received amount for calculations.
7. Historical receipts before a recovery agreement are captured in `baseline_collected` and cannot satisfy the new target.
8. Invoice outstanding and negotiated target remaining are different numbers and must be shown separately.
9. Disputed money can be under review and should not be requested as normal collection.
10. A promise can be active, kept, or broken; a fully paid invoice has no current collectable promise work.
11. Risk scores are low-is-good and need at least three completed invoices.
12. Recommendations require finance-manager approval.
13. Below-BEP negotiated targets require a note.
14. No draft is sent automatically.
15. Missing PDF facts must be requested, not invented.
16. New behavior requires tests and documentation.

When investigating a bug, reproduce it with a focused test or runtime scenario before changing code. Prefer fixing the producer of an incorrect value over masking it in the UI. Preserve `Decimal` arithmetic, explicit validation, audit fields, and the separation of independent business concepts.

---

## 22. Executable scenario catalog and data-entry workflows

This section is the practical test manual. A future AI should use these
scenarios to reproduce behavior before changing any calculation. The sample
files are synthetic and already exist in the repository:

- [`data/extra_synthetic.json`](../data/extra_synthetic.json): compact
  validation and edge-case pack.
- [`data/real_world_synthetic.json`](../data/real_world_synthetic.json):
  complete retailer workflow pack.

### 22.1 Universal upload workflow

To run any JSON scenario:

1. Start the app:

   ```powershell
   python -m streamlit run app/app.py --server.port 8501
   ```

2. Open `http://localhost:8501`.
3. In the left sidebar under **Import data**, upload the scenario JSON.
4. If the app asks whether to append or replace, use the intended test mode:
   - **Replace/new session:** best for deterministic scenario testing.
   - **Append:** best for testing manual/PDF data joining with existing data.
5. Confirm the displayed source and selected `as_of` date.
6. Open **Your bills** and inspect the invoice table.
7. Select an invoice in **Invoice detail** for editable dispute, promise,
   received amount, due date, and settlement fields.
8. Open **Customers** for retailer history, risk, complaints, and negotiated
   recovery.
9. Use the export action after the expected result is visible.

For deterministic fixture tests, the `as_of` date must match the file:

| File | Required as-of date |
|---|---|
| `extra_synthetic.json` | 2026-10-16 |
| `real_world_synthetic.json` | 2026-10-18 |

Changing the as-of date intentionally changes receipt inclusion, ageing,
promise status, invoice state, and priority.

### 22.2 Compact edge-case pack

Upload [`data/extra_synthetic.json`](../data/extra_synthetic.json). It contains
the following exact records:

```json
{
  "as_of": "2026-10-16",
  "invoices": [
    {
      "id": "SYN-PARTIAL",
      "customer": "Synthetic A",
      "amount_inr": 10000,
      "received_inr": 4000,
      "due": "2026-10-01",
      "disputed": false
    },
    {
      "id": "SYN-DISPUTE",
      "customer": "Synthetic B",
      "amount_inr": 10000,
      "received_inr": 0,
      "due": "2026-10-01",
      "disputed": true,
      "dispute_status": "open",
      "disputed_amount": 2000,
      "dispute_cause": "damaged_goods",
      "dispute_resolution": "pending"
    },
    {
      "id": "SYN-PROMISE",
      "customer": "Synthetic C",
      "amount_inr": 8000,
      "received_inr": 0,
      "due": "2026-09-01",
      "disputed": false,
      "promise_made_date": "2026-10-01",
      "promise_date": "2026-10-10",
      "promise_amount": 8000
    },
    {
      "id": "SYN-INVALID",
      "customer": "Synthetic Invalid",
      "amount_inr": -1,
      "received_inr": 0,
      "due": "2026-10-01",
      "disputed": false
    }
  ],
  "receipts": [
    {
      "receipt_id": "SYN-R1",
      "invoice_id": "SYN-PARTIAL",
      "customer": "Synthetic A",
      "amount": 1000,
      "receipt_date": "2026-10-05"
    },
    {
      "receipt_id": "SYN-UNAPPLIED",
      "invoice_id": "",
      "customer": "Synthetic A",
      "amount": 500,
      "receipt_date": "2026-10-05"
    },
    {
      "receipt_id": "SYN-FUTURE",
      "invoice_id": "SYN-PARTIAL",
      "customer": "Synthetic A",
      "amount": 1000,
      "receipt_date": "2026-11-01"
    }
  ]
}
```

Expected tests:

| Case | Where to test | Expected behavior |
|---|---|---|
| `SYN-PARTIAL` | Your bills → invoice table | Detailed receipt `1000` replaces aggregate `received_inr=4000`; outstanding is `9000`, not `5000`. |
| `SYN-DISPUTE` | Your bills → Invoice detail | Outstanding `10000`; disputed/review `2000`; collectable `8000`; damage reason is shown. |
| `SYN-PROMISE` | Your bills → Invoice detail | Promise date has passed with no receipt, so promise is broken and shortfall is `8000`. |
| `SYN-INVALID` | Upload result/error area | Negative invoice amount is rejected with a validation error. |
| `SYN-UNAPPLIED` | Your bills → unapplied receipts view | Receipt remains visible but does not reduce any invoice. |
| `SYN-FUTURE` | Change as-of to 2026-10-16 | Future receipt is excluded; change as-of to 2026-11-02 to include it. |

The `SYN-PARTIAL` result is intentionally non-obvious. The detailed receipt
list supersedes the aggregate invoice value. This is a regression case, not a
data mistake.

### 22.3 Complete real-world pack: exact invoice records

Upload [`data/real_world_synthetic.json`](../data/real_world_synthetic.json)
with as-of date `2026-10-18`. The exact invoice inputs are:

| ID | Customer | Amount | Aggregate received | Invoice date | Due date | Special fields |
|---|---|---:|---:|---|---|---|
| `RW-001-PARTIAL` | Aarav General Store | 100000 | 40000 | 2026-08-15 | 2026-09-15 | no dispute; detailed receipt also exists |
| `RW-002-PAID-ONTIME` | Aarav General Store | 75000 | 75000 | 2026-08-01 | 2026-09-01 | paid; receipt dated 2026-08-30 |
| `RW-003-DISPUTE-OPEN` | Bharat Retail Hub | 90000 | 10000 | 2026-08-20 | 2026-09-20 | open damage dispute; disputed 30000; pending |
| `RW-004-REPLACEMENT` | Bharat Retail Hub | 60000 | 0 | 2026-08-10 | 2026-09-10 | damage; replacement delivered |
| `RW-005-CREDIT-NOTE` | Chaitanya Pharmacy | 80000 | 20000 | 2026-07-15 | 2026-08-15 | short delivery; credit note 15000 |
| `RW-006-PROMISE-ACTIVE` | Deepak Supermart | 110000 | 20000 | 2026-09-01 | 2026-10-01 | promise 90000 due 2026-10-25 |
| `RW-007-PROMISE-BROKEN` | Deepak Supermart | 50000 | 0 | 2026-07-01 | 2026-08-01 | promise 50000 due 2026-09-15; receipt only 5000 |
| `RW-008-PROMISE-KEPT` | Esha Wholesale Mart | 60000 | 0 | 2026-08-01 | 2026-09-01 | promise 45000 due 2026-09-20; receipt 45000 |
| `RW-009-SETTLEMENT` | Farhan Convenience Store | 120000 | 0 | 2026-07-01 | 2026-08-01 | settlement agreed; payable 90000 |
| `RW-010-OVERPAID` | Gopal Traders | 30000 | 35000 | 2026-09-01 | 2026-10-01 | overpayment 5000 |
| `RW-011-FUTURE` | Hema New Retailer | 70000 | 0 | 2026-10-20 | 2026-11-20 | invoice date is after 2026-10-18 |
| `RW-012-HIGH-RISK` | Indus Market | 150000 | 0 | 2026-03-01 | 2026-04-01 | severely overdue |

The corresponding exact receipt inputs are:

| Receipt ID | Invoice ID | Customer | Amount | Receipt date | Expected use |
|---|---|---|---:|---|---|
| `RW-R001` | `RW-001-PARTIAL` | Aarav General Store | 10000 | 2026-10-01 | Replaces aggregate received value for calculation; outstanding becomes 90000. |
| `RW-R002` | `RW-006-PROMISE-ACTIVE` | Deepak Supermart | 20000 | 2026-10-12 | Counts toward active promise; promise remains short by 70000. |
| `RW-R003` | `RW-007-PROMISE-BROKEN` | Deepak Supermart | 5000 | 2026-09-20 | Counts after promise date; broken shortfall becomes 45000. |
| `RW-R004` | `RW-008-PROMISE-KEPT` | Esha Wholesale Mart | 45000 | 2026-09-20 | Fully satisfies the 45000 promise. |
| `RW-R005` | `RW-002-PAID-ONTIME` | Aarav General Store | 75000 | 2026-08-30 | Confirms payment before due date. |
| `RW-R006` | *(empty)* | Unknown Retailer | 12500 | 2026-10-05 | Unapplied receipt; never reduces an invoice. |
| `RW-R007` | `RW-001-PARTIAL` | Aarav General Store | 5000 | 2026-11-01 | Future at as-of 2026-10-18; excluded until as-of passes it. |

### 22.4 Expected outputs for every real-world invoice

Use the **Your bills** table and invoice detail panel. Values below are
calculated for `as_of=2026-10-18`.

| ID | Expected balance/state | What to verify |
|---|---|---|
| `RW-001-PARTIAL` | Applied receipts `10000`; outstanding `90000`; collectable `90000`; collectable/overdue | Detailed receipt replacement rule; aggregate 40000 is not added to 10000. |
| `RW-002-PAID-ONTIME` | Applied `75000`; outstanding `0`; state `Paid` | On-time receipt and zero balance. |
| `RW-003-DISPUTE-OPEN` | Outstanding `80000`; review `30000`; collectable `50000`; overdue | Open damage dispute holds only the disputed amount. |
| `RW-004-REPLACEMENT` | Outstanding `60000`; review `0`; collectable `60000`; overdue | Replacement delivered means the disputed amount is no longer held. |
| `RW-005-CREDIT-NOTE` | Applied `20000`; credit `15000`; outstanding `45000`; collectable `45000` | Credit note reduces balance and is not a review hold. |
| `RW-006-PROMISE-ACTIVE` | Applied detailed receipts `20000`; outstanding `90000`; promise active; shortfall `70000` | Active promise appears as `Promised`; it is not yet classified broken on 2026-10-18. |
| `RW-007-PROMISE-BROKEN` | Applied `5000`; outstanding `45000`; broken promise; shortfall `45000` | Broken promise contributes to priority and draft wording. |
| `RW-008-PROMISE-KEPT` | Applied `45000`; outstanding `15000`; promise kept | Promise is kept even though the invoice itself remains partly unpaid. |
| `RW-009-SETTLEMENT` | Settlement payable `90000`; outstanding `30000` | Settlement credit is `30000`; payable balance is not zero unless 90000 is collected. |
| `RW-010-OVERPAID` | Outstanding `0`; overpaid amount `5000`; state `Paid` | Excess is exposed, not allocated elsewhere. |
| `RW-011-FUTURE` | Outstanding `70000`; not-yet-issued flag true; not due | Future invoice must not be treated as overdue collection. |
| `RW-012-HIGH-RISK` | Outstanding `150000`; `90+` ageing; highest urgency candidate | Age escalation and high outstanding amount. |

### 22.5 Retailer and complaint workflow

Open **Customers** after uploading the real-world pack.

The pack contains these complaint records:

| Complaint ID | Retailer | Invoice | Status | Where to inspect |
|---|---|---|---|---|
| `RW-C001` | Bharat Retail Hub | `RW-003-DISPUTE-OPEN` | `open` | Customers → complaint evidence |
| `RW-C002` | Bharat Retail Hub | `RW-004-REPLACEMENT` | `verified_distributor_fault` | Customers → complaint evidence; must not penalize retailer |
| `RW-C003` | Indus Market | `RW-012-HIGH-RISK` | `inspection_required` | Customers → inspection escalation |

Expected workflow:

1. Select Bharat Retail Hub.
2. Confirm invoice count and outstanding evidence.
3. Confirm complaints are visible and distributor-fault complaints are not
   counted as retailer-fault risk.
4. Select Indus Market.
5. Confirm the inspection-required case is a governance signal, not an
   automatic account closure.
6. Because most sample retailers have fewer than three completed invoices,
   many will show **Insufficient history**. This is correct.
7. To test an eligible risk score, use at least three completed invoices for
   one customer or add three manual invoices and receipts for the same
   retailer. Do not change the minimum-history rule just to make the demo show
   a numeric score.

### 22.6 Manual invoice-entry workflow

Use **Add new bill → Manual entry**. Enter all required fields:

| UI field | Sample value |
|---|---|
| Customer name | `Manual Test Retailer` |
| Invoice number | `MANUAL-001` |
| Invoice amount | `10000` |
| Invoice date | `2026-10-01` |
| Due date | `2026-10-31` |
| Already received amount | `4000` |

Save the form, then verify:

1. `MANUAL-001` appears in **Your bills**.
2. It appears under **Customers → Manual Test Retailer**.
3. Outstanding is `6000`.
4. It is included in exports.
5. A duplicate `MANUAL-001` is rejected or skipped rather than duplicated.

To test optional cases through the invoice-detail editor:

| Case | Invoice detail fields to enter | Expected result |
|---|---|---|
| Changed due date | Agreed due date `2026-11-15` | Ageing recalculates from the new due date. |
| Settlement | Check “Customer agreed to settle for less”; final amount `8000`; note | Outstanding becomes payable settlement amount semantics; note is exported. |
| Open damage dispute | Disputed amount `2000`; cause `damaged_goods`; resolution `pending` | Review `2000`, collectable is the remainder. |
| Replacement pending | Cause `damaged_goods`; resolution `replace_goods`; replacement unchecked | Disputed amount remains under review. |
| Replacement completed | Same fields; replacement checked | Held amount becomes collectable. |
| Credit note | Cause `short_delivery`; resolution `credit_note`; credit amount `1000` | Balance is reduced by the credit. |
| Promise | Promise made `2026-10-18`; promise date `2026-10-25`; promise amount `5000` | Promise is active until the date passes or enough payment is recorded. |

### 22.7 PDF-entry workflow

Use **sidebar → Import data → upload PDF** with a computer-generated invoice
such as [`invoice_51109301.pdf`](../data/source_documents/invoice_51109301.pdf).

1. Upload one PDF.
2. Confirm extracted invoice number, customer, amount, and invoice date.
3. If due date is absent, enter **Manual due date if PDF has no due date**.
4. Enter **Already received amount** manually; for a new invoice use `0`.
5. Confirm only the required invoice fields are persisted.
6. Verify vendor GST, address, phone, and email are not being treated as
   customer or invoice fields.
7. Verify the invoice joins the same Your bills and Customers workflow as a
   manual invoice.

Negative PDF tests:

- Upload a scanned/image-only PDF: expect an extraction error explaining that
  selectable text/OCR is required.
- Upload a PDF without due date and leave manual due date empty: expect a
  required due-date error, not an invented date.
- Upload the same invoice ID already in session: expect duplicate handling.

### 22.8 Negotiated recovery workflow

Use **Customers → select retailer → Negotiated next-order condition**.
Select a previous invoice and confirm the invoice evidence first.

#### Exact BEP baseline regression

Create a manual invoice:

```text
Invoice ID: BASELINE-001
Customer: Recovery Test Retailer
Invoice amount: 10000
Already received amount: 4000
Due date: 2026-09-01
```

Then create an agreement:

```text
Previous invoice: BASELINE-001
Target type: Exactly the BEP amount
Actual BEP: 2000
Next-order upfront: 50%
Credit period: 90 days
Negotiation note: Exact historical BEP recovery test
```

Before any new receipt, expected display:

```text
Collected before agreement: 4000
Recovered toward agreement: 0
Target: 2000
Target remaining: 2000
Invoice outstanding: 6000
Invoice balance after target payment: 4000
```

Add a new receipt of `1000` dated `2026-10-19`, move as-of to
`2026-10-20`, and verify:

```text
Recovered toward agreement: 1000
Target remaining: 1000
Invoice outstanding: 5000
Invoice balance after target payment: 3000
```

Add another `1000` post-agreement receipt and verify target reached and
next-order eligibility becomes true only after finance approval. Add a further
`500` to test `target_exceeded` and `excess_amount=500`.

#### Other target types

| Target type | Data to enter | Expected target |
|---|---|---:|
| BEP plus amount | BEP `15000`, additional amount `5000` | `20000` |
| Exact BEP | BEP `15000` | `15000` |
| BEP multiplier | BEP `15000`, multiplier `0.8` | `12000`; below-BEP note is required |
| Custom amount | Custom target `18000`, recovery floor `15000` | `18000` |

For every agreement, test:

1. Save without required target fields: clear validation error.
2. Enter upfront `60%` and credit `50%`: total validation error.
3. Enter a target below the floor: validation error.
4. Enter a below-BEP target without a note: validation error.
5. Approve without manager name or approval note: validation error.
6. Approve with manager `Finance Manager`, current timestamp, and reason:
   agreement becomes approved.
7. Confirm export contains baseline, approval evidence, recovery status, and
   both balance values.

### 22.9 AI test execution checklist

When a future AI receives a bug report, it should:

1. Identify the smallest matching scenario ID.
2. Load the corresponding fixture or enter the exact manual values.
3. Use the documented as-of date.
4. Record the observed values for:
   - applied receipts,
   - credit,
   - outstanding,
   - review,
   - collectable,
   - state,
   - promise,
   - priority,
   - recovery progress if applicable.
5. Compare observed output with the expected table above.
6. Add or update a focused regression test reproducing the discrepancy.
7. Fix the domain producer (`loader.py`, `rules.py`, `retailer.py`, or
   `negotiated.py`) rather than formatting the wrong value in the UI.
8. Run:

   ```powershell
   python -m pytest -q
   python -m compileall -q app src tests
   git diff --check
   ```

9. Update this scenario catalog whenever the expected behavior or data
   contract intentionally changes.

---

## 23. Approved email communication implementation

The current communication channel is Amazon SES email. The implementation is
in [`src/communications.py`](../src/communications.py), and the UI integration
is in `app/app.py` under `_render_drafts()`.

### 23.1 Current behavior

For every generated customer draft:

1. The application displays the editable subject and body.
2. The subject includes the exact collectable amount when a payment is due.
3. A customer email field is displayed.
4. Aarav General Store is initially assigned
   `unnamedinsect424@gmail.com` for the requested test setup.
5. The finance user must check:
   **I reviewed the exact figures and approve this email**.
6. Only then is **Approve and send email** enabled.
7. SES validates recipient, sender, subject, and body.
8. The result is explicitly shown as sent, test-blocked, or failed.

Approval is per Streamlit session and is not an identity-provider approval.
Before production, communication approval should be persisted with user
identity, timestamp, exact body, invoice IDs, and an immutable audit event.

### 23.2 Test mode safety

Email delivery is disabled unless:

```text
HISAABSET_EMAIL_TEST_MODE=false
```

The default is effectively `true`. In test mode, the UI still exercises the
review and approval path but `send_via_ses()` returns `test_blocked` and does
not call AWS.

Required live configuration:

```text
HISAABSET_EMAIL_SENDER=unnamedinsect424@gmail.com
AWS_REGION=<SES region>
HISAABSET_EMAIL_TEST_MODE=false
```

AWS credentials must be supplied through the standard AWS credential chain.
They must never be committed to the repository or entered into a fixture. The
sender must be verified in SES. In SES sandbox mode, the recipient must also
be verified.

### 23.3 SES result handling

`send_via_ses()` returns a `SendResult`:

```text
sent         SES accepted the request; provider message ID is shown
test_blocked delivery intentionally prevented by test mode
failed       validation, configuration, missing dependency, or SES error
```

The current implementation uses a lazy `boto3` import so the application can
show a clear dependency error. AWS SDK/client errors are caught explicitly and
are not hidden as successful sends.

### 23.4 First safe test

1. Keep `HISAABSET_EMAIL_TEST_MODE=true`.
2. Upload the real-world synthetic fixture.
3. Open **Your bills → Drafts**.
4. Select Aarav General Store's draft.
5. Confirm the exact amount in the subject/body.
6. Confirm recipient `unnamedinsect424@gmail.com`.
7. Check the approval checkbox.
8. Click **Approve and send email**.
9. Verify the UI says test mode blocked and no message was delivered.

Only after SES identity verification, AWS permissions, and a controlled
recipient test should live mode be enabled. The first live test should still
send to an address the finance team owns.

### 23.5 Security and product rules

- Do not use a personal Gmail password, browser automation, or unofficial
  email scraping.
- Do not put AWS access keys in Python files, JSON fixtures, README files, or
  committed Streamlit secrets.
- Do not send drafts for open disputes as ordinary payment demands without
  finance review.
- Do not send future-invoice reminders.
- Do not auto-send settlement or below-BEP negotiation messages without a
  separate explicit approval policy.
- SES acceptance is not proof that the customer read or paid the message. A
  future phase should persist provider events and bounces.

### 23.6 Test coverage

`tests/test_communications.py` covers valid and invalid email addresses, test
mode preventing delivery, and live mode requiring an AWS region. Existing
draft tests continue to cover exact collectable figures and case-specific
message wording. Future production work should add mocked SES request tests,
duplicate-send protection, bounce handling, and durable communication audit
records.

---

## 24. AWS Docker deployment bundle

The repository includes a secret-free deployment bundle:

```text
deploy/docker/streamlit.Dockerfile
.dockerignore
.env.example
deploy/aws/
├── README.md
├── deploy.ps1
├── hisaabset-ses-task-policy.json
└── hisaabset-task-definition.template.json
```

The Docker image uses `python:3.14-slim`, installs `requirements.txt`, runs as
non-root user `appuser`, listens on `0.0.0.0:8501`, and exposes the Streamlit
health endpoint at `/_stcore/health`. The ECS task template defaults email
delivery to test mode.

Build and smoke test:

```powershell
docker build -t hisaabset:local .
docker run --rm -p 8501:8501 `
  -e AWS_REGION=ap-south-1 `
  -e HISAABSET_EMAIL_SENDER=unnamedinsect424@gmail.com `
  -e HISAABSET_EMAIL_TEST_MODE=true `
  hisaabset:local
```

`deploy/aws/deploy.ps1` resolves the AWS account with STS, logs Docker into
private ECR, builds and pushes the image, and renders the ECS Fargate task
definition:

```powershell
.\deploy\aws\deploy.ps1 -Region ap-south-1 -Tag v1
```

The default keeps `HISAABSET_EMAIL_TEST_MODE=true`. Use `-LiveEmail` only
after SES identity verification, IAM task-role setup, recipient verification
or production access, and a controlled test:

```powershell
.\deploy\aws\deploy.ps1 -Region ap-south-1 -Tag v1 -LiveEmail
```

The rendered task definition is ignored by Git because it contains
account-specific deployment values. No AWS access key, secret, root
credential, or password belongs in this repository.

The ECS task policy allows only `ses:SendEmail` and restricts the sender to
`unnamedinsect424@gmail.com`. The container uses an ECS IAM task role, so AWS
credentials are not needed in application environment variables.

---

## 25. Production foundation and remaining phases

The repository now includes a separate `backend/` production foundation. It is
deliberately kept outside the Streamlit calculation modules so the existing
domain rules remain the source of truth. The foundation currently provides:

1. PostgreSQL-compatible SQLAlchemy models for invoices, receipts, and audit
   events.
2. Organization-scoped invoice reads and writes.
3. Cognito/OIDC JWT validation hooks using issuer, audience, and JWKS settings.
4. Role checks for `finance_admin`, `finance_manager`, `collector`, and
   `auditor`.
5. Audit recording for API invoice creation.
6. A health endpoint and non-root backend container.
7. An explicit seed command for the current demo fixture.

This foundation is not a production launch claim by itself. Before go-live,
configure Cognito, use managed PostgreSQL rather than the development SQLite
fallback, add versioned migrations, deploy behind TLS and an ALB, configure
backups/restore testing, centralize logs and metrics, and complete an
independent security and access-control review.

Recommended remaining phases:

1. Integrate Streamlit with the authenticated API and remove direct
   session-state persistence for production records.
2. Add durable receipt uploads, source-file storage, validation-result
   persistence, and controlled export storage in S3.
3. Add versioned invoice edits, optimistic concurrency, and complete append-only
   audit coverage for disputes, promises, drafts, credit decisions, negotiated
   agreements, and email approvals.
4. Add role-based finance-manager approval and duplicate-send protection for
   SES.
5. Add Alembic migrations, secret management, TLS/ALB, backups, monitoring,
   alerting, retention/deletion workflows, and disaster-recovery exercises.
6. Add OCR for scanned invoices, receipt allocation, policy-versioned risk
   weights, and formal timezone-aware approval timestamps.
7. Add stronger PDF template configuration and extraction confidence.
8. Add product-level BEP and margin capture.
9. Add payment gateway or bank-statement reconciliation only behind explicit
   approval workflows.
10. Add automated UI testing for accessibility and visual regressions.

Any future automation must retain the current safety rule: the application may recommend, explain, and prepare; a responsible finance user must approve consequential actions.
