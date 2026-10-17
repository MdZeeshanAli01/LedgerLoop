# Assumptions and known limits

## Observed

- The authoritative C28 starter fixture has six invoices, one global as-of date
  (`2026-10-16`), one paid invoice, and no detailed receipt list.
- The starter reference totals are ₹46,000 outstanding, ₹36,000 collectible, and
  ₹10,000 under review.
- The fixture uses INR and states that `null` means unknown, never zero.
- The starter dispute field is boolean; detailed dispute and promise fields are
  optional additions handled by the application.
- The supplied dataset is synthetic and intentionally small.

## Assumed

- Priority weights are design choices: 45% age, 35% collectible amount, and 20%
  broken-promise shortfall.
- Age normalization is capped at 90 days.
- When detailed receipt rows exist, they replace the starter aggregate receipt
  amount for that invoice.
- Template drafts are an acceptable disclosed fallback for message generation;
  there are no model or external-service calls.
- A missing amount on an open boolean dispute means the full current outstanding
  balance is under review.
- The product is a read-only workflow aid; production reconciliation, recovery
  rates, customer payment history, and market demand are not established.

## Known gaps

- The starter fixture does not provide payment history, detailed disputes,
  promise records, or receipt dates; those behaviors are demonstrated using
  clearly labelled synthetic test data.
- MBA pricing, growth, customer research, and pitch deliverables are outside the
  engineering scope.
- MBA-entry snapshot evidence must be added when the MBA team actually joins;
  it is not fabricated in this repository beforehand.
