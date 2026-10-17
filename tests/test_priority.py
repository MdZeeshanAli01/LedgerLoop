from datetime import date
from decimal import Decimal

from src.loader import Invoice, Receipt
from src.disputes import explain
from src.rules import (
    AGE_CAP,
    W_AGE,
    W_AMOUNT,
    W_PROMISE,
    evaluate_all,
    priority_score,
    ranked_collectable,
)


def make_invoice(invoice_id, amount="4000", due=date(2026, 8, 29), **kwargs):
    received = kwargs.pop("received", "0")
    return Invoice(
        invoice_id=invoice_id,
        customer=invoice_id,
        amount=Decimal(amount),
        received_amount=Decimal(received),
        due_date=due,
        **kwargs,
    )


def test_active_promise_is_held_on_promise_date():
    item = make_invoice(
        "INV1",
        promise_made_date=date(2026, 10, 5),
        promise_date=date(2026, 10, 12),
        promise_amount=Decimal("4000"),
    )
    evaluation = evaluate_all([item], [], date(2026, 10, 12))[0]

    assert evaluation.promise_status == "active"
    assert evaluation.state == "Promised"
    assert evaluation.promise_shortfall == Decimal("4000.00")
    assert ranked_collectable([evaluation]) == []


def test_broken_promise_returns_to_collectable():
    item = make_invoice(
        "INV1",
        promise_made_date=date(2026, 10, 5),
        promise_date=date(2026, 10, 12),
        promise_amount=Decimal("4000"),
    )
    evaluation = evaluate_all([item], [], date(2026, 10, 13))[0]

    assert evaluation.promise_status == "broken"
    assert evaluation.state == "Collectable"
    assert evaluation.broken_promise is True


def test_receipts_after_promise_made_reduce_shortfall():
    item = make_invoice(
        "INV1",
        promise_made_date=date(2026, 10, 5),
        promise_date=date(2026, 10, 12),
        promise_amount=Decimal("3000"),
    )
    receipt = Receipt("R1", "INV1", "INV1", Decimal("1500"), date(2026, 10, 8))
    evaluation = evaluate_all([item], [receipt], date(2026, 10, 13))[0]

    assert evaluation.promised_paid == Decimal("1500.00")
    assert evaluation.promise_shortfall == Decimal("1500.00")


def test_receipt_before_promise_made_does_not_count():
    item = make_invoice(
        "INV1",
        promise_made_date=date(2026, 10, 5),
        promise_date=date(2026, 10, 12),
        promise_amount=Decimal("3000"),
    )
    receipt = Receipt("R1", "INV1", "INV1", Decimal("1500"), date(2026, 10, 4))
    evaluation = evaluate_all([item], [receipt], date(2026, 10, 13))[0]

    assert evaluation.promised_paid == Decimal("0.00")


def test_paid_invoice_ignores_promise():
    item = make_invoice(
        "INV1",
        amount="4000",
        received="4000",
        promise_made_date=date(2026, 10, 5),
        promise_date=date(2026, 10, 12),
        promise_amount=Decimal("4000"),
    )
    evaluation = evaluate_all([item], [], date(2026, 10, 13))[0]

    assert evaluation.state == "Paid"
    assert evaluation.promise_status == "none"


def test_priority_weights_sum_to_one():
    assert W_AGE + W_AMOUNT + W_PROMISE == Decimal("1.00")


def test_broken_promise_can_rank_above_older_small_balance():
    invoice_a = make_invoice(
        "A",
        amount="4000",
        due=date(2026, 8, 29),
        promise_made_date=date(2026, 10, 1),
        promise_date=date(2026, 10, 12),
        promise_amount=Decimal("4000"),
    )
    invoice_b = make_invoice("B", amount="1000", due=date(2026, 7, 25))
    invoice_c = make_invoice("C", amount="8000", due=date(2026, 8, 29))
    evaluations = evaluate_all([invoice_a, invoice_b, invoice_c], [], date(2026, 10, 13))

    ranked = ranked_collectable(evaluations)
    assert ranked[0].invoice_id == "A"
    assert ranked[0].score == Decimal("60.00000000000000000000000000")
    score_by_id = {item.invoice_id: item.score for item in ranked}
    assert score_by_id["B"].quantize(Decimal("0.1")) == Decimal("44.4")


def test_age_score_is_capped_at_ninety_days():
    item = make_invoice("INV1", due=date(2026, 6, 18))
    evaluation = evaluate_all([item], [], date(2026, 10, 16))[0]
    total, age_points, _, _ = priority_score(evaluation, evaluation.collectable_amount)

    assert evaluation.days_overdue == 120
    assert age_points == Decimal("45.00")
    assert AGE_CAP == 90
    assert total == Decimal("80.00")


def test_broken_promise_explanation_includes_shortfall_and_score():
    item = make_invoice(
        "INV-2",
        amount="4000",
        due=date(2026, 8, 29),
        promise_made_date=date(2026, 10, 1),
        promise_date=date(2026, 10, 12),
        promise_amount=Decimal("4000"),
    )
    evaluation = evaluate_all([item], [], date(2026, 10, 13))[0]
    ranked = ranked_collectable([evaluation])
    text = explain(ranked[0])

    assert "Promise missed, shortfall 4000." in text
    assert "Score 77.5" in text
