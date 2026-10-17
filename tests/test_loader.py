import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from src.loader import load_fixture


ROOT = Path(__file__).parents[1]


def test_starter_fixture_maps_and_normalizes():
    result = load_fixture(ROOT / "data" / "fixture.json")

    assert len(result.invoices) == 6
    assert result.as_of_date == date(2026, 10, 16)
    assert result.invoices[0].invoice_id == "INV1"
    assert result.invoices[0].amount == Decimal("10000.00")
    assert result.invoices[0].received_amount == Decimal("4000.00")
    assert result.metadata["case_id"] == "C28"


def test_input_fixture_is_not_modified():
    path = ROOT / "data" / "fixture.json"
    before = path.read_bytes()
    load_fixture(path)
    assert path.read_bytes() == before


def test_invalid_rows_are_excluded_and_all_errors_are_collected(tmp_path):
    path = tmp_path / "invalid.json"
    path.write_text(json.dumps({
        "records": {
            "as_of": "2026-10-16",
            "invoices": [
                {"id": "GOOD", "customer": "C1", "amount_inr": 10,
                 "received_inr": 0, "due": "2026-10-01"},
                {"id": "BAD", "customer": "C2", "amount_inr": -1,
                 "received_inr": 0, "due": "not-a-date"},
                {"id": "GOOD", "customer": "C3", "amount_inr": 20,
                 "received_inr": 0, "due": "2026-10-01"},
            ],
            "receipts": [
                {"receipt_id": "R1", "invoice_id": "MISSING", "amount": 5}
            ],
        }
    }), encoding="utf-8")

    result = load_fixture(path)

    assert [invoice.invoice_id for invoice in result.invoices] == ["GOOD"]
    assert any(error.field == "due_date" for error in result.errors)
    assert any(error.field == "invoice_id" and "duplicate" in error.problem
               for error in result.errors)
    assert any(error.field == "invoice_id" and "unknown" in error.problem
               for error in result.errors)
    assert result.receipts[0].invoice_id is None


def test_optional_receipts_and_promise_fields_are_normalized(tmp_path):
    path = tmp_path / "extended.json"
    path.write_text(json.dumps({
        "records": {
            "as_of": "2026-10-16",
            "invoices": [{
                "id": "INV1", "customer": "C1", "amount_inr": 100,
                "received_inr": 0, "due": "2026-10-01",
                "promise_made_date": "2026-10-10",
                "promise_date": "2026-10-15", "promise_amount": 50,
            }],
            "receipts": [{
                "receipt_id": "R1", "invoice_id": "INV1", "customer": "C1",
                "amount": 25, "receipt_date": "2026-10-12",
            }],
        }
    }), encoding="utf-8")

    result = load_fixture(path)

    assert result.receipts[0].amount == Decimal("25.00")
    assert result.invoices[0].promise_date == date(2026, 10, 15)
    assert result.invoices[0].promise_amount == Decimal("50.00")


def test_csv_rows_are_supported(tmp_path):
    path = tmp_path / "invoices.csv"
    path.write_text(
        "invoice_id,customer,amount,due_date,received_amount\n"
        "INV1,C1,100.5,2026-10-01,25\n",
        encoding="utf-8",
    )

    result = load_fixture(path)

    assert len(result.invoices) == 1
    assert result.invoices[0].amount == Decimal("100.50")
    assert result.invoices[0].received_amount == Decimal("25.00")
    assert any(error.field == "as_of_date" for error in result.errors)


def test_null_values_are_reported_and_rows_are_excluded(tmp_path):
    path = tmp_path / "nulls.json"
    path.write_text(json.dumps({
        "records": {
            "as_of": "2026-10-16",
            "invoices": [
                {"id": "NULL_DUE", "customer": "C1", "amount_inr": 10,
                 "received_inr": 0, "due": None},
                {"id": "NULL_RECEIVED", "customer": "C2", "amount_inr": 10,
                 "received_inr": None, "due": "2026-10-01"},
            ],
        }
    }), encoding="utf-8")

    result = load_fixture(path)

    assert result.invoices == []
    assert any(error.field == "due_date" for error in result.errors)
    assert any(error.field == "received_amount" and "unknown" in error.problem
               for error in result.errors)


def test_invalid_optional_dispute_and_promise_fields_do_not_drop_invoice(tmp_path):
    path = tmp_path / "invalid_optional.json"
    path.write_text(json.dumps({
        "records": {
            "as_of": "2026-10-16",
            "invoices": [{
                "id": "INV1", "customer": "C1", "amount_inr": 100,
                "received_inr": 0, "due": "2026-10-01",
                "disputed": True, "dispute_resolution": "credit_note",
                "disputed_amount": 10, "credit_amount": 20,
                "promise_made_date": "2026-10-10",
                "promise_date": "2026-10-09", "promise_amount": 10,
            }],
        }
    }), encoding="utf-8")

    result = load_fixture(path)

    assert [invoice.invoice_id for invoice in result.invoices] == ["INV1"]
    invoice = result.invoices[0]
    assert invoice.dispute_resolution == "none"
    assert invoice.credit_amount == Decimal("0.00")
    assert invoice.promise_date is None
    assert any(error.field == "promise_date" for error in result.errors)
    assert any(error.field == "credit_amount" for error in result.errors)


def test_receipts_require_positive_amounts(tmp_path):
    path = tmp_path / "bad_receipts.json"
    path.write_text(json.dumps({
        "records": {
            "as_of": "2026-10-16",
            "invoices": [{
                "id": "INV1", "customer": "C1", "amount_inr": 100,
                "received_inr": 0, "due": "2026-10-01",
            }],
            "receipts": [
                {"receipt_id": "R1", "invoice_id": "INV1", "amount": 0},
                {"receipt_id": "R2", "invoice_id": "INV1", "amount": -1},
            ],
        }
    }), encoding="utf-8")

    result = load_fixture(path)

    assert result.receipts == []
    assert sum(error.field == "amount" for error in result.errors) == 2
