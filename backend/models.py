from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Date, DateTime, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class InvoiceRecord(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("organization_id", "invoice_id", name="uq_org_invoice"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    invoice_id: Mapped[str] = mapped_column(String(128))
    customer: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    received_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    due_date: Mapped[date] = mapped_column(Date)
    invoice_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    disputed: Mapped[bool] = mapped_column(default=False)
    dispute_status: Mapped[str] = mapped_column(String(32), default="none")
    disputed_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    dispute_cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dispute_resolution: Mapped[str] = mapped_column(String(32), default="none")
    replacement_delivered: Mapped[bool] = mapped_column(default=False)
    credit_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    promise_made_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    promise_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    promise_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ReceiptRecord(Base):
    __tablename__ = "receipts"
    __table_args__ = (UniqueConstraint("organization_id", "receipt_id", name="uq_org_receipt"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    receipt_id: Mapped[str] = mapped_column(String(128))
    invoice_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    customer: Mapped[str | None] = mapped_column(String(255), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    receipt_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    organization_id: Mapped[str] = mapped_column(String(128), index=True)
    actor_id: Mapped[str] = mapped_column(String(255))
    actor_role: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(128), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
