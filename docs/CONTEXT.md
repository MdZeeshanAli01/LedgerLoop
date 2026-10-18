# C28 Receivables Follow-Up Desk Context

## Problem and boundary

LedgerLoop helps a small distributor's finance lead decide which business
customers can be chased, for how much, and why. It imports invoices and
receipts, calculates balances as of a selected date, separates disputed money
from collectible money, records promises-to-pay, drafts a reviewable follow-up
plan, and saves reproducible evidence.

The data is synthetic and the workflow is bounded. LedgerLoop never sends a
message, calls an external service, auto-applies an unapplied receipt, modifies
the source fixture, or claims recovered cash or production readiness.

## Input mapping

The authoritative starter file is `data/fixture.json`, extracted from
`Starter_Data/C28/fixture.json`.

| Starter field | Internal field |
|---|---|
| `records.invoices[].id` | `invoice_id` |
| `records.invoices[].customer` | `customer` |
| `records.invoices[].amount_inr` | `amount` |
| `records.invoices[].received_inr` | aggregated received amount |
| `records.invoices[].due` | `due_date` |
| `records.invoices[].disputed` | starter dispute flag |
| `records.as_of` | default `as_of_date` |

Optional detailed receipts use `receipt_id`, `invoice_id`, `customer`, `amount`,
and `receipt_date`. Optional dispute fields describe cause, resolution,
replacement delivery, and credit. Optional promise fields describe the promise
made date, promised date, and promised amount.

## Business rules

- Money uses `Decimal`, is rounded to two places, and is displayed in INR.
- `null` means unknown and is never silently changed to zero.
- Receipts after `as_of` are ignored; undated receipts count for balances.
- Outstanding is invoice amount less applied receipts and credit, capped at zero.
- Disputed balances are held separately and remain visible.
- Paid, Under Review, Promised, and Collectable states are evaluated in order.
- Active promises are held through the promise date; unpaid promises become
  broken on the following day.
- Only collectible invoices are prioritized using the documented 0.45/0.35/0.20
  age/amount/broken-promise score and a 90-day age cap.
- Drafts are template-generated, labelled `DRAFT - not sent`, and never sent.

## Module responsibilities

- `src/loader.py`: field mapping, normalization, and validation.
- `src/rules.py`: pure balance, ageing, promise, state, and priority rules.
- `src/disputes.py`: dispute split, validation, and explanations.
- `src/drafts.py`: reviewable template drafts.
- `src/export.py`: JSON, CSV, starting snapshot, and evidence log.
- `app/app.py`: Streamlit rendering and session-state workflow only.
