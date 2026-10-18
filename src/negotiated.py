"""Negotiated recovery conditions for future-order decision support."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from enum import StrEnum

from .loader import Invoice, Receipt, MONEY_QUANTUM


class RecoveryTargetType(StrEnum):
    BEP_PLUS_AMOUNT = "bep_plus_amount"
    EXACT_BEP = "exact_bep"
    BEP_MULTIPLIER = "bep_multiplier"
    CUSTOM_AMOUNT = "custom_amount"


class AgreementStatus(StrEnum):
    DRAFT = "agreement_draft"
    PENDING_APPROVAL = "pending_finance_approval"
    APPROVED = "approved"
    PARTIALLY_RECOVERED = "partially_recovered"
    TARGET_REACHED = "target_reached"
    TARGET_EXCEEDED = "target_exceeded"
    MISSED = "missed"
    CANCELLED = "cancelled"


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class RecoveryAgreement:
    agreement_id: str
    retailer: str
    previous_invoice_id: str
    actual_bep: Decimal
    recovery_floor: Decimal
    target_type: RecoveryTargetType
    agreed_target: Decimal
    upfront_percent: Decimal = Decimal("50.00")
    credit_percent: Decimal = Decimal("50.00")
    credit_period_days: int = 90
    baseline_collected: Decimal = Decimal("0.00")
    agreement_date: date | None = None
    note: str = ""
    status: AgreementStatus = AgreementStatus.DRAFT
    approved_by: str | None = None
    approved_at: datetime | None = None
    approval_note: str | None = None


@dataclass(frozen=True)
class RecoveryProgress:
    agreement: RecoveryAgreement
    recovered_amount: Decimal
    remaining_amount: Decimal
    excess_amount: Decimal
    invoice_outstanding: Decimal
    invoice_balance_after_target: Decimal
    status: AgreementStatus
    next_order_eligible: bool


def calculate_target(
    target_type: RecoveryTargetType,
    bep: Decimal,
    additional_amount: Decimal = Decimal("0.00"),
    multiplier: Decimal = Decimal("1.00"),
    custom_amount: Decimal | None = None,
) -> Decimal:
    if target_type == RecoveryTargetType.BEP_PLUS_AMOUNT:
        return _money(bep + additional_amount)
    if target_type == RecoveryTargetType.EXACT_BEP:
        return _money(bep)
    if target_type == RecoveryTargetType.BEP_MULTIPLIER:
        return _money(bep * multiplier)
    if custom_amount is None:
        raise ValueError("custom_amount is required for a custom target")
    return _money(custom_amount)


def validate_agreement(agreement: RecoveryAgreement) -> list[str]:
    errors: list[str] = []
    if not agreement.agreement_id.strip():
        errors.append("agreement_id is required")
    if not agreement.retailer.strip():
        errors.append("retailer is required")
    if not agreement.previous_invoice_id.strip():
        errors.append("previous_invoice_id is required")
    if agreement.actual_bep < 0:
        errors.append("actual_bep cannot be negative")
    if agreement.baseline_collected < 0:
        errors.append("baseline_collected cannot be negative")
    if agreement.recovery_floor < 0:
        errors.append("recovery_floor cannot be negative")
    if agreement.agreed_target < 0:
        errors.append("agreed_target cannot be negative")
    if agreement.upfront_percent < 0 or agreement.credit_percent < 0:
        errors.append("payment percentages cannot be negative")
    if agreement.upfront_percent + agreement.credit_percent != Decimal("100.00"):
        errors.append("upfront and credit percentages must total 100%")
    if agreement.credit_period_days <= 0:
        errors.append("credit_period_days must be greater than zero")
    if agreement.target_type == RecoveryTargetType.BEP_MULTIPLIER:
        if agreement.actual_bep == 0:
            errors.append("BEP multiplier requires a positive actual_bep")
        elif agreement.agreed_target <= 0:
            errors.append("BEP multiplier target must be greater than zero")
    if agreement.agreed_target < agreement.recovery_floor:
        errors.append("agreed_target cannot be below the recovery_floor")
    if agreement.agreed_target < agreement.actual_bep and not agreement.note.strip():
        errors.append("below-BEP agreement requires a reason in note")
    if agreement.status in {
        AgreementStatus.APPROVED,
        AgreementStatus.PARTIALLY_RECOVERED,
        AgreementStatus.TARGET_REACHED,
        AgreementStatus.TARGET_EXCEEDED,
    }:
        if not agreement.approved_by:
            errors.append("approved agreement requires approved_by")
        if agreement.approved_at is None:
            errors.append("approved agreement requires approved_at")
        if not agreement.approval_note:
            errors.append("approved agreement requires approval_note")
    return errors


def recovery_progress(
    agreement: RecoveryAgreement,
    invoice: Invoice,
    receipts: list[Receipt],
    as_of: date,
) -> RecoveryProgress:
    recovered = invoice.received_amount
    dated_receipts = [
        receipt.amount
        for receipt in receipts
        if receipt.invoice_id == invoice.invoice_id
        and (receipt.receipt_date is None or receipt.receipt_date <= as_of)
    ]
    if dated_receipts:
        recovered = sum(dated_receipts, Decimal("0.00"))
    recovered = _money(max(Decimal("0.00"), recovered - agreement.baseline_collected))
    remaining = _money(max(Decimal("0.00"), agreement.agreed_target - recovered))
    excess = _money(max(Decimal("0.00"), recovered - agreement.agreed_target))
    invoice_balance = _money(max(
        Decimal("0.00"), invoice.amount - recovered - agreement.baseline_collected
    ))
    balance_after_target = _money(max(
        Decimal("0.00"), invoice_balance - agreement.agreed_target
    ))
    if recovered > agreement.agreed_target:
        status = AgreementStatus.TARGET_EXCEEDED
    elif recovered == agreement.agreed_target:
        status = AgreementStatus.TARGET_REACHED
    elif recovered > 0:
        status = AgreementStatus.PARTIALLY_RECOVERED
    elif agreement.status == AgreementStatus.APPROVED:
        status = AgreementStatus.APPROVED
    else:
        status = agreement.status
    return RecoveryProgress(
        agreement, recovered, remaining, excess, invoice_balance,
        balance_after_target, status,
        status in {AgreementStatus.TARGET_REACHED, AgreementStatus.TARGET_EXCEEDED},
    )


def credit_due_date(order_date: date, credit_period_days: int) -> date:
    return order_date + timedelta(days=credit_period_days)


def approve_agreement(
    agreement: RecoveryAgreement,
    manager: str,
    approved_at: datetime,
    note: str,
) -> RecoveryAgreement:
    if not manager.strip() or not note.strip():
        raise ValueError("manager and approval note are required")
    return replace(
        agreement,
        status=AgreementStatus.APPROVED,
        approved_by=manager.strip(),
        approved_at=approved_at,
        approval_note=note.strip(),
    )
