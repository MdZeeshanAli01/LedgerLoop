"""Reproducible result and evidence exports."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable

from .loader import ValidationError
from .negotiated import RecoveryAgreement, RecoveryProgress
from .rules import InvoiceEval, W_AGE, W_AMOUNT, W_PROMISE, AGE_CAP


def _value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return format(value.quantize(Decimal("0.01")), "f")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, list):
        return [_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _value(item) for key, item in value.items()}
    return value


def evaluation_record(evaluation: InvoiceEval) -> dict[str, Any]:
    invoice = evaluation.invoice
    record = {
        "invoice_id": invoice.invoice_id,
        "customer": invoice.customer,
        "amount": invoice.amount,
        "received_amount": invoice.received_amount,
        "invoice_date": invoice.invoice_date,
        "due_date": invoice.due_date,
        "disputed": invoice.disputed,
        "dispute_status": invoice.dispute_status,
        "disputed_amount": invoice.disputed_amount,
        "dispute_cause": invoice.dispute_cause,
        "dispute_resolution": invoice.dispute_resolution,
        "replacement_delivered": invoice.replacement_delivered,
        "credit_amount": invoice.credit_amount,
        "settlement_agreed": invoice.settlement_agreed,
        "settlement_amount": invoice.settlement_amount,
        "settlement_note": invoice.settlement_note,
        "promise_made_date": invoice.promise_made_date,
        "promise_date": invoice.promise_date,
        "promise_amount": invoice.promise_amount,
        "as_of_date": evaluation.as_of_date,
        "applied_receipts": evaluation.applied_receipts,
        "credit_applied": evaluation.credit_applied,
        "outstanding": evaluation.outstanding,
        "overpaid_amount": evaluation.overpaid_amount,
        "days_overdue": evaluation.days_overdue,
        "ageing_bucket": evaluation.ageing_bucket,
        "review_amount": evaluation.review_amount,
        "collectable_amount": evaluation.collectable_amount,
        "state": evaluation.state,
        "is_not_yet_issued": evaluation.is_not_yet_issued,
        "promise_status": evaluation.promise_status,
        "promised_paid": evaluation.promised_paid,
        "promise_shortfall": evaluation.promise_shortfall,
        "broken_promise": evaluation.broken_promise,
        "score": evaluation.score,
        "age_points": evaluation.age_points,
        "amount_points": evaluation.amount_points,
        "promise_points": evaluation.promise_points,
        "escalation_points": evaluation.escalation_points,
    }
    from .disputes import explain
    record["explanation"] = explain(evaluation)
    return _value(record)


def write_result_json(evals: Iterable[InvoiceEval], path: str | Path) -> None:
    records = [evaluation_record(item) for item in evals]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records, indent=2), encoding="utf-8")


def write_result_csv(evals: Iterable[InvoiceEval], path: str | Path) -> None:
    records = [evaluation_record(item) for item in evals]
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(records[0]) if records else [
        "invoice_id", "customer", "as_of_date", "outstanding", "state"
    ]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)


def write_starting_state(
    evals: Iterable[InvoiceEval], path: str | Path
) -> None:
    """Persist the first computed result without mutating source input."""
    write_result_json(evals, path)


def negotiated_record(progress: RecoveryProgress) -> dict[str, Any]:
    agreement = progress.agreement
    return _value({
        "agreement_id": agreement.agreement_id,
        "retailer": agreement.retailer,
        "previous_invoice_id": agreement.previous_invoice_id,
        "actual_bep": agreement.actual_bep,
        "recovery_floor": agreement.recovery_floor,
        "target_type": agreement.target_type.value,
        "agreed_target": agreement.agreed_target,
        "upfront_percent": agreement.upfront_percent,
        "credit_percent": agreement.credit_percent,
        "credit_period_days": agreement.credit_period_days,
        "baseline_collected": agreement.baseline_collected,
        "agreement_date": agreement.agreement_date,
        "note": agreement.note,
        "agreement_status": agreement.status.value,
        "approved_by": agreement.approved_by,
        "approved_at": agreement.approved_at,
        "approval_note": agreement.approval_note,
        "recovered_amount": progress.recovered_amount,
        "remaining_amount": progress.remaining_amount,
        "excess_amount": progress.excess_amount,
        "invoice_outstanding": progress.invoice_outstanding,
        "invoice_balance_after_target": progress.invoice_balance_after_target,
        "recovery_status": progress.status.value,
        "next_order_eligible": progress.next_order_eligible,
    })


def write_negotiated_json(
    progresses: Iterable[RecoveryProgress], path: str | Path
) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps([negotiated_record(item) for item in progresses], indent=2),
        encoding="utf-8",
    )


def _error_text(error: ValidationError | str) -> str:
    if isinstance(error, ValidationError):
        return f"{error.row} | {error.field} | {error.problem}"
    return str(error)


def write_evidence_log(
    path: str | Path,
    evals: Iterable[InvoiceEval] = (),
    *,
    fixture_name: str = "data/fixture.json",
    receipt_count: int = 0,
    validation_errors: Iterable[ValidationError | str] = (),
    tests_passed: int | None = None,
    tests_total: int | None = None,
    negotiated_scope: str = (
        "Disputes with cause and resolution, partial receipts, promises-to-pay, "
        "and collectible-only priority were added to the bounded workflow."
    ),
    starting_description: str = (
        "Original workflow: overdue invoices were listed without dispute handling."
    ),
) -> None:
    items = list(evals)
    states = Counter(item.state for item in items)
    errors = list(validation_errors)
    test_line = (
        f"{tests_passed} passed out of {tests_total}"
        if tests_passed is not None and tests_total is not None
        else "Not supplied; run pytest before release."
    )
    error_lines = "\n".join(f"- {_error_text(error)}" for error in errors)
    if not error_lines:
        error_lines = "- None recorded."
    state_lines = "\n".join(
        f"- {state}: {count}" for state, count in sorted(states.items())
    ) or "- No evaluated invoices."
    content = f"""# LedgerLoop evidence log

## Starting state

{starting_description}
- Fixture: `{fixture_name}`
- Invoices loaded: {len(items)}
- Receipts loaded: {receipt_count}

## Negotiated scope

{negotiated_scope}

## Final evidence

- Tests: {test_line}
- State counts:
{state_lines}
- Validation errors:
{error_lines}

## Observed versus assumed

| Observed | Assumed |
|---|---|
| Values and state counts produced from the loaded synthetic fixture. | Priority weights: age {W_AGE}, amount {W_AMOUNT}, broken promise {W_PROMISE}. |
| Balances, disputes, promises, and ageing are recalculated for the selected as-of date. | Age cap: {AGE_CAP} days; collectible amount is normalized against the largest ranked collectible amount. |
| Drafts are template-generated and remain reviewable. | No production payment behavior, recovery rate, or market demand is inferred. |

Figures come from synthetic data. No cash recovery or production readiness is claimed.
Drafts are not sent.
"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
