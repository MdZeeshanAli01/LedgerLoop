"""Extract common fields from computer-generated invoice PDFs."""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from typing import Any

from .loader import ValidationError


_MONEY_PATTERN = r"(?:₹|INR|Rs\.?)\s*([\d,]+(?:\.\d{1,2})?)|([\d,]+(?:\.\d{1,2})?)"
_DATE_PATTERN = r"(\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})"
_INVOICE_ID_LABELS = (
    "Invoice Number", "Invoice No.", "Invoice No", "Invoice #",
    "Bill Number", "Bill No.", "Bill No",
)
_TOTAL_LABELS = (
    "Grand Total", "Total Amount", "Total Due", "Balance Due",
    "Amount Due", "Net Payable", "Invoice Total", "Total",
)


def extract_pdf_text(path: str | Path) -> str:
    """Return layout-preserving text from all PDF pages."""
    try:
        import pdfplumber
    except ImportError:
        pdfplumber = None
    try:
        from pypdf import PdfReader
    except ImportError:
        PdfReader = None

    if pdfplumber is None and PdfReader is None:
        raise ImportError(
            "PDF extraction requires 'pdfplumber' and 'pypdf'. Please install requirements.txt."
        )

    text = ""
    if pdfplumber is not None:
        with pdfplumber.open(str(path)) as pdf:
            text = "\n".join(
                page.extract_text(layout=True) or "" for page in pdf.pages
            ).strip()
    if text:
        return text
    if PdfReader is not None:
        reader = PdfReader(str(path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return ""


def extract_pdf_tables(path: str | Path) -> list[list[list[str | None]]]:
    """Extract detected tables for audit and future line-item processing."""
    try:
        import pdfplumber
    except ImportError:
        return []
    tables: list[list[list[str | None]]] = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if table:
                    tables.append(table)
    return tables


def _label_value(text: str, labels: tuple[str, ...], pattern: str) -> str | None:
    label_pattern = "|".join(
        sorted((re.escape(label) for label in labels), key=len, reverse=True)
    )
    # PDF text extraction frequently puts a label and value on adjacent lines.
    # Restricting the search to a short window avoids reading a number from a
    # neighbouring table column or from the invoice number itself.
    match = re.search(
        rf"(?:{label_pattern})\s*[:#-]?\s*(?:{pattern})",
        text,
        flags=re.IGNORECASE,
    )
    if match is None:
        for line in text.splitlines():
            if re.search(rf"\b(?:{label_pattern})\b", line, re.IGNORECASE):
                remainder = re.sub(
                    rf"^.*?\b(?:{label_pattern})\b\s*[:#-]?\s*",
                    "",
                    line,
                    count=1,
                    flags=re.IGNORECASE,
                )
                value_match = re.search(pattern, remainder, re.IGNORECASE)
                if value_match is not None:
                    return next((group for group in value_match.groups() if group), None)
    if match is None:
        return None
    return next((group for group in match.groups() if group), None)


def _date_value(text: str, labels: tuple[str, ...]) -> str | None:
    value = _label_value(text, labels, _DATE_PATTERN)
    if value is None:
        return None
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", value):
        day, month, year = re.split(r"[/-]", value)
        return f"{year}-{int(month):02d}-{int(day):02d}"
    return value


def _amounts(value: str) -> list[str]:
    value = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b", "", value)
    return [
        group.replace(",", "")
        for match in re.finditer(_MONEY_PATTERN, value, re.IGNORECASE)
        for group in match.groups()
        if group
    ]


def _money_value(text: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(
        sorted((re.escape(label) for label in labels), key=len, reverse=True)
    )
    candidates: list[str] = []
    preferred_candidates: list[str] = []
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.search(rf"\b(?:{label_pattern})\b", line, re.IGNORECASE):
            remainder = re.sub(
                rf"^.*?\b(?:{label_pattern})\b\s*[:#-]?\s*",
                "",
                line,
                count=1,
                flags=re.IGNORECASE,
            )
            match = re.search(_MONEY_PATTERN, remainder, re.IGNORECASE)
            if match is not None:
                values = [next(group for group in match.groups() if group)]
                candidates.extend(values)
            elif index + 1 < len(lines):
                values = _amounts("\n".join(lines[index + 1:index + 5]))
                candidates.extend(values)
            else:
                values = []
            if re.search(r"\b(?:Gross Worth|Gross Amount|Total Gross)\b", line, re.I):
                preferred_candidates.extend(values)
    if not candidates:
        value = _label_value(text, labels, _MONEY_PATTERN)
        return value.replace(",", "") if value is not None else None
    # Summary sections often print net, tax, and gross values on separate lines.
    # The last value in a labelled total block is normally the payable total.
    value = (preferred_candidates or candidates)[-1]
    return value.replace(",", "") if value is not None else None


def _customer_value(text: str) -> str | None:
    labels = ("Bill To", "Billed To", "Customer", "Buyer", "Client", "Bill To:")
    label_pattern = "|".join(re.escape(label) for label in labels)
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if re.search(r"\bSeller\s*:", line, re.IGNORECASE) and re.search(
            r"\bClient\s*:", line, re.IGNORECASE
        ):
            following = next((item for item in lines[index + 1:] if item.strip()), "")
            if following:
                columns = [part.strip() for part in re.split(r"\s{2,}", following.strip())]
                if len(columns) >= 2:
                    return columns[1]
        match = re.search(
            rf"^\s*(?:{label_pattern})\s*[:#-]?\s*(.*)$",
            line,
            flags=re.IGNORECASE,
        )
        if match:
            value = match.group(1).strip()
            if value:
                return value
            if index + 1 < len(lines) and lines[index + 1].strip():
                return lines[index + 1].strip()
    return None


def _text_value(text: str, labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(
        sorted((re.escape(label) for label in labels), key=len, reverse=True)
    )
    for line in text.splitlines():
        match = re.search(
            rf"^\s*(?:{label_pattern})\s*[:#-]?\s*(.+?)\s*$",
            line,
            flags=re.IGNORECASE,
        )
        if match and match.group(1).strip():
            value = match.group(1).strip(" \t:#-")
            if value:
                return value
    return None


def _label_block(text: str, labels: tuple[str, ...], stop_labels: tuple[str, ...]) -> str | None:
    label_pattern = "|".join(
        sorted((re.escape(label) for label in labels), key=len, reverse=True)
    )
    stop_pattern = "|".join(
        sorted((re.escape(label) for label in stop_labels), key=len, reverse=True)
    )
    lines = text.splitlines()
    for index, line in enumerate(lines):
        match = re.search(
            rf"^\s*(?:{label_pattern})\s*[:#-]?\s*(.*)$",
            line,
            flags=re.IGNORECASE,
        )
        if not match:
            continue
        values = [match.group(1).strip()] if match.group(1).strip() else []
        for following in lines[index + 1:]:
            if re.search(rf"^\s*(?:{stop_pattern})\b", following, re.IGNORECASE):
                break
            if following.strip():
                values.append(following.strip())
        return " ".join(values) or None
    return None


def _vendor_details(text: str) -> dict[str, str]:
    lines = text.splitlines()
    vendor_name = _text_value(
        text, ("Vendor Name", "Supplier Name", "Seller Name", "Supplier", "Seller")
    )
    for index, line in enumerate(lines):
        if re.search(r"\bSeller\s*:", line, re.IGNORECASE) and re.search(
            r"\bClient\s*:", line, re.IGNORECASE
        ):
            following = next((item for item in lines[index + 1:] if item.strip()), "")
            if following:
                columns = [part.strip() for part in re.split(r"\s{2,}", following.strip())]
                if columns:
                    vendor_name = columns[0]
            break
    if vendor_name is None:
        for index, line in enumerate(lines):
            if re.fullmatch(r"\s*(?:Seller|Supplier)\s*:?\s*", line, re.IGNORECASE):
                if index + 1 < len(lines) and lines[index + 1].strip():
                    vendor_name = lines[index + 1].strip()
                break
    gstin_match = re.search(
        r"\bGSTIN\s*[:#-]?\s*([A-Z0-9]{8,20})", text, re.IGNORECASE
    )
    vendor_gstin = (
        gstin_match.group(1)
        if gstin_match
        else _text_value(text, ("GST No", "GST Number", "Tax ID", "VAT Number"))
    )
    vendor_address = _label_block(
        text,
        ("Vendor Address", "Supplier Address", "Seller Address"),
        ("Tax Id", "Tax ID", "GSTIN", "GST No", "Invoice", "Client", "Customer"),
    )
    if vendor_address is None:
        vendor_lines = text.splitlines()
        for index, line in enumerate(vendor_lines):
            if re.fullmatch(r"\s*(?:Seller|Supplier)\s*:?\s*", line, re.IGNORECASE):
                values: list[str] = []
                for following in vendor_lines[index + 1:]:
                    if re.match(r"\s*(?:Tax Id|Tax ID|GSTIN|Client|Customer)\b", following, re.I):
                        break
                    if following.strip():
                        values.append(following.strip())
                if values:
                    vendor_address = " ".join(values[1:])
                break
    vendor_phone = _text_value(text, ("Vendor Phone", "Supplier Phone", "Phone", "Mobile", "Tel"))
    vendor_email = _text_value(text, ("Vendor Email", "Supplier Email", "Email", "E-mail"))
    details = {
        "vendor_name": vendor_name,
        "vendor_gstin": vendor_gstin,
        "vendor_address": vendor_address,
        "vendor_phone": vendor_phone,
        "vendor_email": vendor_email,
    }
    return {key: value for key, value in details.items() if value}


def extract_invoice_payload(
    text: str,
    *,
    as_of_date: date,
    source_name: str = "invoice.pdf",
    tables: list[list[list[str | None]]] | None = None,
) -> tuple[dict[str, Any], list[ValidationError]]:
    """Convert extracted invoice text into the existing JSON input schema."""
    errors: list[ValidationError] = []
    invoice_id = _label_value(
        text,
        _INVOICE_ID_LABELS,
        r"([A-Za-z0-9][A-Za-z0-9/_-]*)",
    )
    customer = _customer_value(text)
    amount = _money_value(
        text,
        (*_TOTAL_LABELS, "Gross Worth", "Gross Amount", "Total Gross"),
    )
    due_date = _date_value(text, ("Due Date", "Payment Due", "Due"))
    invoice_date = _date_value(text, ("Invoice Date", "Bill Date", "Date of issue"))

    fields = {
        "invoice_id": invoice_id,
        "customer": customer,
        "amount": amount,
        "due_date": due_date,
    }
    for field_name, value in fields.items():
        if value is None:
            errors.append(
                ValidationError(
                    source_name,
                    field_name,
                    "could not be extracted; review the PDF or enter it manually",
                )
            )

    invoice: dict[str, Any] = {
        "id": invoice_id or "",
        "customer": customer or "",
        "amount_inr": amount or "",
        "due": due_date or "",
        "received_inr": 0,
        "disputed": False,
    }
    if invoice_date is not None:
        invoice["invoice_date"] = invoice_date

    payload: dict[str, Any] = {
        "source_format": "pdf",
        "source_name": source_name,
        "records": {
            "as_of": as_of_date.isoformat(),
            "invoices": [invoice],
            "receipts": [],
        },
    }
    if tables:
        payload["extracted_tables"] = tables
    return payload, errors


def extract_invoice_pdf(
    path: str | Path,
    *,
    as_of_date: date,
    source_name: str | None = None,
) -> tuple[dict[str, Any], list[ValidationError]]:
    """Extract one computer-generated invoice PDF into loader-compatible JSON."""
    source_name = source_name or Path(path).name
    try:
        text = extract_pdf_text(path)
        tables = extract_pdf_tables(path)
    except (OSError, ValueError, ImportError) as exc:
        return {}, [
            ValidationError(source_name, "pdf", f"could not read PDF: {exc}")
        ]
    if not text:
        return {}, [
            ValidationError(
                source_name,
                "pdf",
                "no selectable text found; this may be a scanned image and needs OCR",
            )
        ]
    return extract_invoice_payload(
        text,
        as_of_date=as_of_date,
        source_name=source_name,
        tables=tables,
    )
