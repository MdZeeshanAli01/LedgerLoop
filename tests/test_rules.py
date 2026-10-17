from datetime import date
from decimal import Decimal

from src.loader import Invoice, Receipt
from src.loader import load_fixture
from src.rules import (
    applied_receipts,
    bucket,
    days_overdue,
    evaluate_all,
    outstanding,
    ranked_collectable,
    unapplied_receipts,
)


AS_OF = date(2026, 10, 16)
DUE = date(2026, 10, 1)


def make_invoice(invoice_id="INV1", amount="10000", received="0", due=DUE, **kwargs):
    return Invoice(
        invoice_id=invoice_id,
        customer="C1",
        amount=Decimal(amount),
        received_amount=Decimal(received),
        due_date=due,
        **kwargs,
    )


def test_partial_receipt_leaves_outstanding_balance():
    evaluation = evaluate_all([make_invoice(received="4000")], [], AS_OF)[0]

    assert evaluation.outstanding == Decimal("6000.00")
    assert evaluation.collectable_amount == Decimal("6000.00")


def test_paid_invoice_is_not_ranked():
    evaluation = evaluate_all([make_invoice(received="10000")], [], AS_OF)[0]

    assert evaluation.outstanding == Decimal("0.00")
    assert evaluation.state == "Paid"
    assert ranked_collectable([evaluation]) == []


def test_overpayment_is_capped_and_flagged():
    evaluation = evaluate_all([make_invoice(received="12000")], [], AS_OF)[0]

    assert evaluation.outstanding == Decimal("0.00")
    assert evaluation.overpaid_amount == Decimal("2000.00")


def test_overdue_and_boundary_bucket():
    assert days_overdue(date(2026, 9, 1), date(2026, 9, 26)) == 25
    assert bucket(25) == "1-30"
    assert bucket(30) == "1-30"
    assert bucket(31) == "31-60"
    assert bucket(60) == "31-60"
    assert bucket(61) == "61-90"
    assert bucket(90) == "61-90"
    assert bucket(91) == "90+"


def test_due_date_is_not_overdue_and_is_not_ranked():
    invoice = make_invoice(due=date(2026, 10, 16))
    evaluation = evaluate_all([invoice], [], AS_OF)[0]

    assert evaluation.days_overdue == 0
    assert evaluation.ageing_bucket == "Not due"
    assert evaluation.state == "Not due"
    assert ranked_collectable([evaluation]) == []


def test_before_due_date_is_not_overdue():
    invoice = make_invoice(due=date(2026, 10, 20))
    evaluation = evaluate_all([invoice], [], AS_OF)[0]

    assert evaluation.days_overdue == 0
    assert evaluation.state == "Not due"


def test_unapplied_receipt_is_not_subtracted():
    invoice = make_invoice()
    receipt = Receipt("R1", None, "C1", Decimal("4000.00"), date(2026, 10, 10))

    assert applied_receipts(invoice, [receipt], AS_OF) == Decimal("0.00")
    assert unapplied_receipts([receipt], AS_OF) == [receipt]


def test_future_receipt_is_ignored():
    invoice = make_invoice()
    receipt = Receipt("R1", "INV1", "C1", Decimal("4000.00"), date(2026, 10, 17))

    assert applied_receipts(invoice, [receipt], AS_OF) == Decimal("0.00")
    assert outstanding(invoice, [receipt], AS_OF) == Decimal("10000.00")


def test_multiple_receipts_are_added():
    invoice = make_invoice()
    receipts = [
        Receipt("R1", "INV1", "C1", Decimal("3000.00"), date(2026, 10, 1)),
        Receipt("R2", "INV1", "C1", Decimal("2000.00"), date(2026, 10, 2)),
    ]

    assert applied_receipts(invoice, receipts, AS_OF) == Decimal("5000.00")
    assert outstanding(invoice, receipts, AS_OF) == Decimal("5000.00")


def test_future_invoice_is_marked_not_yet_issued():
    invoice = make_invoice(invoice_date=date(2026, 10, 20))

    evaluation = evaluate_all([invoice], [], AS_OF)[0]

    assert evaluation.is_not_yet_issued is True


def test_c28_starter_reference_run():
    result = load_fixture("data/fixture.json")
    evaluations = evaluate_all(result.invoices, result.receipts, result.as_of_date)

    assert sum((item.outstanding for item in evaluations), Decimal("0.00")) == Decimal("46000.00")
    assert sum((item.collectable_amount for item in evaluations), Decimal("0.00")) == Decimal("36000.00")
    assert sum((item.review_amount for item in evaluations), Decimal("0.00")) == Decimal("10000.00")
    assert sum(item.state == "Paid" for item in evaluations) == 1
    assert [item.invoice_id for item in ranked_collectable(evaluations)] == [
        "INV4", "INV5", "INV6", "INV1"
    ]


def test_changing_as_of_recomputes_ageing_without_mutating_invoice():
    invoice = make_invoice()
    first = evaluate_all([invoice], [], date(2026, 10, 16))[0]
    second = evaluate_all([invoice], [], date(2026, 11, 1))[0]

    assert first.days_overdue == 15
    assert first.ageing_bucket == "1-30"
    assert second.days_overdue == 31
    assert second.ageing_bucket == "31-60"
