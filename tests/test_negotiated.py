from datetime import date, datetime
from decimal import Decimal

import pytest

from src.loader import Invoice, Receipt
from src.negotiated import (
    AgreementStatus,
    RecoveryAgreement,
    RecoveryTargetType,
    approve_agreement,
    calculate_target,
    credit_due_date,
    recovery_progress,
    validate_agreement,
)


def agreement(**overrides):
    values = {
        "agreement_id": "AGR-1",
        "retailer": "Retailer X",
        "previous_invoice_id": "INV-1",
        "actual_bep": Decimal("15000"),
        "recovery_floor": Decimal("15000"),
        "target_type": RecoveryTargetType.BEP_PLUS_AMOUNT,
        "agreed_target": Decimal("20000"),
        "agreement_date": date(2026, 10, 18),
        "note": "Negotiated recovery target.",
    }
    values.update(overrides)
    return RecoveryAgreement(**values)


def invoice():
    return Invoice("INV-1", "Retailer X", Decimal("50000"), date(2026, 9, 1))


def test_target_types_are_explicit():
    assert calculate_target(
        RecoveryTargetType.BEP_PLUS_AMOUNT, Decimal("15000"), Decimal("5000")
    ) == Decimal("20000.00")
    assert calculate_target(
        RecoveryTargetType.EXACT_BEP, Decimal("15000")
    ) == Decimal("15000.00")
    assert calculate_target(
        RecoveryTargetType.BEP_MULTIPLIER, Decimal("15000"),
        multiplier=Decimal("0.8")
    ) == Decimal("12000.00")
    assert calculate_target(
        RecoveryTargetType.CUSTOM_AMOUNT, Decimal("15000"),
        custom_amount=Decimal("18000")
    ) == Decimal("18000.00")


def test_agreement_validation_requires_reason_below_bep_and_valid_terms():
    errors = validate_agreement(agreement(agreed_target=Decimal("12000"), note=""))
    assert "below-BEP agreement requires a reason in note" in errors
    assert validate_agreement(agreement()) == []


def test_recovery_progress_handles_partial_exact_and_excess():
    agreement_value = agreement(baseline_collected=Decimal("4000"))
    receipts = [Receipt("R1", "INV-1", "Retailer X", Decimal("12000"), date(2026, 10, 1))]
    partial = recovery_progress(agreement_value, invoice(), receipts, date(2026, 10, 18))
    assert partial.status == AgreementStatus.PARTIALLY_RECOVERED
    assert partial.recovered_amount == Decimal("8000.00")
    assert partial.remaining_amount == Decimal("12000.00")
    assert partial.invoice_outstanding == Decimal("38000.00")
    assert partial.invoice_balance_after_target == Decimal("18000.00")
    exact = recovery_progress(
        agreement_value, invoice(),
        receipts + [Receipt("R2", "INV-1", "Retailer X", Decimal("12000"), date(2026, 10, 2))],
        date(2026, 10, 18),
    )
    assert exact.next_order_eligible is True
    assert exact.status == AgreementStatus.TARGET_REACHED
    excess = recovery_progress(
        agreement_value, invoice(),
        receipts + [Receipt("R2", "INV-1", "Retailer X", Decimal("14000"), date(2026, 10, 2))],
        date(2026, 10, 18),
    )
    assert excess.excess_amount == Decimal("2000.00")
    assert excess.status == AgreementStatus.TARGET_EXCEEDED


def test_approval_is_explicit_and_credit_date_is_deterministic():
    approved = approve_agreement(
        agreement(status=AgreementStatus.PENDING_APPROVAL),
        "Finance Manager",
        datetime(2026, 10, 18, 10, 30),
        "Reviewed payment history.",
    )
    assert approved.status == AgreementStatus.APPROVED
    assert credit_due_date(date(2026, 10, 18), 90) == date(2027, 1, 16)


def test_approval_requires_manager_and_note():
    with pytest.raises(ValueError):
        approve_agreement(
            agreement(), "", datetime(2026, 10, 18), ""
        )


def test_target_ignores_amount_collected_before_agreement():
    previous = Invoice(
        "INV-2", "Retailer X", Decimal("10000"), date(2026, 9, 1),
        received_amount=Decimal("4000"),
    )
    agreement_value = agreement(
        previous_invoice_id="INV-2",
        actual_bep=Decimal("2000"),
        recovery_floor=Decimal("2000"),
        target_type=RecoveryTargetType.EXACT_BEP,
        agreed_target=Decimal("2000"),
        baseline_collected=Decimal("4000"),
    )

    progress = recovery_progress(
        agreement_value, previous, [], date(2026, 10, 18)
    )

    assert progress.recovered_amount == Decimal("0.00")
    assert progress.remaining_amount == Decimal("2000.00")
    assert progress.invoice_outstanding == Decimal("6000.00")
    assert progress.invoice_balance_after_target == Decimal("4000.00")
    assert progress.next_order_eligible is False
