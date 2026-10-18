from datetime import date
from decimal import Decimal
from pathlib import Path

from src.loader import load_fixture
from src.retailer import retailer_history, retailer_risk
from src.rules import evaluate_all


ROOT = Path(__file__).parents[1]
DATASET = ROOT / "data" / "real_world_synthetic.json"


def test_real_world_synthetic_dataset_loads_all_invoice_scenarios():
    result = load_fixture(DATASET)

    assert len(result.invoices) == 12
    assert len(result.receipts) == 7
    assert result.errors == []
    assert result.as_of_date == date(2026, 10, 18)
    assert result.metadata["synthetic"] is True


def test_real_world_synthetic_dataset_covers_expected_behaviors():
    result = load_fixture(DATASET)
    evaluations = {
        item.invoice_id: item
        for item in evaluate_all(result.invoices, result.receipts, result.as_of_date)
    }

    assert evaluations["RW-003-DISPUTE-OPEN"].review_amount == Decimal("30000.00")
    assert evaluations["RW-004-REPLACEMENT"].review_amount == Decimal("0.00")
    assert evaluations["RW-005-CREDIT-NOTE"].credit_applied == Decimal("15000.00")
    assert evaluations["RW-006-PROMISE-ACTIVE"].promise_status == "active"
    assert evaluations["RW-007-PROMISE-BROKEN"].promise_status == "broken"
    assert evaluations["RW-008-PROMISE-KEPT"].promise_status == "kept"
    assert evaluations["RW-009-SETTLEMENT"].outstanding == Decimal("90000.00")
    assert evaluations["RW-010-OVERPAID"].overpaid_amount == Decimal("5000.00")
    assert evaluations["RW-011-FUTURE"].is_not_yet_issued is True


def test_real_world_synthetic_dataset_exercises_retailer_history():
    result = load_fixture(DATASET)
    history = retailer_history(result.invoices, result.receipts, result.as_of_date)

    aarav = history["Aarav General Store"]
    assert aarav.completed_invoice_count == 1
    assert aarav.on_time_payment_count == 1
    assert retailer_risk(aarav).category == "Insufficient history"
