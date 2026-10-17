"""LedgerLoop's single-page Streamlit workflow."""

from __future__ import annotations

import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import streamlit as st

from src.disputes import VALID_CAUSES, VALID_RESOLUTIONS, explain, validate_dispute
from src.drafts import drafts_for_customers
from src.export import (
    write_evidence_log,
    write_result_csv,
    write_result_json,
    write_starting_state,
)
from src.loader import Invoice, load_fixture
from src.rules import evaluate_all, ranked_collectable, unapplied_receipts

ROOT = Path(__file__).parent
DEFAULT_FIXTURE = ROOT / "data" / "fixture.json"
OUTPUT_DIR = ROOT / "output"


def _money(value: Decimal) -> str:
    return f"₹{value:,.2f}"


def _load_source(uploaded_file):
    if uploaded_file is None:
        return load_fixture(DEFAULT_FIXTURE), str(DEFAULT_FIXTURE)
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=Path(uploaded_file.name).suffix, delete=False
    ) as handle:
        handle.write(uploaded_file.getbuffer())
        temp_path = handle.name
    return load_fixture(temp_path), uploaded_file.name


def _initialize_state():
    if "load_result" not in st.session_state:
        result, source = _load_source(None)
        st.session_state.load_result = result
        st.session_state.source_name = source
        st.session_state.as_of_date = result.as_of_date
        st.session_state.reviewed_drafts = {}
        st.session_state.draft_text = {}
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        starting = OUTPUT_DIR / "starting_state.json"
        if not starting.exists() and result.invoices:
            write_starting_state(
                evaluate_all(result.invoices, result.receipts, result.as_of_date),
                starting,
            )


def _apply_new_source(uploaded_file):
    result, source = _load_source(uploaded_file)
    st.session_state.load_result = result
    st.session_state.source_name = source
    st.session_state.as_of_date = result.as_of_date
    st.session_state.reviewed_drafts = {}
    st.session_state.draft_text = {}


def _decimal_input(label: str, value: Decimal | None) -> Decimal | None:
    number = st.number_input(
        label,
        min_value=0.0,
        value=float(value or Decimal("0.00")),
        step=0.01,
        format="%.2f",
    )
    try:
        return Decimal(str(number)).quantize(Decimal("0.01"))
    except InvalidOperation:
        st.error(f"{label} must be a valid amount.")
        return None


def _render_invoice_detail(evaluations):
    if not evaluations:
        return
    selected_id = st.selectbox(
        "Invoice detail",
        [item.invoice_id for item in evaluations],
    )
    evaluation = next(item for item in evaluations if item.invoice_id == selected_id)
    invoice = evaluation.invoice
    st.subheader(f"{invoice.invoice_id} · {invoice.customer}")
    st.caption(explain(evaluation))
    audit = pd.DataFrame([{
        "Amount": _money(invoice.amount),
        "Receipts": _money(evaluation.applied_receipts),
        "Credit": _money(evaluation.credit_applied),
        "Outstanding": _money(evaluation.outstanding),
        "Review": _money(evaluation.review_amount),
        "Collectable": _money(evaluation.collectable_amount),
        "Promise": evaluation.promise_status,
        "State": evaluation.state,
    }])
    st.dataframe(audit, hide_index=True, use_container_width=True)

    with st.form(f"edit-{invoice.invoice_id}"):
        st.markdown("#### Dispute and promise review")
        disputed_amount = _decimal_input("Disputed amount", invoice.disputed_amount)
        cause_options = ["none", *sorted(VALID_CAUSES)]
        current_cause = invoice.dispute_cause or "none"
        cause = st.selectbox(
            "Dispute cause",
            cause_options,
            index=cause_options.index(current_cause) if current_cause in cause_options else 0,
        )
        resolution_options = sorted(VALID_RESOLUTIONS)
        resolution = st.selectbox(
            "Dispute resolution",
            resolution_options,
            index=resolution_options.index(invoice.dispute_resolution)
            if invoice.dispute_resolution in resolution_options else 0,
        )
        delivered = invoice.replacement_delivered
        if resolution == "replace_goods":
            delivered = st.checkbox("Replacement delivered", value=delivered)
        credit_amount = invoice.credit_amount
        if resolution == "credit_note":
            credit_amount = _decimal_input("Credit amount", invoice.credit_amount)
        promise_made = st.date_input(
            "Promise made date",
            value=invoice.promise_made_date,
            min_value=date(2000, 1, 1),
        )
        promise_date = st.date_input(
            "Promise date",
            value=invoice.promise_date,
            min_value=date(2000, 1, 1),
        )
        promise_amount = _decimal_input("Promise amount", invoice.promise_amount)
        save = st.form_submit_button("Save review fields")
        if save:
            candidate = Invoice(
                **{
                    **invoice.__dict__,
                    "disputed": disputed_amount is not None and disputed_amount > 0,
                    "disputed_amount": disputed_amount,
                    "dispute_cause": None if cause == "none" else cause,
                    "dispute_resolution": resolution,
                    "replacement_delivered": delivered,
                    "credit_amount": credit_amount or Decimal("0.00"),
                    "promise_made_date": promise_made,
                    "promise_date": promise_date,
                    "promise_amount": promise_amount,
                }
            )
            errors = validate_dispute(candidate, evaluation.applied_receipts)
            if errors:
                for error in errors:
                    st.error(error)
            else:
                index = next(
                    index for index, item in enumerate(st.session_state.load_result.invoices)
                    if item.invoice_id == invoice.invoice_id
                )
                st.session_state.load_result.invoices[index] = candidate
                st.success("Review fields saved. Recalculation will use the updated session state.")
                st.rerun()


def _render_drafts(evaluations):
    for draft in drafts_for_customers(evaluations):
        customer = draft["customer"]
        text_key = f"draft-{customer}"
        body = st.text_area(
            f"{draft['status']} · {customer}",
            value=st.session_state.draft_text.get(text_key, draft["body"]),
            key=text_key,
        )
        st.session_state.draft_text[text_key] = body
        st.session_state.reviewed_drafts[customer] = st.checkbox(
            "Mark reviewed",
            value=st.session_state.reviewed_drafts.get(customer, False),
            key=f"reviewed-{customer}",
        )


def main():
    st.set_page_config(page_title="LedgerLoop", layout="wide")
    _initialize_state()
    result = st.session_state.load_result

    st.title("LedgerLoop")
    st.caption(
        "Synthetic-data receivables follow-up desk. Drafts are template-generated, "
        "reviewable, and never sent."
    )
    with st.sidebar:
        st.header("Controls")
        upload = st.file_uploader("Load JSON or CSV", type=["json", "csv"])
        if st.button("Load selected file") and upload is not None:
            _apply_new_source(upload)
            st.rerun()
        as_of = st.date_input("As-of date", value=st.session_state.as_of_date)
        st.session_state.as_of_date = as_of
        customers = sorted({invoice.customer for invoice in result.invoices})
        customer_filter = st.multiselect("Customer filter", customers)

    if result.errors:
        st.warning(f"{len(result.errors)} validation error(s) found; invalid rows are excluded.")
        st.dataframe(
            pd.DataFrame([error.__dict__ for error in result.errors]),
            hide_index=True,
            use_container_width=True,
        )

    evaluations = evaluate_all(result.invoices, result.receipts, as_of)
    if customer_filter:
        evaluations = [item for item in evaluations if item.customer in customer_filter]
    ranked = ranked_collectable(evaluations)
    promised = [item for item in evaluations if item.state == "Promised"]
    review = [item for item in evaluations if item.review_amount > 0]
    not_due = [item for item in evaluations if item.state == "Not due"]
    paid = [item for item in evaluations if item.state == "Paid"]
    total_outstanding = sum((item.outstanding for item in evaluations), Decimal("0.00"))
    total_collectable = sum((item.collectable_amount for item in evaluations), Decimal("0.00"))
    total_review = sum((item.review_amount for item in evaluations), Decimal("0.00"))

    metrics = st.columns(4)
    metrics[0].metric("Outstanding", _money(total_outstanding))
    metrics[1].metric("Collectable", _money(total_collectable))
    metrics[2].metric("Under review", _money(total_review))
    metrics[3].metric("Promised", str(len(promised)))

    tabs = st.tabs([
        "Priority list", "Under review", "Promised", "Not yet due / Paid",
        "Unapplied receipts", "Draft plan", "Invoice detail",
    ])
    with tabs[0]:
        st.dataframe(pd.DataFrame([{
            "Rank": index,
            "Customer": item.customer,
            "Invoice": item.invoice_id,
            "Due date": item.invoice.due_date,
            "Days overdue": item.days_overdue,
            "Bucket": item.ageing_bucket,
            "Collectable": _money(item.collectable_amount),
            "Review": _money(item.review_amount),
            "Score": str(item.score.quantize(Decimal("0.1"))) if item.score is not None else "",
        } for index, item in enumerate(ranked, 1)]), hide_index=True, use_container_width=True)
    with tabs[1]:
        st.dataframe(pd.DataFrame([{
            "Invoice": item.invoice_id,
            "Customer": item.customer,
            "Review": _money(item.review_amount),
            "Cause": item.invoice.dispute_cause or "dispute detail missing",
            "Resolution": item.invoice.dispute_resolution,
        } for item in review]), hide_index=True, use_container_width=True)
    with tabs[2]:
        st.dataframe(pd.DataFrame([{
            "Invoice": item.invoice_id,
            "Customer": item.customer,
            "Promise date": item.invoice.promise_date,
            "Promised": _money(item.invoice.promise_amount or item.collectable_amount),
            "Received": _money(item.promised_paid),
            "Shortfall": _money(item.promise_shortfall),
        } for item in promised]), hide_index=True, use_container_width=True)
    with tabs[3]:
        st.subheader("Not yet due")
        st.dataframe(pd.DataFrame([{
            "Invoice": item.invoice_id, "Customer": item.customer,
            "Due date": item.invoice.due_date, "Outstanding": _money(item.outstanding),
        } for item in not_due]), hide_index=True, use_container_width=True)
        st.subheader("Paid")
        st.dataframe(pd.DataFrame([{
            "Invoice": item.invoice_id, "Customer": item.customer,
            "Paid amount": _money(item.invoice.amount),
        } for item in paid]), hide_index=True, use_container_width=True)
    with tabs[4]:
        unapplied = unapplied_receipts(result.receipts, as_of)
        st.dataframe(pd.DataFrame([{
            "Receipt": receipt.receipt_id, "Customer": receipt.customer,
            "Amount": _money(receipt.amount), "Date": receipt.receipt_date,
        } for receipt in unapplied]), hide_index=True, use_container_width=True)
    with tabs[5]:
        _render_drafts(evaluations)
    with tabs[6]:
        _render_invoice_detail(evaluations)

    st.divider()
    if st.button("Export results and evidence"):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        write_result_json(evaluations, OUTPUT_DIR / "result.json")
        write_result_csv(evaluations, OUTPUT_DIR / "result.csv")
        write_evidence_log(
            OUTPUT_DIR / "evidence_log.md",
            evaluations,
            fixture_name=st.session_state.source_name,
            receipt_count=len(result.receipts),
            validation_errors=result.errors,
        )
        st.success("Exported result.json, result.csv, and evidence_log.md.")
    st.caption(
        "Figures come from synthetic data. No cash recovery or production readiness "
        "is claimed. No messages are sent."
    )


if __name__ == "__main__":
    main()
