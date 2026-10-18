from datetime import date
from decimal import Decimal

from src.loader import Invoice, Receipt
from src.payments import record_payment, generate_payment_voucher, PAYMENT_MODES
from src.rules import evaluate_all


def test_record_full_payment_closes_invoice():
    invoice = Invoice(
        invoice_id="INV-TEST-01",
        customer="Apex Traders",
        amount=Decimal("50000.00"),
        due_date=date(2026, 9, 30),
        received_amount=Decimal("0.00"),
    )
    receipts: list[Receipt] = []
    invoices = [invoice]

    receipt, updated_inv = record_payment(
        invoice=invoice,
        receipts=receipts,
        invoices=invoices,
        payment_amount=Decimal("50000.00"),
        payment_date=date(2026, 10, 18),
        payment_mode="Bank Transfer (NEFT / RTGS / IMPS)",
        reference_id="UTR-99887766",
        note="Full payment via NEFT",
    )

    assert receipt.amount == Decimal("50000.00")
    assert receipt.invoice_id == "INV-TEST-01"
    assert updated_inv.received_amount == Decimal("50000.00")
    assert len(receipts) == 1

    # Evaluate invoice with rules engine
    evals = evaluate_all(invoices, receipts, date(2026, 10, 18))
    evaluation = evals[0]
    assert evaluation.outstanding == Decimal("0.00")
    assert evaluation.collectable_amount == Decimal("0.00")
    assert evaluation.state == "Paid"


def test_record_partial_payment_with_settlement():
    invoice = Invoice(
        invoice_id="INV-TEST-02",
        customer="Zenith Enterprises",
        amount=Decimal("100000.00"),
        due_date=date(2026, 9, 15),
        received_amount=Decimal("20000.00"),
    )
    receipts: list[Receipt] = []
    invoices = [invoice]

    # Customer pays 70,000, and we agree to settle the remaining 10,000 as final discount
    receipt, updated_inv = record_payment(
        invoice=invoice,
        receipts=receipts,
        invoices=invoices,
        payment_amount=Decimal("70000.00"),
        payment_date=date(2026, 10, 18),
        payment_mode="UPI / QR Code (PhonePe, GPay, Paytm, BHIM)",
        reference_id="UPI-12345678",
        settle_remaining=True,
    )

    assert updated_inv.received_amount == Decimal("90000.00")
    assert updated_inv.settlement_agreed is True
    assert updated_inv.settlement_amount == Decimal("90000.00")
    # Initial 20,000 was backfilled, plus the new 70,000 receipt
    assert len(receipts) == 2

    evals = evaluate_all(invoices, receipts, date(2026, 10, 18))
    evaluation = evals[0]
    assert evaluation.applied_receipts == Decimal("90000.00")
    assert evaluation.credit_applied == Decimal("10000.00")
    assert evaluation.outstanding == Decimal("0.00")
    assert evaluation.state == "Paid"


def test_record_payment_resolves_dispute():
    invoice = Invoice(
        invoice_id="INV-TEST-03",
        customer="Royal Tech",
        amount=Decimal("80000.00"),
        due_date=date(2026, 9, 20),
        disputed=True,
        dispute_status="open",
        disputed_amount=Decimal("30000.00"),
        dispute_cause="damaged_goods",
        dispute_resolution="pending",
    )
    receipts: list[Receipt] = []
    invoices = [invoice]

    receipt, updated_inv = record_payment(
        invoice=invoice,
        receipts=receipts,
        invoices=invoices,
        payment_amount=Decimal("80000.00"),
        payment_date=date(2026, 10, 18),
        payment_mode="Cheque / Demand Draft",
        reference_id="CHQ-554433",
        resolve_dispute=True,
    )

    assert updated_inv.disputed is False
    assert updated_inv.dispute_status == "resolved"
    assert updated_inv.disputed_amount == Decimal("0.00")

    evals = evaluate_all(invoices, receipts, date(2026, 10, 18))
    evaluation = evals[0]
    assert evaluation.outstanding == Decimal("0.00")
    assert evaluation.review_amount == Decimal("0.00")
    assert evaluation.state == "Paid"


def test_payment_voucher_generation():
    invoice = Invoice(
        invoice_id="INV-1001",
        customer="Raj Electronics",
        amount=Decimal("150000.00"),
        due_date=date(2026, 10, 1),
        received_amount=Decimal("150000.00"),
    )
    receipt = Receipt(
        receipt_id="REC-INV-1001-1",
        invoice_id="INV-1001",
        customer="Raj Electronics",
        amount=Decimal("150000.00"),
        receipt_date=date(2026, 10, 18),
    )

    voucher = generate_payment_voucher(
        invoice=invoice,
        receipt=receipt,
        payment_mode="Bank Transfer (NEFT / RTGS / IMPS)",
        reference_id="UTR-77665544",
        note="Full payment received via NEFT.",
        remaining_balance=Decimal("0.00"),
    )

    assert "HISAABSET PAYMENT RECEIPT VOUCHER" in voucher
    assert "REC-INV-1001-1" in voucher
    assert "INV-1001" in voucher
    assert "INR 150,000.00" in voucher
    assert "PAID & CLOSED" in voucher
    assert "Finance Lead (Md Zeeshan Ali)" in voucher

