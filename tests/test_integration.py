import json
from decimal import Decimal
from pathlib import Path

from src.drafts import drafts_for_customers
from src.export import write_evidence_log, write_result_csv, write_result_json
from src.loader import load_fixture
from src.rules import evaluate_all, ranked_collectable, unapplied_receipts


ROOT = Path(__file__).parents[1]


def test_synthetic_fixture_runs_through_complete_workflow(tmp_path):
    result = load_fixture(ROOT / "data" / "extra_synthetic.json")
    evaluations = evaluate_all(result.invoices, result.receipts, result.as_of_date)

    assert len(result.invoices) == 3
    assert len(result.errors) >= 1
    partial = next(item for item in evaluations if item.invoice_id == "SYN-PARTIAL")
    disputed = next(item for item in evaluations if item.invoice_id == "SYN-DISPUTE")
    promised = next(item for item in evaluations if item.invoice_id == "SYN-PROMISE")
    assert partial.outstanding == Decimal("9000.00")
    assert disputed.review_amount == Decimal("2000.00")
    assert disputed.collectable_amount == Decimal("8000.00")
    assert promised.state == "Collectable"
    assert promised.broken_promise is True
    assert len(unapplied_receipts(result.receipts, result.as_of_date)) == 1
    assert drafts_for_customers(evaluations)
    assert ranked_collectable(evaluations)[0].invoice_id == "SYN-PROMISE"

    json_path = tmp_path / "result.json"
    csv_path = tmp_path / "result.csv"
    evidence_path = tmp_path / "evidence_log.md"
    write_result_json(evaluations, json_path)
    write_result_csv(evaluations, csv_path)
    write_evidence_log(
        evidence_path,
        evaluations,
        fixture_name="data/extra_synthetic.json",
        receipt_count=len(result.receipts),
        validation_errors=result.errors,
        tests_passed=1,
        tests_total=1,
    )
    exported = json.loads(json_path.read_text(encoding="utf-8"))
    assert exported[0]["as_of_date"] == "2026-10-16"
    assert csv_path.exists()
    assert "Figures come from synthetic data" in evidence_path.read_text(encoding="utf-8")
