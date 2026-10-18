# LedgerLoop: MBA Student Guide

## 1. What is LedgerLoop?

LedgerLoop is a small receivables follow-up desk for a distributor. It helps a
finance team decide:

- how much money is still unpaid;
- how much can safely be requested now;
- how much should be held because of a customer dispute;
- which customers or invoices deserve attention first;
- whether a payment promise is active, kept, or broken; and
- what a human could send after reviewing a prepared draft.

The application is a decision-support prototype. It is not an accounting
system, payment gateway, credit-risk model, CRM, or messaging system.

All supplied data is synthetic. The application never sends an email,
WhatsApp message, SMS, payment request, or external API call.

## 2. Why this problem matters to an MBA student

Receivables affect working capital and cash-flow visibility. A business may
show revenue on its books while still waiting for customers to pay. However,
the entire outstanding balance cannot always be chased:

- part of an invoice may be genuinely disputed;
- a customer may have promised to pay later;
- a receipt may not be safely matched to an invoice; or
- the invoice may not yet be due.

LedgerLoop separates these cases instead of treating every unpaid invoice as a
collection failure. This gives an MBA team a practical way to discuss:

- working-capital discipline;
- order-to-cash operations;
- customer relationship management;
- dispute resolution;
- collections prioritisation;
- process controls and auditability; and
- the difference between a prototype and a production product.

## 3. The business vocabulary

| Term | Meaning |
|---|---|
| Invoice | A bill raised for goods or services |
| Receipt | Money received from a customer |
| Outstanding | Balance remaining after receipts and approved credits |
| Collectable | Outstanding money that is currently safe to request |
| Under review | Money held because the customer has a dispute |
| Ageing | How many days an invoice is past its due date |
| Promise-to-pay | A customer commitment to pay a specified amount by a date |
| Unapplied receipt | Money received but not safely linked to an invoice |
| Draft plan | A customer-level message prepared for human review |
| As-of date | The date on which the receivables position is measured |

## 4. The complete business flow

The application follows this sequence:

```text
Load invoice and receipt data
        ↓
Validate and normalize the input
        ↓
Calculate receipts, credits, and outstanding balances
        ↓
Separate disputed money from collectible money
        ↓
Calculate due status and ageing
        ↓
Evaluate payment promises
        ↓
Rank collectible invoices
        ↓
Prepare customer-level draft plans
        ↓
Human reviews and edits the drafts
        ↓
Export results and evidence
```

The finance user should not begin by writing messages. The correct sequence is
to establish a reliable balance first, understand exceptions second, and only
then decide how to follow up.

## 5. Starting the application

From the project folder, run:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Open `http://localhost:8501` in a browser. The default input is
`data/fixture.json`.

The Streamlit interface is implemented in `app.py`. Business calculations are
kept in the `src` modules so that the rules can be tested independently of the
screen.

## 6. Input data

### 6.1 Default C28 fixture

The default fixture contains six synthetic invoices, one global as-of date,
INR values, and aggregated receipt amounts. Its important fields are:

| Starter field | Business meaning |
|---|---|
| `id` | Invoice ID |
| `customer` | Customer name or identifier |
| `amount_inr` | Original invoice amount |
| `received_inr` | Aggregated amount received |
| `due` | Due date |
| `disputed` | Starter dispute flag |
| `records.as_of` | Default reporting date |

The field mapping is centralized in `src/loader.py`.

### 6.2 Optional detailed data

The application also accepts detailed receipts:

```json
{
  "receipt_id": "REC001",
  "invoice_id": "INV1",
  "customer": "C1",
  "amount": 2000,
  "receipt_date": "2026-10-10"
}
```

Optional invoice fields support:

- invoice date;
- disputed amount;
- dispute cause and resolution;
- replacement delivery status;
- credit amount;
- promise made date;
- promise date; and
- promise amount.

Detailed rows are useful for demonstrating realistic operational cases that are
not present in the small starter fixture.

### 6.3 PDF invoice ingestion

Real distributors may receive invoices as computer-generated PDFs. The sidebar
supports uploading one such PDF. LedgerLoop extracts selectable text, looks for
common labels, converts the result into the existing invoice JSON structure, and
then sends it through the normal validation and balance workflow.

The PDF extraction phase loads only the fields required by the receivables
workflow:

- invoice number;
- customer or billed-to name;
- invoice total, grand total, amount due, or net payable;
- invoice date; and
- due date.

The extracted invoice is given the currently selected as-of date. Receipt
information is not invented from the PDF: invoice documents normally show what
was billed, not what has subsequently been received. The finance user enters
the already received amount manually in the PDF upload form.

This is a controlled extraction step, not blind automation. The engine uses
layout-tolerant label matching, line-aware values, vendor blocks, and summary
total heuristics. If a required field cannot be found, the application displays
an extraction error and the invoice must be reviewed or corrected before
relying on the result. Different vendors use different layouts, so field
labels and formats should be tested against representative documents. The
system does not claim perfect extraction for every possible vendor format.

The current phase supports text-based, computer-generated PDFs. A scanned PDF
or image with no selectable text is identified as requiring OCR and is not
silently treated as an empty or valid invoice. OCR should be added as a separate
phase with confidence scores and mandatory human verification.

The extraction backend uses `pdfplumber` to preserve page layout, with `pypdf`
retained as a fallback. Vendor identity fields such as GSTIN, address, phone,
and email are intentionally ignored because they are not required for this
receivables workflow. The current calculation uses the validated invoice total;
it does not sum line items blindly when a document provides multiple net, tax,
and gross figures.

## 7. Loading and validation

The sidebar allows a user to upload JSON or CSV and click **Load selected
file**. The loader then:

1. reads the file;
2. maps starter names to internal names;
3. converts money to two-decimal `Decimal` values;
4. converts dates to ISO dates;
5. validates required and optional fields;
6. keeps valid invoice rows; and
7. displays all discovered errors.

The system collects errors instead of stopping at the first bad row. This is
important operationally: one bad invoice should not hide every other valid
invoice.

### Validation rules

The loader rejects or flags:

- missing invoice IDs, customers, amounts, or due dates;
- zero or negative invoice amounts;
- invalid dates;
- due dates before invoice dates;
- duplicate invoice IDs;
- invalid receipt amounts;
- negative receipts;
- invalid dispute or promise fields; and
- null required values.

`null` means unknown. It does not silently mean zero.

A receipt pointing to an unknown invoice is kept as an unapplied receipt and
flagged for investigation instead of being applied to an arbitrary invoice.

## 8. The as-of date

The sidebar contains an **As-of date** control. This is a reporting cut-off,
not simply a display filter.

Changing it recalculates:

- which receipts count;
- outstanding balances;
- overdue days;
- ageing buckets;
- promise status;
- priority scores;
- invoice states;
- explanations; and
- drafts.

Receipts after the as-of date do not count. Undated receipts count for the
balance but do not count toward fulfilling a promise.

This lets an MBA student perform a simple time-based analysis: “What did the
receivables position look like on this date?”

## 9. Balance calculation

The core calculation is:

```text
Outstanding = max(0, invoice amount - applied receipts - credit applied)
```

Example:

```text
Invoice amount       ₹10,000
Applied receipts      ₹4,000
Credit note              ₹0
Outstanding           ₹6,000
```

If receipts or credits exceed the invoice amount, outstanding is capped at zero
and the excess is recorded as an overpayment. The system does not create a
negative receivable.

The application uses `Decimal` for money and displays amounts in INR.

## 10. Invoice states

Each invoice receives a business state:

### Paid

Outstanding is zero. The invoice is excluded from the priority list and shown
in the Paid section.

### Under Review

The remaining balance is held because of a dispute and has no currently
collectable portion.

### Promised

The customer has an active payment promise and there is still a collectable
balance. The system avoids unnecessary chasing while the promise is active.

### Not due

The as-of date is on or before the due date. The invoice is not overdue.

### Collectable

The invoice is overdue, has a positive collectable amount, and is not blocked
by an active promise or a full dispute hold.

Only collectable invoices are included in priority ranking.

## 11. Ageing

Overdue days are calculated as:

```text
max(0, as-of date - due date)
```

The exact ageing buckets are:

| Days overdue | Bucket | Typical business interpretation |
|---:|---|---|
| 0 or less | Not due | Do not chase yet |
| 1-30 | 1-30 | Friendly reminder |
| 31-60 | 31-60 | More direct follow-up |
| 61-90 | 61-90 | Formal escalation |
| More than 90 | 90+ | High ageing risk |

Ageing is recomputed each time the as-of date changes.

## 12. Dispute handling

Open **Invoice detail**, select an invoice, and use **Dispute and promise
review**.

### 12.1 Dispute causes

The selectable causes are:

- **Damaged goods**: goods arrived damaged or unusable.
- **Short delivery**: the customer received fewer goods than invoiced.
- **Wrong price**: the invoice price differs from the agreed price.
- **Other**: another documented reason.
- **None**: no cause selected.

### 12.2 Dispute resolutions

The available resolutions are:

- `none`;
- `pending`;
- `replace_goods`; and
- `credit_note`.

### 12.3 Pending dispute

A pending dispute is unresolved. The disputed part is held.

Example:

```text
Outstanding:    ₹10,000
Disputed:        ₹4,000
Under review:    ₹4,000
Collectable:     ₹6,000
```

If an open dispute has no amount, the whole outstanding balance is held. This
is a conservative control: the system never asks for money whose status is
unknown.

### 12.4 Replacement of goods

The form shows **Replacement delivered** when this resolution is selected.

If the replacement is not delivered:

```text
disputed portion = under review
remaining balance = collectable
```

If the replacement is delivered, the full outstanding balance becomes
collectable because the operational remedy has been completed.

A valid cause is required for this resolution.

### 12.5 Credit note

A credit note reduces the balance financially.

Example:

```text
Outstanding before credit: ₹10,000
Credit note:                ₹2,000
Outstanding after credit:   ₹8,000
```

The credit cannot exceed the disputed amount, and a valid cause is required.
The remaining amount is payable after the credit is applied.

### 12.6 Why the split matters

The tool deliberately shows both numbers:

```text
Outstanding = Under review + Collectable
```

This prevents two opposite mistakes:

1. chasing the customer for a disputed amount; or
2. hiding an amount that could safely be collected.

## 13. Promises-to-pay

The promise section captures:

- promise made date;
- promised payment date; and
- promised amount.

The promised amount cannot exceed the collectible balance. The promise date
cannot be before the promise made date.

Only dated receipts between the promise made date and the as-of date count
toward fulfilling the promise.

### Active promise

The promise date has not passed and the promised amount is not fully received.
The invoice is shown as `Promised`.

### Kept promise

Qualifying receipts meet or exceed the promised amount.

### Broken promise

The promise date has passed and the amount is still short.

```text
Shortfall = promised amount - qualifying receipts
```

A broken promise returns the invoice to active collection work and increases
its priority score.

## 14. Priority list

The **Priority list** tab shows only invoices that are safe to consider for
collection.

The score uses a base score:

```text
45% age
35% collectible amount
20% broken-promise shortfall
```

More precisely:

```text
Base = 100 × (
    0.45 × age score
  + 0.35 × amount score
  + 0.20 × broken-promise score
)
```

For invoices more than 90 days overdue, the system adds an ageing escalation:

```text
E = 0                                      if days_overdue <= 90
E = 0.25 + 0.5 × min((days_overdue - 90) / 90, 1)  otherwise
Priority = Base + (100 - Base) × E
```

The age component itself remains capped at 90 days. The amount score is
normalized against the largest currently ranked collectible invoice. This
separates normal ageing contribution from the additional escalation applied to
very old receivables.

Ranking order is:

1. score descending;
2. overdue days descending;
3. collectible amount descending; and
4. invoice ID ascending.

The purpose is not to predict payment probability. It is a transparent,
deterministic method for choosing the next safe follow-up.

## 15. Customer follow-up drafts

The **Draft plan** tab creates one draft per customer, not one message per
invoice. This reflects a realistic account-management workflow.

The draft uses only collectable money. It does not ask for disputed amounts.

### Tone selection

| Situation | Draft approach |
|---|---|
| 1-30 days overdue | Gentle reminder |
| 31-60 days overdue | Firm request for payment date |
| More than 60 days overdue | Formal request to arrange payment |
| Broken promise | At least firm and asks for a new date |
| Active promise or not due | No message needed; schedule next check |
| Entire account under review | Explain that the concern is being investigated |
| Mixed account | Request collectable money and mention held dispute separately |

Every draft is labelled:

```text
DRAFT - not sent
```

The user can edit the text and mark it reviewed. There is intentionally no send
control.

## 16. User interface tabs

### Priority list

Shows ranked collectable invoices and score components.

### Under review

Shows disputed amounts, causes, and resolutions.

### Promised

Shows promise dates, promised amounts, receipts counted, and shortfalls.

### Not yet due / Paid

Separates invoices that are not due from invoices already paid.

### Unapplied receipts

Shows receipts that need manual investigation. The application never assigns
them automatically.

### Draft plan

Shows one editable, reviewable draft per customer.

### Invoice detail

Shows the full audit explanation and permits dispute and promise edits.

## 17. Worked example using the starter fixture

The starter fixture contains six invoices:

| Invoice | Amount | Received | Initial result |
|---|---:|---:|---|
| INV1 | ₹10,000 | ₹4,000 | ₹6,000 outstanding |
| INV2 | ₹10,000 | ₹10,000 | Paid |
| INV3 | ₹10,000 | ₹0 | Under review |
| INV4 | ₹10,000 | ₹0 | Collectable |
| INV5 | ₹10,000 | ₹0 | Collectable |
| INV6 | ₹10,000 | ₹0 | Collectable |

At the fixture as-of date:

```text
Outstanding: ₹46,000
Collectable: ₹36,000
Under review: ₹10,000
Paid invoices: 1
```

The ₹10,000 under review comes from the disputed invoice. It remains in total
outstanding but is excluded from the amount requested in a follow-up.

## 18. Exports and evidence

Click **Export results and evidence** to create:

- `output/result.json`;
- `output/result.csv`; and
- `output/evidence_log.md`.

The exports contain input values, calculated values, states, explanations,
promise information, dispute information, and the selected as-of date.

The evidence log records:

- starting state;
- scope;
- test and state evidence;
- validation errors;
- priority weights;
- age cap;
- amount normalization;
- synthetic-data disclaimer; and
- no-send and no-production-readiness statements.

The first computed result is also saved as
`output/starting_state.json` when the application initializes.

## 19. How MBA students should analyse the prototype

### Operations questions

- Which invoices create the largest safe collection opportunity?
- How much cash is blocked by disputes?
- How many receipts are unapplied?
- What percentage of outstanding money is currently collectable?
- Which customers have broken promises?

### Working-capital questions

- What happens to collectable value when the as-of date changes?
- How does faster dispute resolution change cash visibility?
- How much money is tied up in ageing buckets?
- What is the difference between total outstanding and actionable receivables?

### Customer-management questions

- Should a customer with a small old invoice be contacted before a customer
  with a large recent invoice?
- How should tone change with ageing?
- Should a broken promise override a normal reminder sequence?
- How can the business protect the relationship while still requesting
  undisputed money?

### Product and strategy questions

- Which integrations would be required for production?
- What permissions and audit controls would a finance team need?
- How would accounting-system reconciliation be added?
- What evidence would be required before claiming cash recovery?
- What customer research is needed before pricing the product?

## 20. What this prototype does not prove

The prototype does not prove:

- actual cash recovery;
- customer willingness to pay;
- market demand;
- production reliability;
- accounting-system compatibility;
- a recovery-rate improvement;
- a valid price point; or
- an effective real-world message.

The dataset is intentionally small and synthetic. The `45/35/20` weights and
90-day cap are transparent design assumptions, not statistically learned
business truths.

## 21. Suggested MBA handoff checklist

Before presenting the project, an MBA team should:

- understand the difference between outstanding, collectable, and under review;
- demonstrate one pending dispute;
- demonstrate one replacement resolution;
- demonstrate one credit-note resolution;
- demonstrate an active and a broken promise;
- explain why unapplied receipts are not auto-matched;
- change the as-of date and show the recalculation;
- upload a representative computer-generated PDF and verify the extracted
  invoice fields;
- explain why a scanned image PDF is not automatically accepted yet;
- show why the highest-ranked invoice is ranked first;
- edit a draft and mark it reviewed;
- export the evidence files; and
- clearly state that no messages are sent and all data is synthetic.

## 22. Where to read the implementation details

- `CONTEXT.md`: system boundaries and module responsibilities.
- `PROJECT_REQUIREMENTS.md`: detailed requirements and acceptance criteria.
- `docs/assumptions.md`: observed facts, assumptions, and known gaps.
- `src/loader.py`: input mapping and validation.
- `src/rules.py`: balances, ageing, promises, states, and scoring.
- `src/disputes.py`: dispute splitting and explanations.
- `src/drafts.py`: customer draft generation.
- `src/export.py`: export and evidence generation.
- `docs/BUSINESS_PRICING_AND_AWS_COST_MODEL.md`: complete AWS cost analysis (dev, deploy, maintain), unit economics, and 3-tier SaaS subscription pricing model.
- `tests/`: executable examples of the rules.

