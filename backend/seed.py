import json
from datetime import date
from pathlib import Path

from .db import Base, SessionLocal, engine
from .models import InvoiceRecord, ReceiptRecord
from .settings import get_settings


def seed() -> None:
    settings = get_settings()
    Base.metadata.create_all(bind=engine)
    payload = json.loads(Path(settings.seed_fixture_path).read_text(encoding="utf-8"))
    records = payload.get("records", payload)
    session = SessionLocal()
    try:
        organization_id = "demo-organization"
        for row in records.get("invoices", []):
            session.merge(InvoiceRecord(
                organization_id=organization_id,
                invoice_id=str(row["id"]),
                customer=str(row["customer"]),
                amount=row["amount_inr"],
                received_amount=row.get("received_inr", 0),
                due_date=date.fromisoformat(row["due"]),
                invoice_date=(
                    date.fromisoformat(row["invoice_date"])
                    if row.get("invoice_date") else None
                ),
                disputed=bool(row.get("disputed", False)),
                dispute_resolution="pending" if row.get("disputed") else "none",
            ))
        for index, row in enumerate(records.get("receipts", []), start=1):
            session.merge(ReceiptRecord(
                organization_id=organization_id,
                receipt_id=str(row.get("receipt_id", f"receipt-{index}")),
                invoice_id=row.get("invoice_id"),
                customer=row.get("customer"),
                amount=row["amount"],
                receipt_date=(
                    date.fromisoformat(row["receipt_date"])
                    if row.get("receipt_date") else None
                ),
            ))
        session.commit()
    finally:
        session.close()


if __name__ == "__main__":
    seed()
