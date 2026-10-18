"""Payment recording, invoice closing, and receipt voucher generation for LedgerLoop."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from src.loader import Invoice, Receipt, MONEY_QUANTUM


PAYMENT_MODES = [
    "Bank Transfer (NEFT / RTGS / IMPS)",
    "UPI / QR Code (PhonePe, GPay, Paytm, BHIM)",
    "Cheque / Demand Draft",
    "Cash",
    "Direct Debit / ECS",
    "Payment Gateway / Card",
]


def record_payment(
    invoice: Invoice,
    receipts: list[Receipt],
    invoices: list[Invoice],
    payment_amount: Decimal,
    payment_date: date,
    payment_mode: str = "Bank Transfer (NEFT / RTGS / IMPS)",
    reference_id: str | None = None,
    note: str | None = None,
    settle_remaining: bool = False,
    resolve_dispute: bool = True,
) -> tuple[Receipt, Invoice]:
    """Record a received payment, append receipt, update invoice, and optionally close it.

    Ensures mathematical consistency:
    - If prior invoice.received_amount had no detailed Receipt rows, backfills REC-INIT.
    - Appends a new uniquely-identified Receipt.
    - Updates invoice.received_amount.
    - If settle_remaining is requested, marks settlement_agreed so remaining balance becomes credit.
    - If resolve_dispute is requested, clears active dispute.
    """
    if payment_amount <= Decimal("0.00"):
        raise ValueError("Payment amount must be greater than zero.")

    payment_amount = payment_amount.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

    # 1. Backfill initial receipt if aggregate received_amount exists without receipt rows
    has_prior_receipts = any(r.invoice_id == invoice.invoice_id for r in receipts)
    if invoice.received_amount > Decimal("0.00") and not has_prior_receipts:
        init_receipt = Receipt(
            receipt_id=f"REC-INIT-{invoice.invoice_id}",
            invoice_id=invoice.invoice_id,
            customer=invoice.customer,
            amount=invoice.received_amount,
            receipt_date=invoice.invoice_date or date(2000, 1, 1),
        )
        receipts.append(init_receipt)

    # 2. Create the new payment receipt
    receipt_seq = sum(1 for r in receipts if r.invoice_id == invoice.invoice_id) + 1
    clean_ref = reference_id.strip() if reference_id else ""
    ref_suffix = f"-{clean_ref[:8]}" if clean_ref else ""
    rec_id = f"REC-{invoice.invoice_id}-{receipt_seq}{ref_suffix}"

    new_receipt = Receipt(
        receipt_id=rec_id,
        invoice_id=invoice.invoice_id,
        customer=invoice.customer,
        amount=payment_amount,
        receipt_date=payment_date,
    )
    receipts.append(new_receipt)

    # 3. Calculate new total received amount
    current_recd = invoice.received_amount or Decimal("0.00")
    new_recd_total = (current_recd + payment_amount).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

    # 4. Prepare updated invoice attributes
    updated_attrs = dict(invoice.__dict__)
    updated_attrs["received_amount"] = new_recd_total

    # Resolve dispute if requested
    if resolve_dispute:
        updated_attrs["disputed"] = False
        updated_attrs["dispute_status"] = "resolved"
        updated_attrs["disputed_amount"] = Decimal("0.00")
        updated_attrs["dispute_resolution"] = "settled_in_finances"

    # Handle full & final settlement if remaining balance is forgiven/discounted
    if settle_remaining and new_recd_total < invoice.amount:
        updated_attrs["settlement_agreed"] = True
        updated_attrs["settlement_amount"] = new_recd_total
        settlement_desc = f"Settled via {payment_mode}"
        if clean_ref:
            settlement_desc += f" (Ref: {clean_ref})"
        if note:
            settlement_desc += f" - {note.strip()}"
        updated_attrs["settlement_note"] = settlement_desc

    # Update promise status if applicable
    if invoice.promise_date is not None:
        updated_attrs["promise_shortfall"] = Decimal("0.00")

    updated_invoice = Invoice(**updated_attrs)

    # 5. Update invoice in the invoices list
    for idx, item in enumerate(invoices):
        if item.invoice_id == invoice.invoice_id:
            invoices[idx] = updated_invoice
            break

    return new_receipt, updated_invoice


def generate_payment_voucher(
    invoice: Invoice,
    receipt: Receipt,
    payment_mode: str = "Bank Transfer",
    reference_id: str | None = None,
    note: str | None = None,
    authorized_by: str = "Finance Lead (Md Zeeshan Ali)",
    remaining_balance: Decimal = Decimal("0.00"),
) -> str:
    """Generate an official, printable payment receipt and settlement voucher."""
    border = "=" * 62
    sub_border = "-" * 62
    ref_display = reference_id.strip() if reference_id else "N/A"
    note_display = note.strip() if note else "Payment received in full and acknowledged."
    status_display = "PAID & CLOSED" if remaining_balance <= Decimal("0.00") else "PARTIALLY PAID"

    lines = [
        border,
        "              HISAABSET PAYMENT RECEIPT VOUCHER              ",
        "             Automated Accounts Receivable Engine            ",
        border,
        f"Receipt Number   : {receipt.receipt_id}",
        f"Receipt Date     : {receipt.receipt_date or date.today()}",
        f"Payment Mode     : {payment_mode}",
        f"Transaction/UTR  : {ref_display}",
        sub_border,
        f"Customer Name    : {invoice.customer}",
        f"Invoice Number   : {invoice.invoice_id}",
        f"Invoice Date     : {invoice.invoice_date or 'N/A'}",
        f"Due Date         : {invoice.due_date}",
        sub_border,
        f"Original Amount  : INR {invoice.amount:,.2f}",
        f"Amount Received  : INR {receipt.amount:,.2f}",
        f"Total Collected  : INR {invoice.received_amount:,.2f}",
        f"Remaining Balance: INR {max(Decimal('0.00'), remaining_balance):,.2f}",
        f"Account Status   : {status_display}",
        sub_border,
        f"Notes / Remarks  : {note_display}",
        f"Authorized By    : {authorized_by}",
        border,
        "   This document confirms receipt of funds into the merchant   ",
        "     bank account and updates the general ledger status.       ",
        border,
    ]
    return "\n".join(lines)

