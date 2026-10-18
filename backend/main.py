from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .audit import record_event
from .auth import CurrentUser, get_current_user, require_roles
from .db import Base, engine, get_db
from .models import AuditEvent, InvoiceRecord
from .schemas import AuditRead, InvoiceCreate, InvoiceRead
from .settings import get_settings

settings = get_settings()
app = FastAPI(title="LedgerLoop API", version="1.0.0", docs_url="/docs" if settings.environment != "production" else None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.on_event("startup")
def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ledgerloop-api", "environment": settings.environment}


@app.get("/api/v1/invoices", response_model=list[InvoiceRead])
def list_invoices(
    user: CurrentUser = Depends(get_current_user),
    session: Session = Depends(get_db),
) -> list[InvoiceRecord]:
    return list(session.scalars(select(InvoiceRecord).where(
        InvoiceRecord.organization_id == user.organization_id
    ).order_by(InvoiceRecord.due_date)).all())


@app.post("/api/v1/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(
    payload: InvoiceCreate,
    user: CurrentUser = Depends(require_roles("finance_admin", "finance_manager", "collector")),
    session: Session = Depends(get_db),
) -> InvoiceRecord:
    if payload.invoice_date and payload.due_date < payload.invoice_date:
        raise HTTPException(status_code=422, detail="due_date cannot be before invoice_date")
    record = InvoiceRecord(organization_id=user.organization_id, **payload.model_dump())
    session.add(record)
    record_event(session, user, "invoice.created", "invoice", record.invoice_id)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise HTTPException(status_code=409, detail="Invoice already exists in this organization") from error
    session.refresh(record)
    return record


@app.get("/api/v1/audit-events", response_model=list[AuditRead])
def list_audit_events(
    user: CurrentUser = Depends(require_roles("finance_admin", "auditor")),
    session: Session = Depends(get_db),
) -> list[AuditEvent]:
    return list(session.scalars(select(AuditEvent).where(
        AuditEvent.organization_id == user.organization_id
    ).order_by(AuditEvent.created_at.desc()).limit(200)).all())
