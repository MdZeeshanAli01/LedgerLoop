from datetime import date, datetime
from decimal import Decimal

from src.loader import Invoice, Receipt
from src.retailer import (
    ComplaintCase,
    CreditDecision,
    complaint_action,
    credit_recommendation,
    retailer_history,
    retailer_risk,
    validate_complaint,
    validate_credit_decision,
)


AS_OF = date(2026, 10, 16)


def invoice(invoice_id, due_day, amount="10000", customer="Retailer"):
    return Invoice(
        invoice_id=invoice_id,
        customer=customer,
        amount=Decimal(amount),
        due_date=date(2026, 10, due_day),
    )


def test_history_counts_only_dated_completed_payments_as_on_time():
    invoices = [invoice("I1", 1), invoice("I2", 10), invoice("I3", 12)]
    receipts = [
        Receipt("R1", "I1", "Retailer", Decimal("10000"), date(2026, 10, 1)),
        Receipt("R2", "I2", "Retailer", Decimal("10000"), date(2026, 10, 12)),
    ]

    history = retailer_history(invoices, receipts, AS_OF)["Retailer"]

    assert history.invoice_count == 3
    assert history.completed_invoice_count == 2
    assert history.on_time_payment_count == 1
    assert history.late_payment_count == 1
    assert history.average_days_late == Decimal("2.00")
    assert history.eligible_history is False


def test_history_tracks_outstanding_and_broken_promises():
    item = invoice("I1", 1)
    item.promise_made_date = date(2026, 10, 1)
    item.promise_date = date(2026, 10, 5)
    item.promise_amount = Decimal("10000")

    history = retailer_history([item], [], AS_OF)["Retailer"]

    assert history.outstanding == Decimal("10000.00")
    assert history.broken_promise_count == 1


def test_risk_requires_three_completed_invoices():
    history = retailer_history([invoice("I1", 1)], [], AS_OF)["Retailer"]

    risk = retailer_risk(history)

    assert risk.rating is None
    assert risk.category == "Insufficient history"
    assert risk.eligible is False


def test_risk_is_transparent_and_low_for_reliable_retailer():
    invoices = [invoice(f"I{i}", i) for i in (1, 2, 3)]
    receipts = [
        Receipt(f"R{i}", f"I{i}", "Retailer", Decimal("10000"), date(2026, 10, i))
        for i in (1, 2, 3)
    ]

    risk = retailer_risk(retailer_history(invoices, receipts, AS_OF)["Retailer"])

    assert risk.rating == Decimal("0.00")
    assert risk.category == "Excellent"
    assert len(risk.explanation) == 4


def test_unknown_retailer_gets_safe_standard_terms():
    history = retailer_history([invoice("I1", 1)], [], AS_OF)["Retailer"]
    risk = retailer_risk(history)

    recommendation = credit_recommendation(risk, history, Decimal("100000"))

    assert recommendation.purchasing_multiplier == Decimal("100000.00")
    assert recommendation.upfront_percent == Decimal("50")
    assert recommendation.credit_percent == Decimal("50")
    assert recommendation.approval_required is True


def test_five_on_time_payments_unlock_stronger_terms():
    invoices = [invoice(f"I{i}", i) for i in range(1, 6)]
    receipts = [
        Receipt(f"R{i}", f"I{i}", "Retailer", Decimal("10000"), date(2026, 10, i))
        for i in range(1, 6)
    ]
    history = retailer_history(invoices, receipts, AS_OF)["Retailer"]
    recommendation = credit_recommendation(
        retailer_risk(history), history, Decimal("100000")
    )

    assert recommendation.upfront_percent == Decimal("40")
    assert recommendation.credit_percent == Decimal("60")


def test_complaints_escalate_without_automatically_penalizing_retailer():
    first = ComplaintCase("C1", "Retailer", "I1", "Damaged goods")
    second = ComplaintCase("C2", "Retailer", "I2", "Damaged goods")
    third = ComplaintCase("C3", "Retailer", "I3", "Damaged goods")

    assert complaint_action("Retailer", []) == "accept_and_review"
    assert complaint_action("Retailer", [first]) == "distributor_validation_required"
    assert complaint_action("Retailer", [first, second]) == "inspection_required"
    assert complaint_action("Retailer", [first, second, third]) == "inspection_required"


def test_retailer_fault_requires_evidence():
    complaint = ComplaintCase(
        "C1", "Retailer", "I1", "Damaged goods",
        status="verified_retailer_fault",
    )

    assert validate_complaint(complaint) == [
        "retailer-fault complaints require an evidence note"
    ]


def test_credit_recommendation_decision_requires_auditable_manager_reason():
    pending = CreditDecision("Retailer", "pending")
    approved = CreditDecision(
        "Retailer", "approved", "manager@example.com",
        datetime(2026, 10, 18), "Approved after reviewing payment history.",
    )

    assert validate_credit_decision(pending) == []
    assert validate_credit_decision(approved) == []


def test_credit_override_requires_terms_totalling_one_hundred_percent():
    override = CreditDecision(
        "Retailer", "overridden", "manager@example.com",
        datetime(2026, 10, 18), "Approved exception.",
        Decimal("45"), Decimal("50"),
    )

    assert validate_credit_decision(override) == [
        "approved payment terms must total 100%"
    ]
