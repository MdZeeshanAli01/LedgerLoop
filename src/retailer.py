"""Retailer-level risk evidence and distributor credit recommendations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Iterable

from .loader import Invoice, Receipt, MONEY_QUANTUM
from .rules import InvoiceEval, evaluate_all


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM)


@dataclass(frozen=True)
class RetailerHistory:
    retailer: str
    invoice_count: int
    total_billed: Decimal
    completed_invoice_count: int
    on_time_payment_count: int
    late_payment_count: int
    average_days_late: Decimal
    outstanding: Decimal
    broken_promise_count: int
    verified_complaint_count: int = 0
    eligible_history: bool = False


def _receipt_total(invoice: Invoice, receipts: list[Receipt], as_of: date) -> Decimal:
    detailed = [
        receipt for receipt in receipts
        if receipt.invoice_id == invoice.invoice_id
        and (receipt.receipt_date is None or receipt.receipt_date <= as_of)
    ]
    if detailed:
        return _money(sum((item.amount for item in detailed), Decimal("0.00")))
    return invoice.received_amount


def _completion_date(invoice: Invoice, receipts: list[Receipt], as_of: date) -> date | None:
    detailed = [
        receipt.receipt_date for receipt in receipts
        if receipt.invoice_id == invoice.invoice_id
        and receipt.receipt_date is not None
        and receipt.receipt_date <= as_of
    ]
    if not detailed:
        return None
    return max(detailed)


def retailer_history(
    invoices: Iterable[Invoice],
    receipts: list[Receipt],
    as_of: date,
    complaints: Iterable[object] = (),
) -> dict[str, RetailerHistory]:
    """Aggregate payment behavior without treating missing dates as on-time."""
    invoice_list = list(invoices)
    evaluations = evaluate_all(invoice_list, receipts, as_of)
    complaint_counts: dict[str, int] = {}
    for complaint in complaints:
        retailer = getattr(complaint, "retailer", None)
        if retailer and getattr(complaint, "status", None) == "verified_retailer_fault":
            complaint_counts[retailer] = complaint_counts.get(retailer, 0) + 1

    grouped: dict[str, list[InvoiceEval]] = {}
    for evaluation in evaluations:
        grouped.setdefault(evaluation.customer, []).append(evaluation)

    history: dict[str, RetailerHistory] = {}
    for retailer, items in grouped.items():
        completed = 0
        on_time = 0
        late = 0
        late_days: list[int] = []
        for item in items:
            paid = _receipt_total(item.invoice, receipts, as_of) + item.credit_applied
            if paid < item.invoice.amount:
                continue
            completed += 1
            completed_on = _completion_date(item.invoice, receipts, as_of)
            if completed_on is not None and completed_on <= item.invoice.due_date:
                on_time += 1
            elif completed_on is not None:
                late += 1
                late_days.append((completed_on - item.invoice.due_date).days)
        average_late = (
            Decimal(sum(late_days)) / Decimal(len(late_days))
            if late_days else Decimal("0.00")
        )
        history[retailer] = RetailerHistory(
            retailer=retailer,
            invoice_count=len(items),
            total_billed=_money(sum((item.invoice.amount for item in items), Decimal("0.00"))),
            completed_invoice_count=completed,
            on_time_payment_count=on_time,
            late_payment_count=late,
            average_days_late=_money(average_late),
            outstanding=_money(sum((item.outstanding for item in items), Decimal("0.00"))),
            broken_promise_count=sum(item.broken_promise for item in items),
            verified_complaint_count=complaint_counts.get(retailer, 0),
            eligible_history=completed >= 3,
        )
    return history


@dataclass(frozen=True)
class RetailerRisk:
    retailer: str
    rating: Decimal | None
    category: str
    eligible: bool
    explanation: tuple[str, ...]
    lateness_points: Decimal = Decimal("0.00")
    age_points: Decimal = Decimal("0.00")
    balance_points: Decimal = Decimal("0.00")
    promise_points: Decimal = Decimal("0.00")
    complaint_points: Decimal = Decimal("0.00")


def retailer_risk(history: RetailerHistory) -> RetailerRisk:
    """Return a low-is-good 0-100 rating with component evidence."""
    if not history.eligible_history:
        return RetailerRisk(
            history.retailer, None, "Insufficient history", False,
            ("Complete at least 3 invoices before assigning a risk rating.",),
        )
    completed = Decimal(history.completed_invoice_count)
    lateness = Decimal(history.late_payment_count) / completed
    lateness_points = min(Decimal("35.00"), lateness * Decimal("35.00"))
    age_points = min(
        Decimal("25.00"),
        history.average_days_late / Decimal("90.00") * Decimal("25.00"),
    )
    balance_ratio = (
        history.outstanding / history.total_billed
        if history.total_billed else Decimal("1.00")
    )
    balance_points = min(Decimal("15.00"), balance_ratio * Decimal("15.00"))
    promise_points = min(
        Decimal("15.00"),
        Decimal(history.broken_promise_count) / completed * Decimal("15.00"),
    )
    complaint_points = min(
        Decimal("10.00"),
        Decimal(history.verified_complaint_count) * Decimal("5.00"),
    )
    rating = _money(
        lateness_points + age_points + balance_points + promise_points + complaint_points
    )
    if rating <= 10:
        category = "Excellent"
    elif rating <= 20:
        category = "Very good"
    elif rating <= 40:
        category = "Good"
    elif rating <= 50:
        category = "Acceptable"
    elif rating <= 60:
        category = "Moderate"
    elif rating <= 70:
        category = "Watchlist"
    elif rating <= 80:
        category = "High risk"
    elif rating <= 90:
        category = "Very high risk"
    else:
        category = "Critical"
    return RetailerRisk(
        history.retailer, rating, category, True,
        (
            f"{history.on_time_payment_count} of {history.completed_invoice_count} completed invoices were paid on time.",
            f"Average late payment: {history.average_days_late} days.",
            f"Current outstanding: {_money(history.outstanding)}.",
            f"Broken promises: {history.broken_promise_count}.",
        ),
        lateness_points, age_points, balance_points, promise_points, complaint_points,
    )


@dataclass(frozen=True)
class CreditRecommendation:
    retailer: str
    risk_rating: Decimal | None
    risk_category: str
    purchasing_multiplier: Decimal
    upfront_percent: Decimal
    credit_percent: Decimal
    approval_required: bool
    reason: str


COMPLAINT_STATUSES = {
    "open",
    "verified_distributor_fault",
    "verified_retailer_fault",
    "inconclusive",
    "inspection_required",
    "closed",
}


@dataclass(frozen=True)
class ComplaintCase:
    complaint_id: str
    retailer: str
    invoice_id: str | None
    description: str
    status: str = "open"
    evidence_note: str | None = None
    inspection_outcome: str | None = None


@dataclass(frozen=True)
class CreditDecision:
    retailer: str
    status: str
    decided_by: str | None = None
    decided_at: datetime | None = None
    note: str | None = None
    approved_upfront_percent: Decimal | None = None
    approved_credit_percent: Decimal | None = None


DECISION_STATUSES = {"pending", "approved", "rejected", "overridden"}


def validate_credit_decision(decision: CreditDecision) -> list[str]:
    errors: list[str] = []
    if decision.status not in DECISION_STATUSES:
        errors.append("status is not supported")
    if decision.status != "pending":
        if not decision.decided_by:
            errors.append("decided_by is required")
        if decision.decided_at is None:
            errors.append("decided_at is required")
        if not decision.note:
            errors.append("decision note is required")
    if decision.status == "overridden":
        if decision.approved_upfront_percent is None or decision.approved_credit_percent is None:
            errors.append("override requires approved payment terms")
        elif (
            decision.approved_upfront_percent
            + decision.approved_credit_percent
            != Decimal("100")
        ):
            errors.append("approved payment terms must total 100%")
    return errors


def complaint_action(
    retailer: str, complaints: Iterable[ComplaintCase]
) -> str:
    """Return the next control step without making an ethical finding."""
    prior = [
        complaint for complaint in complaints
        if complaint.retailer == retailer
        and complaint.status != "closed"
    ]
    count = len(prior)
    if count == 0:
        return "accept_and_review"
    if count == 1:
        return "distributor_validation_required"
    return "inspection_required"


def validate_complaint(complaint: ComplaintCase) -> list[str]:
    errors: list[str] = []
    if not complaint.complaint_id.strip():
        errors.append("complaint_id is required")
    if not complaint.retailer.strip():
        errors.append("retailer is required")
    if not complaint.description.strip():
        errors.append("description is required")
    if complaint.status not in COMPLAINT_STATUSES:
        errors.append("status is not supported")
    if complaint.status == "verified_retailer_fault" and not complaint.evidence_note:
        errors.append("retailer-fault complaints require an evidence note")
    return errors


def credit_recommendation(
    risk: RetailerRisk, history: RetailerHistory, reference_limit: Decimal
) -> CreditRecommendation:
    """Suggest exposure only; a finance manager must approve the terms."""
    if not risk.eligible or risk.rating is None:
        upfront, credit, multiplier = Decimal("50"), Decimal("50"), Decimal("1.00")
        reason = "New or insufficient-history retailer: use standard 50% upfront terms."
    elif risk.rating <= 10:
        multiplier, upfront, credit = Decimal("1.80"), Decimal("45"), Decimal("55")
        reason = "Excellent payment history supports the strongest suggested limit."
    elif risk.rating <= 20:
        multiplier, upfront, credit = Decimal("1.70"), Decimal("45"), Decimal("55")
        reason = "Very good payment history supports expanded credit."
    elif risk.rating <= 30:
        multiplier, upfront, credit = Decimal("1.50"), Decimal("50"), Decimal("50")
        reason = "Good risk profile supports a measured increase in purchasing power."
    elif risk.rating <= 50:
        multiplier, upfront, credit = Decimal("1.30"), Decimal("50"), Decimal("50")
        reason = "Acceptable risk profile supports standard credit terms."
    elif risk.rating <= 60:
        multiplier, upfront, credit = Decimal("1.00"), Decimal("60"), Decimal("40")
        reason = "Moderate risk requires reduced credit exposure."
    elif risk.rating <= 70:
        multiplier, upfront, credit = Decimal("0.90"), Decimal("70"), Decimal("30")
        reason = "Watchlist status requires stronger upfront payment."
    elif risk.rating <= 80:
        multiplier, upfront, credit = Decimal("0.80"), Decimal("80"), Decimal("20")
        reason = "High risk requires very limited credit."
    else:
        multiplier, upfront, credit = Decimal("0.00"), Decimal("100"), Decimal("0")
        reason = "Very high or critical risk: no new credit without exceptional approval."

    if history.on_time_payment_count >= 5 and risk.rating is not None and risk.rating <= 50:
        upfront, credit = Decimal("40"), Decimal("60")
        reason += " Five or more verified on-time payments support a trust benefit."
    elif history.on_time_payment_count >= 1 and risk.rating is not None and risk.rating <= 50:
        upfront, credit = Decimal("45"), Decimal("55")
        reason += " Verified on-time payment history supports a trust benefit."
    return CreditRecommendation(
        risk.retailer, risk.rating, risk.category,
        _money(reference_limit * multiplier), upfront, credit, True, reason,
    )
