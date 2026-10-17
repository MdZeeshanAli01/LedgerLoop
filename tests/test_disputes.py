from datetime import date
from decimal import Decimal

from src.disputes import explain, split_balance, validate_dispute
from src.loader import Invoice
from src.rules import evaluate_all


AS_OF = date(2026, 9, 26)


def invoice(**kwargs):
    values = {
        "invoice_id": "INV-1",
        "customer": "C1",
        "amount": Decimal("10000.00"),
        "received_amount": Decimal("4000.00"),
        "due_date": date(2026, 9, 1),
    }
    values.update(kwargs)
    return Invoice(**values)


def test_pending_partial_dispute_splits_balance_and_remains_collectable():
    item = invoice(
        disputed=True,
        dispute_status="open",
        disputed_amount=Decimal("2000.00"),
        dispute_cause="damaged_goods",
        dispute_resolution="pending",
    )
    evaluation = evaluate_all([item], [], AS_OF)[0]
    assert evaluation.outstanding == Decimal("6000.00")
    assert evaluation.review_amount == Decimal("2000.00")
    assert evaluation.collectable_amount == Decimal("4000.00")
    assert evaluation.state == "Collectable"


def test_whole_dispute_is_under_review():
    item = invoice(disputed=True, dispute_status="open", dispute_resolution="pending")
    evaluation = evaluate_all([item], [], AS_OF)[0]
    assert evaluation.review_amount == Decimal("6000.00")
    assert evaluation.collectable_amount == Decimal("0.00")
    assert evaluation.state == "Under Review"


def test_replacement_not_delivered_holds_disputed_part():
    item = invoice(
        disputed=True,
        disputed_amount=Decimal("2000.00"),
        dispute_cause="short_delivery",
        dispute_resolution="replace_goods",
        replacement_delivered=False,
    )
    assert split_balance(item, Decimal("6000.00")) == (
        Decimal("2000.00"), Decimal("4000.00")
    )


def test_replacement_delivered_makes_full_balance_collectable():
    item = invoice(
        disputed=True,
        disputed_amount=Decimal("2000.00"),
        dispute_cause="short_delivery",
        dispute_resolution="replace_goods",
        replacement_delivered=True,
    )
    assert split_balance(item, Decimal("6000.00")) == (
        Decimal("0.00"), Decimal("6000.00")
    )


def test_credit_note_reduces_outstanding_and_is_collectable():
    item = invoice(
        disputed=True,
        disputed_amount=Decimal("2000.00"),
        dispute_cause="wrong_price",
        dispute_resolution="credit_note",
        credit_amount=Decimal("1500.00"),
    )
    evaluation = evaluate_all([item], [], AS_OF)[0]
    assert evaluation.credit_applied == Decimal("1500.00")
    assert evaluation.outstanding == Decimal("4500.00")
    assert evaluation.review_amount == Decimal("0.00")
    assert evaluation.collectable_amount == Decimal("4500.00")


def test_invalid_dispute_amounts_are_reported():
    item = invoice(
        disputed_amount=Decimal("7000.00"),
        dispute_resolution="credit_note",
        credit_amount=Decimal("8000.00"),
    )
    errors = validate_dispute(item, Decimal("4000.00"))
    assert any("balance before credit" in error for error in errors)
    assert any("credit_amount" in error for error in errors)


def test_explanation_matches_required_settled_example():
    item = invoice(
        disputed=True,
        disputed_amount=Decimal("2000.00"),
        dispute_cause="damaged_goods",
        dispute_resolution="credit_note",
        credit_amount=Decimal("1500.00"),
    )
    evaluation = evaluate_all([item], [], AS_OF)[0]
    assert explain(evaluation) == (
        "Invoice INV-1: amount 10000. Receipts applied 4000. "
        "Disputed 2000 (damaged goods). Settled financially: credit of "
        "1500 agreed. Remaining disputed amount 500 is payable. "
        "Outstanding 4500: collectable 4500, under review 0. "
        "Due 2026-09-01, 25 days overdue (1-30) as of 2026-09-26."
    )


def test_boolean_starter_dispute_explanation_holds_full_balance():
    item = invoice(disputed=True)
    evaluation = evaluate_all([item], [], AS_OF)[0]
    assert "Disputed 6000 (dispute detail missing)." in explain(evaluation)
    assert evaluation.state == "Under Review"
