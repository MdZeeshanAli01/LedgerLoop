from datetime import date
from decimal import Decimal

from src.drafts import draft_for_customer, drafts_for_customers
from src.loader import Invoice
from src.rules import evaluate_all


def make_invoice(invoice_id="INV1", customer="C1", due=date(2026, 9, 1), **kwargs):
    return Invoice(
        invoice_id=invoice_id,
        customer=customer,
        amount=Decimal("10000"),
        received_amount=Decimal("0"),
        due_date=due,
        **kwargs,
    )


def test_early_overdue_draft_uses_collectable_amount_and_gentle_tone():
    item = make_invoice()
    evaluation = evaluate_all([item], [], date(2026, 9, 26))[0]

    draft = draft_for_customer("C1", [evaluation])

    assert draft["status"] == "DRAFT - not sent"
    assert "totalling 10000" in draft["body"]
    assert "friendly reminder" in draft["body"]
    assert "send" not in draft


def test_oldest_bucket_chooses_formal_tone():
    item = make_invoice(due=date(2026, 6, 1))
    evaluation = evaluate_all([item], [], date(2026, 10, 16))[0]

    draft = draft_for_customer("C1", [evaluation])

    assert "Dear C1" in draft["body"]
    assert "over 137 days overdue" in draft["body"]


def test_active_promise_gets_no_chase_draft():
    item = make_invoice(
        promise_made_date=date(2026, 9, 10),
        promise_date=date(2026, 9, 30),
        promise_amount=Decimal("10000"),
    )
    evaluation = evaluate_all([item], [], date(2026, 9, 26))[0]

    draft = draft_for_customer("C1", [evaluation])

    assert draft["body"] == "No message needed. Next check: 2026-09-30."


def test_under_review_only_gets_dispute_note():
    item = make_invoice(
        disputed=True,
        dispute_resolution="pending",
    )
    evaluation = evaluate_all([item], [], date(2026, 9, 26))[0]

    draft = draft_for_customer("C1", [evaluation])

    assert "looking into your concern" in draft["body"]
    assert "10000" not in draft["body"]


def test_broken_promise_is_at_least_firm_and_names_shortfall():
    item = make_invoice(
        promise_made_date=date(2026, 9, 10),
        promise_date=date(2026, 9, 20),
        promise_amount=Decimal("10000"),
    )
    evaluation = evaluate_all([item], [], date(2026, 9, 26))[0]

    draft = draft_for_customer("C1", [evaluation])

    assert "agreed to pay 10000" in draft["body"]
    assert "2026-09-20" in draft["body"]
    assert "friendly reminder" not in draft["body"]


def test_partial_dispute_is_visible_in_collectable_draft():
    item = make_invoice(
        disputed=True,
        disputed_amount=Decimal("2000"),
        dispute_cause="damaged_goods",
        dispute_resolution="pending",
    )
    evaluation = evaluate_all([item], [], date(2026, 9, 26))[0]

    draft = draft_for_customer("C1", [evaluation])

    assert "totalling 8000" in draft["body"]
    assert "reviewing 2000 on invoice INV1" in draft["body"]
    assert "not asking for that amount now" in draft["body"]


def test_drafts_are_one_per_customer():
    evaluations = evaluate_all(
        [make_invoice("INV1", "C1"), make_invoice("INV2", "C2")],
        [],
        date(2026, 9, 26),
    )

    drafts = drafts_for_customers(evaluations)

    assert [draft["customer"] for draft in drafts] == ["C1", "C2"]
