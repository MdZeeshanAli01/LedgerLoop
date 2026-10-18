# LedgerLoop Project Requirements

## 1. Product definition

LedgerLoop is a single-page Streamlit decision-support tool for a small
distributor's finance lead. It imports synthetic invoice and receipt data,
calculates what is still owed, separates disputed money from collectible money,
prioritizes safe follow-up, prepares human-reviewable draft messages, and exports
reproducible evidence.

The product is a workflow aid, not a payment system, messaging system, recovery
guarantee, or production-readiness claim.

## 2. Non-negotiable boundaries

- Never send email, WhatsApp, SMS, or any other message.
- Never call an external service, LLM, payment gateway, or machine-learning model.
- Never auto-match or auto-apply unapplied receipts.
- Never modify the source fixture. Keep edits in session state and exported results.
- Never store derived ageing or priority values; recompute them from the selected
  `as_of` date.
- Never hide disputed balances.
- Use `Decimal` for all money, rounded to two decimal places, and display `₹`.
- Use only Python 3.10+, Streamlit, pandas, and pytest.
- Treat all supplied data as synthetic. Do not claim recovered cash, live revenue,
  or production readiness.

## 3. Required repository shape

```text
LedgerLoop/
  CONTEXT.md
  app.py
  src/
    __init__.py
    loader.py
    rules.py
    disputes.py
    drafts.py
    export.py
  tests/
    test_loader.py
    test_rules.py
    test_disputes.py
    test_drafts.py
    test_integration.py
  data/
    fixture.json
    extra_synthetic.json
  output/
  docs/
    assumptions.md
  requirements.txt
  README.md
```

## 4. Functional requirements

### F1-F3: Import and validation

- Load the supplied fixture and optionally a CSV with equivalent fields.
- Map the real starter fields in one place:
  `id -> invoice_id`, `amount_inr -> amount`, `received_inr -> applied
  receipts`, `due -> due_date`, `records.as_of -> as_of_date`, and
  `disputed -> dispute flag`.
- Support both the starter's aggregated `received_inr` and an optional receipt
  list.
- Accept optional invoice date, promise, dispute, resolution, credit, and
  receipt-date fields without inventing missing values.
- Read `records.as_of` as the default date.
- Preserve unknown metadata such as `synthetic`, `data_version`, `currency`, and
  `limit` for display/evidence where appropriate.
- Collect all validation errors as `(row, field, problem)` records; valid rows
  still load and invalid rows are excluded.
- Reject missing required fields, non-positive/invalid amounts, invalid dates,
  due dates before invoice dates, duplicate invoice IDs, invalid receipts, and
  invalid dispute/promise fields.
- Keep a receipt pointing to an unknown invoice as unapplied and flag it.
- Treat `null` as unknown, never as zero. A null required amount, receipt amount,
  or due date is flagged and excluded from calculation.

### F4-F10: Balances, dates, and ageing

- Calculate applied receipts using all valid linked receipts whose date is not
  after `as_of`; undated receipts count.
- Keep receipts with no invoice ID separate and show them by customer with the
  required warning banner.
- Calculate `outstanding = max(0, amount - receipts - credit)`.
- Flag and show overpayment excess when receipts/credit exceed the invoice.
- Calculate credit days only when an invoice date exists.
- Calculate overdue days as `max(0, as_of - due_date)`.
- Use exact buckets: `Not due`, `1-30`, `31-60`, `61-90`, `90+`.
- Exclude invoices issued after `as_of` and show a note.
- Mark zero-outstanding invoices `Paid`; exclude them from priority and show them
  in a Paid view.
- Ensure every as-of change updates all balances, states, ageing, scores,
  explanations, and drafts consistently.

### F11-F14: Disputes

- Capture disputed amount and cause: damaged goods, short delivery, wrong price,
  or other.
- Capture resolution: pending, replace goods, or credit note.
- For replacement, capture whether goods were delivered.
- For credit notes, capture and validate the credit amount.
- Apply the exact review/collectable split:
  - pending or replacement not delivered: disputed portion is under review;
  - replacement delivered: full outstanding remains collectible;
  - credit note: credit reduces outstanding and the remainder is collectible.
- Reject disputed amounts above the pre-credit balance, credits above disputed
  amount, missing causes for resolutions, and invalid resolution combinations.
- If an open dispute has no amount, hold the whole outstanding balance.
- Show the review amount even when the invoice also has a collectible amount.
- Generate the required plain-language explanation for every invoice.

### F15-F17: Promises and priority

- Store only the latest promise per invoice:
  `promise_made_date`, `promise_date`, and `promise_amount`.
- Validate required promise fields, date order, and promise amount not exceeding
  collectible amount.
- Count only receipts dated from promise-made date through `as_of` toward a
  promise; undated and earlier receipts do not count.
- Keep an active promise in `Promised` state, including on the promise date.
- On the day after an unpaid promise, mark it `Collectable` with a broken-promise
  note and shortfall.
- Ignore promises on paid invoices.
- Rank only collectible invoices using:
  `Base = 100 * (0.45 * age_score + 0.35 * amount_score + 0.20 * broken_promise)`.
  For invoices older than 90 days, use
  `E = 0.25 + 0.5 * min((days_overdue - 90) / 90, 1)` and
  `Priority = Base + (100 - Base) * E`. `E` is zero at 90 days or less.
- Use `AGE_CAP = 90`; normalize amount against the largest ranked collectible
  amount, or `1.0` when only one invoice is ranked.
- Sort by unrounded score descending, overdue days descending, collectible
  amount descending, then invoice ID ascending.
- Show score components and a “why ranked here” sentence.

### F18: Draft follow-up plan

- Create one draft per customer covering that customer's collectible invoices.
- Use the oldest ageing bucket to choose Gentle, Firm, or Formal tone.
- Raise tone to at least Firm for a broken promise.
- Use collectible amount only, never full outstanding amount.
- Include held dispute amounts and appropriate no-chase/dispute text.
- Always label drafts `DRAFT - not sent`.
- Allow editing and a “Mark reviewed” checkbox; provide no send control.

### F19-F21: UI and auditability

- Build one Streamlit page with:
  - file upload/default fixture, as-of date picker, customer filter, and errors;
  - totals for outstanding, collectible, under review, and promised;
  - Priority, Under Review, Promised, Not Yet Due/Paid, Unapplied Receipts, and
    Draft Plan tabs;
  - selectable invoice detail panel;
  - dispute and promise edit forms with conditional fields;
  - audit table and explanation/score breakdown.
- Keep all numeric calculations behind `evaluate_all`; the UI only renders results.
- Keep source data read-only and edits in session state.

### F20-F24: Exports, evidence, and honesty

- Export `output/result.json` and `output/result.csv` with every input/computed
  field, state, explanation, and as-of date.
- Save the untouched initial run to `output/starting_state.json`.
- Generate `output/evidence_log.md` with:
  1. starting state,
  2. negotiated scope,
  3. final test/state/error evidence,
  4. observed versus assumed values.
- Include the priority weights, age cap, amount normalization, synthetic-data
  disclaimer, no-send statement, and no-production-readiness statement.
- README must explain setup, test execution, template-only fallback, known gaps,
  and limitations.

## 5. Development phases and definition of done

Each phase is complete only when its tests pass and its commit is created.

### Phase 0 — Research, context, and baseline

- [ ] Preserve the supplied fixture unchanged.
- [ ] Use `Starter_Data/C28/fixture.json` as the authoritative input:
  `case_id=C28`, `data_version=v3.2`, INR currency, six invoices, one global
  `records.as_of`, and `null means unknown, never zero`.
- [ ] Add `CONTEXT.md` summarizing Sections 1-6 of the build specification.
- [ ] Add `docs/assumptions.md` with observed-vs-assumed decisions.
- [ ] Record the starter baseline: six invoices, one paid, ₹46,000 outstanding,
  ₹36,000 collectible, ₹10,000 under review at `2026-10-16`.
- [ ] Add `data/extra_synthetic.json` with labelled partial payment, unapplied
  receipt, dispute detail, promise, and negative-input cases.
- [ ] Add `requirements.txt`, package layout, and test configuration.

**Exit criteria:** context, assumptions, fixture, synthetic cases, and runnable
test command exist.

### Phase 1 — Loader and validation

- [ ] Implement field mapping and JSON/CSV loading in `src/loader.py`.
- [ ] Normalize dates and money to `date` and `Decimal`.
- [ ] Implement all row, receipt, dispute, promise, null, duplicate, and unknown
  invoice validations.
- [ ] Return valid invoices, receipts, fixture as-of date, metadata, and errors.
- [ ] Write `test_loader.py`, including a test proving the input file is unchanged.

**Exit criteria:** malformed data produces visible errors without crashing and
valid rows remain usable.

### Phase 2 — Core balances and ageing

- [ ] Implement pure date, bucket, receipt, outstanding, overpayment, and
  unapplied-receipt functions in `src/rules.py`.
- [ ] Implement `evaluate_all` as the only orchestration entry point.
- [ ] Write tests 1-8, 16-17, 25, and 41.
- [ ] Verify the starter reference values and all ageing boundaries.

**Exit criteria:** balance, receipt, as-of, and ageing tests pass exactly.

### Phase 3 — Dispute workflow and explanations

- [ ] Implement `src/disputes.py` split, validation, and explanation functions.
- [ ] Implement invoice state ordering: Paid, Under Review, Promised, Collectable.
- [ ] Write tests 9-15 and 23.
- [ ] Verify partial disputes remain visible and credit/replacement outcomes are
  explained precisely.

**Exit criteria:** all dispute and explanation tests pass.

### Phase 4 — Promise-to-pay and priority queue

- [ ] Implement promise status, promised-paid, shortfall, and broken-promise logic.
- [ ] Implement score constants, score components, deterministic sorting, and
  ranking explanations.
- [ ] Write tests 18-22, 26-36, and 38-40.
- [ ] Verify active promises are held and broken promises are prioritized correctly.

**Exit criteria:** promise and priority behavior is deterministic and fully tested.

### Phase 5 — Draft plan

- [ ] Implement template-only customer drafts in `src/drafts.py`.
- [ ] Implement ageing tone, broken-promise escalation, held-dispute text,
  no-chase text, and reviewed state.
- [ ] Write tests 24 and 37.

**Exit criteria:** every draft is reviewable, uses collectible amounts, and can
never be sent.

### Phase 6 — Export and evidence

- [ ] Implement JSON, flat CSV, starting snapshot, and evidence log in
  `src/export.py`.
- [ ] Include all computed fields needed to reproduce the displayed result.
- [ ] Include test counts, state counts, validation errors, assumptions, negotiated
  scope, and synthetic-data disclaimer.

**Exit criteria:** export files are created and reproduce on-screen results.

### Phase 7 — Streamlit interface

- [ ] Implement the one-page UI in `app.py`.
- [ ] Wire file loading, filters, date changes, all tabs, detail panel, forms,
  session state, drafts, exports, and error display.
- [ ] Confirm no calculation logic is duplicated in the UI.
- [ ] Manually walk through changing as-of, saving a dispute, saving a promise,
  reviewing a draft, and exporting.

**Exit criteria:** the complete judge-repeatable workflow runs without errors.

### Phase 8 — Integration, reliability, and handoff

- [ ] Add integration tests covering the full starter fixture and synthetic cases.
- [ ] Run all 41 specification tests plus the starter reference regression test
  (test 42).
- [ ] Test bad rows, null values, duplicate edits, overpayment, unknown receipts,
  and empty priority states.
- [ ] Update README with setup, commands, limitations, known gaps, and fallback.
- [ ] Add `output/snapshot_at_mba_entry.md` when the MBA team joins, containing
  demo/reference, test results, known gaps, backlog, contributors, timestamp,
  and baseline.
- [ ] Use the supplied `Negotiation_and_Transfer_Log.csv`, `Roster_Register.csv`,
  and judging templates for the handoff record; link the transfer entry to the
  repository README.
- [ ] Tag the release only after the full suite and manual workflow pass.

**Exit criteria:** all automated tests pass, the demo is repeatable, evidence is
saved, and claims remain honest.

## 6. Acceptance checklist

- [ ] Fixture loads and counts are shown.
- [ ] ₹10,000 invoice with ₹4,000 receipts shows ₹6,000 outstanding.
- [ ] Paid invoices leave priority.
- [ ] Disputed balances remain visible.
- [ ] As-of date changes all derived values consistently.
- [ ] Partial and unapplied receipts behave correctly.
- [ ] Disputes record cause and resolution.
- [ ] Active and broken promises behave correctly.
- [ ] Priority score and explanation are visible.
- [ ] One not-sent draft exists per customer.
- [ ] JSON, CSV, starting snapshot, and evidence log export.
- [ ] All 41 specification tests and starter regression test pass.
- [ ] No prohibited feature or unsupported production claim exists.

## 7. Explicitly out of scope

Authentication, users, roles, database persistence, live integrations, sending
messages, payment gateways, multi-currency, tax, interest, late fees, receipt
auto-matching, LLM/ML calls, recovered-cash claims, production deployment, and
MBA-only pricing, growth, customer, and pitch deliverables.
