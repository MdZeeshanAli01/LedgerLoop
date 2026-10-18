"""Template-only, human-reviewable follow-up drafts."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from typing import Iterable

from .rules import InvoiceEval


def _amount(value: Decimal) -> str:
    text = format(value.quantize(Decimal("0.01")), "f").rstrip("0").rstrip(".")
    return text or "0"


def _collectable(items: list[InvoiceEval]) -> list[InvoiceEval]:
    return [
        item for item in items
        if item.state == "Collectable" and item.collectable_amount > 0
    ]


def _draft_body(items: list[InvoiceEval]) -> str:
    collectable = _collectable(items)
    review = [item for item in items if item.review_amount > 0]
    broken = next((item for item in collectable if item.broken_promise), None)

    if broken is not None:
        body = (
            f"Hello {broken.customer}, you had agreed to pay "
            f"{_amount(broken.promise_shortfall)} for invoice "
            f"{broken.invoice_id} by {broken.invoice.promise_date.isoformat()}. "
            "We have not received it yet. Please confirm a new payment date."
        )
    elif collectable:
        oldest = max(collectable, key=lambda item: item.days_overdue)
        total = sum((item.collectable_amount for item in collectable), Decimal("0.00"))
        ids = ", ".join(item.invoice_id for item in collectable)
        if oldest.ageing_bucket == "1-30":
            body = (
                f"Hello {oldest.customer}, a friendly reminder that invoice(s) "
                f"{ids} totalling {_amount(total)} passed the due date. "
                "Could you please share the payment date?"
            )
        elif oldest.ageing_bucket == "31-60":
            body = (
                f"Hello {oldest.customer}, invoice(s) {ids} totalling "
                f"{_amount(total)} are now {oldest.days_overdue} days overdue. "
                f"Please confirm payment by {oldest.as_of_date.isoformat()}."
            )
        else:
            body = (
                f"Dear {oldest.customer}, invoice(s) {ids} are over "
                f"{oldest.days_overdue} days overdue. Please arrange payment "
                "or contact us to discuss this week."
            )
    elif items and all(item.state in {"Promised", "Not due"} for item in items):
        promise_dates = [
            item.invoice.promise_date.isoformat()
            for item in items
            if item.invoice.promise_date is not None
        ]
        next_check = min(promise_dates) if promise_dates else min(
            item.invoice.due_date.isoformat() for item in items
        )
        body = f"No message needed. Next check: {next_check}."
    elif items and all(item.state == "Under Review" for item in items):
        first = items[0]
        body = (
            f"We are looking into your concern about invoice {first.invoice_id}. "
            "We will update you on the resolution."
        )
    else:
        body = "No message needed. Review the account again after the next update."

    if review and collectable:
        for item in review:
            body += (
                f" We are separately reviewing {_amount(item.review_amount)} on "
                f"invoice {item.invoice_id} and are not asking for that amount now."
            )
    return body


def draft_for_customer(
    customer: str, invoice_evals: Iterable[InvoiceEval]
) -> dict[str, str]:
    """Create one unsent draft for a customer from evaluated invoices."""
    items = [item for item in invoice_evals if item.customer == customer]
    collectable = _collectable(items)
    total = sum((item.collectable_amount for item in collectable), Decimal("0.00"))
    subject = (
        f"Payment reminder: {_amount(total)} due - {customer}"
        if total > 0
        else f"Receivables update - {customer}"
    )
    return {
        "customer": customer,
        "status": "DRAFT - not sent",
        "subject": subject,
        "body": _draft_body(items),
    }


def drafts_for_customers(invoice_evals: Iterable[InvoiceEval]) -> list[dict[str, str]]:
    grouped: dict[str, list[InvoiceEval]] = defaultdict(list)
    for item in invoice_evals:
        grouped[item.customer].append(item)
    return [
        draft_for_customer(customer, items)
        for customer, items in sorted(grouped.items())
    ]
