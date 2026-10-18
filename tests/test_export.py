import csv
import json
from datetime import date, datetime
from decimal import Decimal

from src.export import (
    evaluation_record,
    write_evidence_log,
    write_result_csv,
    write_result_json,
    write_starting_state,
    negotiated_record,
)
from src.negotiated import (
    AgreementStatus,
    RecoveryAgreement,
    RecoveryProgress,
    RecoveryTargetType,
)
from src.loader import Invoice, ValidationError
from src.rules import evaluate_all


def make_eval():
    invoice = Invoice(
        invoice_id="INV1",
        customer="C1",
        amount=Decimal("10000"),
        received_amount=Decimal("4000"),
        due_date=date(2026, 9, 1),
    )
    return evaluate_all([invoice], [], date(2026, 9, 26))


def test_evaluation_record_is_json_safe_and_reproducible():
    record = evaluation_record(make_eval()[0])

    assert record["amount"] == "10000.00"
    assert record["as_of_date"] == "2026-09-26"
    assert record["outstanding"] == "6000.00"
    assert record["state"] == "Collectable"
    assert "explanation" in record
    json.dumps(record)


def test_json_and_csv_exports_include_computed_fields(tmp_path):
    evaluations = make_eval()
    json_path = tmp_path / "result.json"
    csv_path = tmp_path / "result.csv"

    write_result_json(evaluations, json_path)
    write_result_csv(evaluations, csv_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data[0]["collectable_amount"] == "6000.00"
    with csv_path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["outstanding"] == "6000.00"
    assert rows[0]["explanation"]


def test_starting_state_and_evidence_log(tmp_path):
    evaluations = make_eval()
    starting = tmp_path / "starting_state.json"
    evidence = tmp_path / "evidence_log.md"

    write_starting_state(evaluations, starting)
    write_evidence_log(
        evidence,
        evaluations,
        fixture_name="data/fixture.json",
        receipt_count=0,
        validation_errors=[ValidationError(2, "amount", "must be positive")],
        tests_passed=44,
        tests_total=44,
    )

    assert json.loads(starting.read_text(encoding="utf-8"))[0]["invoice_id"] == "INV1"
    text = evidence.read_text(encoding="utf-8")
    assert "## Starting state" in text
    assert "## Negotiated scope" in text
    assert "## Final evidence" in text
    assert "## Observed versus assumed" in text
    assert "44 passed out of 44" in text
    assert "must be positive" in text
    assert "Figures come from synthetic data" in text


def test_negotiated_export_is_json_safe(tmp_path):
    agreement = RecoveryAgreement(
        "AGR-1", "C1", "INV1", Decimal("15000"), Decimal("15000"),
        RecoveryTargetType.EXACT_BEP, Decimal("15000"),
        status=AgreementStatus.APPROVED,
        approved_by="Manager",
        approved_at=datetime(2026, 10, 18, 10, 0),
        approval_note="Reviewed.",
    )
    progress = RecoveryProgress(
        agreement=agreement,
        recovered_amount=Decimal("12000"),
        remaining_amount=Decimal("3000"),
        excess_amount=Decimal("0"),
        invoice_outstanding=Decimal("15000"),
        invoice_balance_after_target=Decimal("0"),
        status=AgreementStatus.PARTIALLY_RECOVERED,
        next_order_eligible=False,
    )

    record = negotiated_record(progress)

    assert record["agreed_target"] == "15000.00"
    assert record["approved_at"] == "2026-10-18T10:00:00"
    json.dumps(record)
