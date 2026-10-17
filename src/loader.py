"""Input loading, field mapping, normalization, and validation for C28."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any, Iterator

MONEY_QUANTUM = Decimal("0.01")

# The starter fixture uses these names. Keep all schema translation here.
FIELD_MAP = {
    "invoice_id": "id",
    "customer": "customer",
    "amount": "amount_inr",
    "received": "received_inr",
    "due_date": "due",
    "disputed": "disputed",
}


@dataclass
class ValidationError:
    row: int | str
    field: str
    problem: str


@dataclass
class Invoice:
    invoice_id: str
    customer: str
    amount: Decimal
    due_date: date
    received_amount: Decimal = Decimal("0.00")
    invoice_date: date | None = None
    disputed: bool = False
    dispute_status: str = "none"
    disputed_amount: Decimal | None = None
    dispute_cause: str | None = None
    dispute_resolution: str = "none"
    replacement_delivered: bool = False
    credit_amount: Decimal = Decimal("0.00")
    promise_made_date: date | None = None
    promise_date: date | None = None
    promise_amount: Decimal | None = None


@dataclass
class Receipt:
    receipt_id: str
    invoice_id: str | None
    customer: str | None
    amount: Decimal
    receipt_date: date | None = None


@dataclass
class LoadResult:
    invoices: list[Invoice]
    receipts: list[Receipt]
    as_of_date: date
    errors: list[ValidationError] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __iter__(self) -> Iterator[Any]:
        """Allow convenient unpacking while retaining named result fields."""
        yield self.invoices
        yield self.receipts
        yield self.as_of_date
        yield self.errors
        yield self.metadata


def _parse_date(value: Any, row: int | str, field_name: str,
                errors: list[ValidationError], required: bool = False) -> date | None:
    if value is None or value == "":
        if required:
            errors.append(ValidationError(row, field_name, "value is required"))
        return None
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        errors.append(ValidationError(row, field_name, "must be an ISO date"))
        return None


def _parse_money(value: Any, row: int | str, field_name: str,
                 errors: list[ValidationError], required: bool = False,
                 positive: bool = False) -> Decimal | None:
    if value is None or value == "":
        if required:
            errors.append(ValidationError(row, field_name, "value is required"))
        return None
    try:
        amount = Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        errors.append(ValidationError(row, field_name, "must be a number"))
        return None
    if positive and amount <= 0:
        errors.append(ValidationError(row, field_name, "must be greater than zero"))
        return None
    return amount


def _optional_money(value: Any, row: int | str, field_name: str,
                    errors: list[ValidationError]) -> Decimal | None:
    return _parse_money(value, row, field_name, errors, positive=False)


def _raw_records(payload: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any]:
    records = payload.get("records", payload)
    if not isinstance(records, dict):
        raise ValueError("records must be an object")
    invoices = records.get("invoices", [])
    receipts = records.get("receipts", [])
    if not isinstance(invoices, list) or not isinstance(receipts, list):
        raise ValueError("invoices and receipts must be arrays")
    return invoices, receipts, records.get("as_of", payload.get("as_of_date"))


def _normalize_dispute(raw: dict[str, Any], invoice: Invoice, row: int | str,
                       errors: list[ValidationError]) -> None:
    error_count = len(errors)
    if raw.get("disputed") is True and raw.get("dispute_status") is None:
        invoice.dispute_status = "open"
        invoice.disputed_amount = None
    status = raw.get("dispute_status")
    if status is not None:
        if status not in {"none", "open", "resolved"}:
            errors.append(ValidationError(row, "dispute_status", "must be none, open, or resolved"))
        else:
            invoice.dispute_status = status
    invoice.disputed_amount = _optional_money(
        raw.get("disputed_amount"), row, "disputed_amount", errors
    )
    invoice.dispute_cause = raw.get("dispute_cause", raw.get("cause"))
    resolution = raw.get("dispute_resolution", raw.get("resolution", "none"))
    if resolution not in {"none", "pending", "replace_goods", "credit_note"}:
        errors.append(ValidationError(row, "dispute_resolution", "has an unsupported value"))
    else:
        invoice.dispute_resolution = resolution
    delivered = raw.get("replacement_delivered")
    if delivered is not None and not isinstance(delivered, bool):
        errors.append(ValidationError(row, "replacement_delivered", "must be true or false"))
    elif delivered is not None:
        invoice.replacement_delivered = delivered
    credit = _optional_money(raw.get("credit_amount"), row, "credit_amount", errors)
    if credit is not None:
        invoice.credit_amount = credit
    balance_before_credit = invoice.amount - invoice.received_amount
    if invoice.disputed_amount is not None and invoice.disputed_amount > balance_before_credit:
        errors.append(ValidationError(
            row, "disputed_amount", "cannot exceed the balance before credit"
        ))
    if invoice.credit_amount > 0 and (
        invoice.disputed_amount is None or invoice.credit_amount > invoice.disputed_amount
    ):
        errors.append(ValidationError(
            row, "credit_amount", "cannot exceed disputed_amount"
        ))
    if resolution == "credit_note" and invoice.credit_amount <= 0:
        errors.append(ValidationError(
            row, "credit_amount", "is required for a credit_note"
        ))
    if resolution in {"replace_goods", "credit_note"} and not invoice.dispute_cause:
        errors.append(ValidationError(
            row, "dispute_cause", "is required for this resolution"
        ))
    if len(errors) > error_count:
        invoice.dispute_status = "open" if invoice.disputed else "none"
        invoice.disputed_amount = None
        invoice.dispute_cause = None
        invoice.dispute_resolution = "none"
        invoice.replacement_delivered = False
        invoice.credit_amount = Decimal("0.00")


def _normalize_promise(raw: dict[str, Any], invoice: Invoice, row: int | str,
                       errors: list[ValidationError]) -> None:
    error_count = len(errors)
    invoice.promise_made_date = _parse_date(
        raw.get("promise_made_date"), row, "promise_made_date", errors
    )
    invoice.promise_date = _parse_date(raw.get("promise_date"), row, "promise_date", errors)
    invoice.promise_amount = _optional_money(
        raw.get("promise_amount"), row, "promise_amount", errors
    )
    has_promise = any(
        value is not None
        for value in (invoice.promise_made_date, invoice.promise_date, invoice.promise_amount)
    )
    if has_promise:
        if invoice.promise_made_date is None or invoice.promise_date is None:
            errors.append(ValidationError(row, "promise", "promise dates are both required"))
        elif invoice.promise_date < invoice.promise_made_date:
            errors.append(ValidationError(row, "promise_date", "cannot be before promise_made_date"))
        if invoice.promise_amount is None:
            errors.append(ValidationError(row, "promise_amount", "is required when a promise exists"))
        elif invoice.promise_amount > max(
            Decimal("0.00"),
            invoice.amount - invoice.received_amount - invoice.credit_amount,
        ):
            errors.append(ValidationError(
                row, "promise_amount", "cannot exceed the collectible balance"
            ))
    if len(errors) > error_count:
        invoice.promise_made_date = None
        invoice.promise_date = None
        invoice.promise_amount = None


def _load_json(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("fixture root must be an object")
    invoices, receipts, as_of = _raw_records(payload)
    metadata = {key: value for key, value in payload.items() if key != "records"}
    return invoices, receipts, as_of, metadata


def _load_csv(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Any, dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    return rows, [], None, {"source_format": "csv"}


def load_fixture(path: str | Path) -> LoadResult:
    """Load a fixture without modifying it and return valid rows plus errors."""
    fixture_path = Path(path)
    errors: list[ValidationError] = []
    try:
        if fixture_path.suffix.lower() == ".csv":
            raw_invoices, raw_receipts, raw_as_of, metadata = _load_csv(fixture_path)
        else:
            raw_invoices, raw_receipts, raw_as_of, metadata = _load_json(fixture_path)
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors.append(ValidationError("file", "fixture", str(exc)))
        return LoadResult([], [], date.min, errors, {})

    as_of_date = _parse_date(raw_as_of, "file", "as_of_date", errors, required=True)
    if as_of_date is None:
        as_of_date = date.min

    invoices: list[Invoice] = []
    seen_ids: set[str] = set()
    for row_number, raw in enumerate(raw_invoices, 1):
        if not isinstance(raw, dict):
            errors.append(ValidationError(row_number, "row", "must be an object"))
            continue
        row_errors_before = len(errors)
        invoice_id = raw.get("invoice_id", raw.get(FIELD_MAP["invoice_id"]))
        customer = raw.get("customer", raw.get(FIELD_MAP["customer"]))
        due_date = _parse_date(
            raw.get("due_date", raw.get(FIELD_MAP["due_date"])),
            row_number, "due_date", errors, required=True,
        )
        amount = _parse_money(
            raw.get("amount", raw.get(FIELD_MAP["amount"])),
            row_number, "amount", errors, required=True, positive=True,
        )
        if not invoice_id:
            errors.append(ValidationError(row_number, "invoice_id", "value is required"))
        if not customer:
            errors.append(ValidationError(row_number, "customer", "value is required"))
        duplicate_id = bool(invoice_id) and str(invoice_id) in seen_ids
        if duplicate_id:
            errors.append(ValidationError(row_number, "invoice_id", "duplicate; later row rejected"))
        if invoice_id:
            seen_ids.add(str(invoice_id))
        invoice_date = _parse_date(raw.get("invoice_date"), row_number, "invoice_date", errors)
        if due_date and invoice_date and due_date < invoice_date:
            errors.append(ValidationError(row_number, "due_date", "cannot be before invoice_date"))
        received_key = "received_amount" if "received_amount" in raw else FIELD_MAP["received"]
        received_value = raw.get(received_key, 0)
        if received_key in raw and received_value is None:
            errors.append(ValidationError(row_number, "received_amount", "null is unknown, not zero"))
        received = _parse_money(
            received_value,
            row_number, "received_amount", errors, positive=False,
        )
        if received is not None and received < 0:
            errors.append(ValidationError(
                row_number, "received_amount", "cannot be negative"
            ))
        if received is None and received_key in raw:
            continue
        if len(errors) != row_errors_before and (
            not invoice_id or not customer or not due_date or not amount or duplicate_id
        ):
            continue
        invoice = Invoice(
            invoice_id=str(invoice_id),
            customer=str(customer),
            amount=amount,
            due_date=due_date,
            received_amount=received or Decimal("0.00"),
            invoice_date=invoice_date,
            disputed=bool(raw.get("disputed", raw.get(FIELD_MAP["disputed"], False))),
        )
        _normalize_dispute(raw, invoice, row_number, errors)
        _normalize_promise(raw, invoice, row_number, errors)
        invoices.append(invoice)

    receipts: list[Receipt] = []
    for row_number, raw in enumerate(raw_receipts, 1):
        amount = _parse_money(raw.get("amount"), f"receipt:{row_number}", "amount", errors, positive=True)
        if amount is None:
            continue
        receipt_id = str(raw.get("receipt_id", f"receipt-{row_number}"))
        invoice_id = raw.get("invoice_id") or None
        if invoice_id is not None and str(invoice_id) not in seen_ids:
            errors.append(ValidationError(f"receipt:{row_number}", "invoice_id", "unknown invoice; kept as unapplied"))
            invoice_id = None
        receipt_date = _parse_date(raw.get("receipt_date"), f"receipt:{row_number}", "receipt_date", errors)
        receipts.append(Receipt(receipt_id, str(invoice_id) if invoice_id else None,
                                raw.get("customer"), amount, receipt_date))

    return LoadResult(invoices, receipts, as_of_date, errors, metadata)
