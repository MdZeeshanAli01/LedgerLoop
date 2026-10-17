"""Pure balance and ageing rules for the C28 receivables workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .loader import Invoice, Receipt, MONEY_QUANTUM


@dataclass
class InvoiceEval:
    invoice: Invoice
    as_of_date: date
    applied_receipts: Decimal
    credit_applied: Decimal
    outstanding: Decimal
    overpaid_amount: Decimal
    days_overdue: int
    ageing_bucket: str
    review_amount: Decimal
    collectable_amount: Decimal
    state: str
    is_not_yet_issued: bool = False

    @property
    def invoice_id(self) -> str:
        return self.invoice.invoice_id

    @property
    def customer(self) -> str:
        return self.invoice.customer


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


def days_overdue(due_date: date, as_of: date) -> int:
    """Return zero on or before the due date and calendar days after it."""
    return max(0, (as_of - due_date).days)


def bucket(days: int) -> str:
    if days <= 0:
        return "Not due"
    if days <= 30:
        return "1-30"
    if days <= 60:
        return "31-60"
    if days <= 90:
        return "61-90"
    return "90+"


def _receipt_amount(invoice: Invoice, receipts: list[Receipt], as_of: date) -> Decimal:
    dated_receipts = [
        receipt.amount
        for receipt in receipts
        if receipt.invoice_id == invoice.invoice_id
        and (receipt.receipt_date is None or receipt.receipt_date <= as_of)
    ]
    # The starter fixture has one aggregate received value. When receipt rows
    # are supplied, they are the detailed source and replace that aggregate.
    if dated_receipts:
        return _money(sum(dated_receipts, Decimal("0.00")))
    return _money(invoice.received_amount)


def applied_receipts(invoice: Invoice, receipts: list[Receipt], as_of: date) -> Decimal:
    return _receipt_amount(invoice, receipts, as_of)


def credit_applied(invoice: Invoice) -> Decimal:
    if invoice.dispute_resolution == "credit_note":
        return _money(invoice.credit_amount)
    return Decimal("0.00")


def outstanding(invoice: Invoice, receipts: list[Receipt], as_of: date) -> Decimal:
    applied = applied_receipts(invoice, receipts, as_of)
    return max(Decimal("0.00"), _money(invoice.amount - applied - credit_applied(invoice)))


def overpaid_amount(invoice: Invoice, receipts: list[Receipt], as_of: date) -> Decimal:
    applied = applied_receipts(invoice, receipts, as_of)
    excess = invoice.amount - applied - credit_applied(invoice)
    return _money(max(Decimal("0.00"), excess * Decimal("-1")))


def unapplied_receipts(receipts: list[Receipt], as_of: date) -> list[Receipt]:
    return [
        receipt for receipt in receipts
        if receipt.invoice_id is None
        and (receipt.receipt_date is None or receipt.receipt_date <= as_of)
    ]


def _review_and_collectable(invoice: Invoice, balance: Decimal) -> tuple[Decimal, Decimal]:
    # A starter boolean dispute has no amount/detail; hold the full balance.
    if invoice.disputed and invoice.dispute_status in {"none", "open"}:
        review = balance if invoice.disputed_amount is None else min(
            invoice.disputed_amount, balance
        )
        return review, balance - review
    return Decimal("0.00"), balance


def invoice_state(
    invoice: Invoice,
    balance: Decimal,
    review_amount: Decimal,
    collectable_amount: Decimal,
    as_of: date,
) -> str:
    if balance == 0:
        return "Paid"
    if review_amount > 0 and collectable_amount == 0:
        return "Under Review"
    if as_of <= invoice.due_date:
        return "Not due"
    return "Collectable"


def evaluate_all(
    invoices: list[Invoice], receipts: list[Receipt], as_of: date
) -> list[InvoiceEval]:
    """Evaluate every valid invoice using one explicit calculation pass."""
    evaluations: list[InvoiceEval] = []
    for invoice in invoices:
        not_yet_issued = invoice.invoice_date is not None and invoice.invoice_date > as_of
        applied = applied_receipts(invoice, receipts, as_of)
        credit = credit_applied(invoice)
        raw_balance = _money(invoice.amount - applied - credit)
        balance = max(Decimal("0.00"), raw_balance)
        review, collectable = _review_and_collectable(invoice, balance)
        overdue = days_overdue(invoice.due_date, as_of)
        evaluations.append(InvoiceEval(
            invoice=invoice,
            as_of_date=as_of,
            applied_receipts=applied,
            credit_applied=credit,
            outstanding=balance,
            overpaid_amount=_money(max(Decimal("0.00"), -raw_balance)),
            days_overdue=overdue,
            ageing_bucket=bucket(overdue),
            review_amount=_money(review),
            collectable_amount=_money(collectable),
            state=invoice_state(invoice, balance, review, collectable, as_of),
            is_not_yet_issued=not_yet_issued,
        ))
    return evaluations


def ranked_collectable(evaluations: list[InvoiceEval]) -> list[InvoiceEval]:
    """Return the basic Phase 2 priority view, excluding paid/not-due/review rows."""
    return sorted(
        (
            evaluation for evaluation in evaluations
            if evaluation.state == "Collectable"
            and evaluation.collectable_amount > 0
            and not evaluation.is_not_yet_issued
        ),
        key=lambda evaluation: (
            -evaluation.days_overdue,
            -evaluation.collectable_amount,
            evaluation.invoice_id,
        ),
    )
