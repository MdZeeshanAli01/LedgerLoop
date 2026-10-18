from datetime import date

from src.pdf_invoice import extract_invoice_payload


def test_computer_generated_invoice_text_maps_to_existing_schema():
    payload, errors = extract_invoice_payload(
        """
        Invoice Number: INV-1001
        Invoice Date: 2026-10-01
        Due Date: 2026-10-31
        Bill To: Acme Retail
        Grand Total: INR 12,500.00
        """,
        as_of_date=date(2026, 10, 17),
    )

    assert errors == []
    invoice = payload["records"]["invoices"][0]
    assert invoice["id"] == "INV-1001"
    assert invoice["customer"] == "Acme Retail"
    assert invoice["amount_inr"] == "12500.00"
    assert invoice["due"] == "2026-10-31"
    assert "vendor_name" not in invoice
    assert "vendor_gstin" not in invoice
    assert payload["records"]["as_of"] == "2026-10-17"


def test_invoice_extraction_reports_missing_fields_for_review():
    payload, errors = extract_invoice_payload(
        "Invoice Number: INV-1002\nGrand Total: 5000",
        as_of_date=date(2026, 10, 17),
    )

    assert payload["records"]["invoices"][0]["id"] == "INV-1002"
    assert {error.field for error in errors} == {"customer", "due_date"}


def test_invoice_extraction_handles_label_value_lines_and_plain_total():
    payload, errors = extract_invoice_payload(
        """
        Invoice No.
        FY/2026/0042
        Supplier: North Star Traders
        Customer: Retail Hub
        Total
        18,750.00
        Due Date
        31/10/2026
        """,
        as_of_date=date(2026, 10, 17),
    )

    assert errors == []
    invoice = payload["records"]["invoices"][0]
    assert invoice["id"] == "FY/2026/0042"
    assert invoice["amount_inr"] == "18750.00"
    assert invoice["due"] == "2026-10-31"
    assert "vendor_name" not in invoice


def test_provided_invoice_layout_extracts_vendor_customer_gross_total_and_issue_date():
    import pytest
    pytest.importorskip("pdfplumber")
    from pathlib import Path
    from src.pdf_invoice import extract_invoice_pdf

    payload, errors = extract_invoice_pdf(
        Path("invoice_51109301.pdf"),
        as_of_date=date(2026, 10, 17),
    )

    invoice = payload["records"]["invoices"][0]
    assert invoice["id"] == "51109301"
    assert invoice["customer"] == "Raj Electronics Pvt Ltd"
    assert "vendor_gstin" not in invoice
    assert invoice["amount_inr"] == "1844673.60"
    assert invoice["invoice_date"] == "2023-07-03"
    assert any(error.field == "due_date" for error in errors)
