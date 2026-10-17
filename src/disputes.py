"""Dispute validation, balance splitting, and invoice explanations."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from .loader import Invoice, MONEY_QUANTUM

if TYPE_CHECKING:
    from .rules import InvoiceEval

CAUSE_LABELS = {
    "damaged_goods": "damaged goods",
    "short_delivery": "short delivery",
    "wrong_price": "wrong price",
    "other": "other reason",
}
VALID_CAUSES = set(CAUSE_LABELS)
VALID_RESOLUTIONS = {"none", "pending", "replace_goods", "credit_note"}


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


def _display(value: Decimal) -> str:
    text = format(_money(value), "f").rstrip("0").rstrip(".")
    return text or "0"


def split_balance(invoice: Invoice, outstanding: Decimal) -> tuple[Decimal, Decimal]:
    """Return (review, collectable) according to the exact resolution table."""
    balance = max(Decimal("0.00"), _money(outstanding))
    resolution = invoice.dispute_resolution
    disputed = invoice.disputed_amount

    if resolution == "credit_note":
        return Decimal("0.00"), balance
    if resolution == "replace_goods" and invoice.replacement_delivered:
        return Decimal("0.00"), balance
    if resolution in {"pending", "replace_goods"}:
        held = balance if disputed is None else min(_money(disputed), balance)
        return held, balance - held
    if invoice.disputed:
        held = balance if disputed is None else min(_money(disputed), balance)
        return held, balance - held
    return Decimal("0.00"), balance


def validate_dispute(invoice: Invoice, applied: Decimal) -> list[str]:
    """Validate editable dispute fields without mutating the invoice."""
    errors: list[str] = []
    before_credit = _money(invoice.amount - applied)
    disputed = invoice.disputed_amount
    resolution = invoice.dispute_resolution

    if resolution not in VALID_RESOLUTIONS:
        errors.append("dispute_resolution must be none, pending, replace_goods, or credit_note")
    if disputed is not None and disputed < 0:
        errors.append("disputed_amount cannot be negative")
    if disputed is not None and disputed > before_credit:
        errors.append("disputed_amount cannot exceed the balance before credit")
    if invoice.credit_amount < 0:
        errors.append("credit_amount cannot be negative")
    if invoice.credit_amount > 0 and (
        disputed is None or invoice.credit_amount > disputed
    ):
        errors.append("credit_amount cannot exceed disputed_amount")
    if resolution == "credit_note" and invoice.credit_amount <= 0:
        errors.append("credit_note requires a credit_amount")
    if resolution in {"replace_goods", "credit_note"} and invoice.dispute_cause not in VALID_CAUSES:
        errors.append("this resolution requires a valid dispute_cause")
    if resolution == "replace_goods" and not isinstance(invoice.replacement_delivered, bool):
        errors.append("replacement_delivered must be true or false")
    return errors


def explain(invoice_eval: InvoiceEval) -> str:
    """Build the required plain-language audit sentence for one invoice."""
    invoice = invoice_eval.invoice
    parts = [
        f"Invoice {invoice.invoice_id}: amount {_display(invoice.amount)}.",
        f"Receipts applied {_display(invoice_eval.applied_receipts)}.",
    ]
    if invoice.disputed or invoice.disputed_amount is not None:
        disputed = invoice_eval.outstanding if invoice.disputed_amount is None else invoice.disputed_amount
        cause = (
            CAUSE_LABELS.get(invoice.dispute_cause, "other reason")
            if invoice.dispute_cause
            else "dispute detail missing"
        )
        parts.append(f"Disputed {_display(disputed)} ({cause}).")
        if invoice.dispute_resolution == "pending":
            parts.append("Dispute is open, so this part is held.")
        elif invoice.dispute_resolution == "replace_goods":
            if invoice.replacement_delivered:
                parts.append("Goods replaced. Full amount remains payable.")
            else:
                parts.append(
                    "Agreed to replace the goods. Replacement not yet delivered, "
                    "so this part is held."
                )
        elif invoice.dispute_resolution == "credit_note":
            remaining = max(
                Decimal("0.00"),
                invoice.disputed_amount - invoice.credit_amount,
            ) if invoice.disputed_amount is not None else Decimal("0.00")
            parts.append(
                f"Settled financially: credit of {_display(invoice.credit_amount)} agreed. "
                f"Remaining disputed amount {_display(remaining)} is payable."
            )
    parts.append(
        f"Outstanding {_display(invoice_eval.outstanding)}: "
        f"collectable {_display(invoice_eval.collectable_amount)}, "
        f"under review {_display(invoice_eval.review_amount)}."
    )
    parts.append(
        f"Due {invoice.due_date.isoformat()}, {invoice_eval.days_overdue} days overdue "
        f"({invoice_eval.ageing_bucket}) as of {invoice_eval.as_of_date.isoformat()}."
    )
    if invoice_eval.promise_status != "none":
        parts.append(
            f"Promised {_display(invoice.promise_amount or invoice_eval.collectable_amount)} "
            f"by {invoice.promise_date.isoformat()}, received "
            f"{_display(invoice_eval.promised_paid)}."
        )
        if invoice_eval.promise_status == "active":
            parts.append("Promise active, so this invoice is held.")
        elif invoice_eval.promise_status == "kept":
            parts.append("Promise kept.")
        else:
            parts.append(
                f"Promise missed, shortfall {_display(invoice_eval.promise_shortfall)}."
            )
    if invoice_eval.score is not None:
        parts.append(
            f"Score {_display(invoice_eval.score)} = age {_display(invoice_eval.age_points)} "
            f"+ amount {_display(invoice_eval.amount_points)} + broken promise "
            f"{_display(invoice_eval.promise_points)}."
        )
    return " ".join(parts)
