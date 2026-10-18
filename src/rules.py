"""Pure balance and ageing rules for the C28 receivables workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from .loader import Invoice, Receipt, MONEY_QUANTUM
from .disputes import split_balance

W_AGE = Decimal("0.45")
W_AMOUNT = Decimal("0.35")
W_PROMISE = Decimal("0.20")
AGE_CAP = 90


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
    promise_status: str = "none"
    promised_paid: Decimal = Decimal("0.00")
    promise_shortfall: Decimal = Decimal("0.00")
    broken_promise: bool = False
    score: Decimal | None = None
    age_points: Decimal = Decimal("0.00")
    amount_points: Decimal = Decimal("0.00")
    promise_points: Decimal = Decimal("0.00")
    escalation_points: Decimal = Decimal("0.00")

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
    if invoice.settlement_agreed and invoice.settlement_amount is not None:
        return _money(max(Decimal("0.00"), invoice.amount - invoice.settlement_amount))
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
    return split_balance(invoice, balance)


def promise_status(
    invoice: Invoice, receipts: list[Receipt], as_of: date, collectable: Decimal
) -> tuple[str, Decimal, Decimal]:
    """Return status, receipts counted toward the promise, and shortfall."""
    if invoice.promise_date is None or invoice.promise_made_date is None:
        return "none", Decimal("0.00"), Decimal("0.00")
    if collectable <= 0:
        return "none", Decimal("0.00"), Decimal("0.00")
    paid = _money(sum(
        (
            receipt.amount
            for receipt in receipts
            if receipt.invoice_id == invoice.invoice_id
            and receipt.receipt_date is not None
            and invoice.promise_made_date <= receipt.receipt_date <= as_of
        ),
        Decimal("0.00"),
    ))
    promised_amount = invoice.promise_amount or collectable
    shortfall = max(Decimal("0.00"), _money(promised_amount - paid))
    if shortfall == 0:
        return "kept", paid, shortfall
    if as_of <= invoice.promise_date:
        return "active", paid, shortfall
    return "broken", paid, shortfall


def invoice_state(
    invoice: Invoice,
    balance: Decimal,
    review_amount: Decimal,
    collectable_amount: Decimal,
    as_of: date,
    promise: str = "none",
) -> str:
    if balance == 0:
        return "Paid"
    if review_amount > 0 and collectable_amount == 0:
        return "Under Review"
    if promise == "active" and collectable_amount > 0:
        return "Promised"
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
        promise, promised_paid, shortfall = promise_status(
            invoice, receipts, as_of, collectable
        )
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
            state=invoice_state(invoice, balance, review, collectable, as_of, promise),
            is_not_yet_issued=not_yet_issued,
            promise_status=promise,
            promised_paid=promised_paid,
            promise_shortfall=shortfall,
            broken_promise=promise == "broken",
        ))
    return evaluations


def priority_score(
    evaluation: InvoiceEval, max_collectable: Decimal
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return total score and base component points with ageing escalation."""
    age_score = min(evaluation.days_overdue, AGE_CAP) / Decimal(AGE_CAP)
    amount_score = (
        Decimal("1.00")
        if max_collectable <= 0
        else evaluation.collectable_amount / max_collectable
    )
    promise_score = (
        evaluation.promise_shortfall / (evaluation.invoice.promise_amount or evaluation.collectable_amount)
        if evaluation.broken_promise
        else Decimal("0.00")
    )
    age_points = Decimal("100") * W_AGE * age_score
    amount_points = Decimal("100") * W_AMOUNT * amount_score
    promise_points = Decimal("100") * W_PROMISE * promise_score
    base = age_points + amount_points + promise_points
    if evaluation.days_overdue <= AGE_CAP:
        escalation = Decimal("0.00")
    else:
        excess_age = min(
            Decimal(evaluation.days_overdue - AGE_CAP) / Decimal(AGE_CAP),
            Decimal("1.00"),
        )
        escalation = Decimal("0.25") + Decimal("0.50") * excess_age
    total = base + (Decimal("100.00") - base) * escalation
    return total, age_points, amount_points, promise_points


def ranked_collectable(evaluations: list[InvoiceEval]) -> list[InvoiceEval]:
    """Score and rank collectible invoices using the C28 priority formula."""
    ranked = [
        evaluation for evaluation in evaluations
        if evaluation.state == "Collectable"
        and evaluation.collectable_amount > 0
        and not evaluation.is_not_yet_issued
    ]
    max_collectable = max(
        (evaluation.collectable_amount for evaluation in ranked),
        default=Decimal("0.00"),
    )
    for evaluation in ranked:
        (
            evaluation.score,
            evaluation.age_points,
            evaluation.amount_points,
            evaluation.promise_points,
        ) = priority_score(evaluation, max_collectable)
        base = (
            evaluation.age_points
            + evaluation.amount_points
            + evaluation.promise_points
        )
        evaluation.escalation_points = evaluation.score - base
    return sorted(
        ranked,
        key=lambda evaluation: (
            -evaluation.score,
            -evaluation.days_overdue,
            -evaluation.collectable_amount,
            evaluation.invoice_id,
        ),
    )
