from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceCreate(BaseModel):
    invoice_id: str = Field(min_length=1, max_length=128)
    customer: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0, max_digits=18, decimal_places=2)
    received_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)
    due_date: date
    invoice_date: date | None = None
    disputed: bool = False
    disputed_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    dispute_cause: str | None = None
    dispute_resolution: str = "none"
    replacement_delivered: bool = False
    credit_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=18, decimal_places=2)
    promise_made_date: date | None = None
    promise_date: date | None = None
    promise_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)


class InvoiceRead(InvoiceCreate):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class AuditRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    action: str
    entity_type: str
    entity_id: str | None
    actor_id: str
    actor_role: str
    created_at: datetime
