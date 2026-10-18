"""LedgerLoop's single-page Streamlit workflow."""

from __future__ import annotations

import os
import tempfile
import json
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pandas as pd
import streamlit as st

from src.auth import User, FINANCE_LEAD, authenticate_user
from src.disputes import VALID_CAUSES, VALID_RESOLUTIONS, explain, validate_dispute
from src.drafts import drafts_for_customers
from src.communications import send_via_ses, valid_email
from src.export import (
    write_evidence_log,
    write_result_csv,
    write_result_json,
    write_starting_state,
    write_negotiated_json,
)
from src.loader import Invoice, LoadResult, load_fixture
from src.pdf_invoice import extract_invoice_pdf
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
from src.retailer import credit_recommendation, retailer_history, retailer_risk
from src.rules import evaluate_all, ranked_collectable, unapplied_receipts

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "data" / "fixture.json"
OUTPUT_DIR = ROOT / "output"


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
        :root { --ll-bg:#eef4f3; --ll-card:#ffffff; --ll-surface:#f4f8f7; --ll-text:#173b3b;
          --ll-muted:#557070; --ll-border:#c9dcda; --ll-blue:#087f72; --ll-red-bg:#fff0ed;
          --ll-red:#991b1b; --ll-amber-bg:#fef3c7; --ll-amber:#92400e; --ll-purple-bg:#ede9fe;
          --ll-purple:#5b21b6; --ll-green-bg:#d8f4e8; --ll-green:#065f46; --ll-grey:#e4efed; }
        html, body, [class*="css"] { font-family:'Plus Jakarta Sans',sans-serif; }
        .stApp, .stApp p, .stApp label, .stApp span, .stApp h1, .stApp h2,
        .stApp h3, .stApp h4, .stApp [data-testid="stMarkdownContainer"] {
          color:var(--ll-text); }
        .stApp { background:
          radial-gradient(circle at 92% 4%, rgba(50,180,154,.20) 0, transparent 25%),
          radial-gradient(circle at 5% 85%, rgba(31,100,124,.08) 0, transparent 28%),
          linear-gradient(135deg,#edf5f4 0%,#f7faf9 42%,#edf5f4 100%);
          color:var(--ll-text); }
        .main .block-container { max-width:1500px; padding-top:2rem; padding-bottom:5rem; }
        [data-testid="stSidebar"], [data-testid="stSidebar"] * {
          background-color:#f9fcfb; color:var(--ll-text) !important; }
        [data-testid="stSidebar"] { border-right:1px solid var(--ll-border); }
        [data-testid="stSidebar"] [role="radiogroup"] label {
          border-radius:14px; padding:13px 10px; font-size:16px; font-weight:700;
          border:1px solid transparent; transition:all .2s ease; }
        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
          background:#e2f2ef; border-color:#b8ddd7; transform:translateX(2px); }
        [data-testid="stSidebar"] input, [data-testid="stSidebar"] textarea,
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
          background:#fff !important; color:var(--ll-text) !important; border-color:var(--ll-border) !important; }
        [data-testid="stSidebar"] .stButton > button {
          background:#2563eb !important; color:#fff !important; border:0 !important;
          box-shadow:none !important; }
        [data-testid="stSidebar"] .stButton > button *,
        [data-testid="stSidebar"] .stButton > button p {
          color:#fff !important; background:transparent !important; }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] button {
          background:#fff !important; color:#0f172a !important; border:1px solid #94a3b8 !important; }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] button * {
          color:#0f172a !important; background:transparent !important; }
        .ll-brand { display:flex; align-items:center; gap:11px; margin:4px 0 4px; }
        .ll-logo { width:42px; height:42px; display:grid; place-items:center; border-radius:14px;
          background:linear-gradient(135deg,#087f72,#39b79b); color:#fff; font-size:23px; font-weight:800;
          box-shadow:0 7px 16px rgba(8,127,114,.2); }
        .ll-brand-name { font-size:23px; font-weight:800; color:var(--ll-text); }
        .ll-brand-tagline { color:#087f72; font-size:11px; font-weight:800; margin:0 0 20px 53px;
          letter-spacing:.01em; }
        .ll-side-hint { background:#e8f5f1; border:1px solid #c7e4de; border-radius:14px;
          padding:12px 13px; color:#386563 !important; font-size:12px; line-height:1.5;
          margin:0 0 18px; }
        .ll-eyebrow { color:var(--ll-muted); font-size:12px; font-weight:700; letter-spacing:.08em; }
        .ll-title { color:var(--ll-text); font-size:32px; font-weight:800; margin:0; letter-spacing:-.02em; }
        .ll-subtitle { color:var(--ll-muted) !important; font-size:16px; margin-top:4px; }
        .ll-help { background:linear-gradient(110deg,rgba(223,245,239,.96),rgba(238,249,246,.86)); border:1px solid #abdcd3;
          border-radius:18px; padding:18px 20px; color:#155e59 !important; font-size:16px; font-weight:600;
          margin:18px 0; box-shadow:0 8px 22px rgba(23,59,59,.06); }
        .ll-welcome { display:flex; align-items:center; justify-content:space-between; gap:18px;
          background:linear-gradient(110deg,#087f72,#30a98e); border-radius:22px; padding:22px 26px;
          color:#fff !important; margin:8px 0 22px; box-shadow:0 12px 28px rgba(8,127,114,.18); }
        .ll-welcome * { color:#fff !important; }
        .ll-welcome-title { font-size:24px; font-weight:800; margin-bottom:3px; }
        .ll-welcome-copy { font-size:14px; opacity:.92; }
        .ll-welcome-icon { font-size:42px; opacity:.9; }
        .ll-note { background:var(--ll-surface); border:1px solid var(--ll-border); border-radius:12px;
          padding:12px; color:var(--ll-muted); font-size:13px; }
        .ll-pill { display:inline-block; border-radius:999px; padding:5px 10px; font-size:12px; font-weight:700; }
        .ll-paid { background:var(--ll-green-bg); color:var(--ll-green); }
        .ll-review { background:var(--ll-amber-bg); color:var(--ll-amber); }
        .ll-promised { background:var(--ll-purple-bg); color:var(--ll-purple); }
        .ll-overdue { background:var(--ll-red-bg); color:var(--ll-red); }
        .ll-notdue { background:var(--ll-grey); color:#334155; }
        [data-testid="stMetric"] { background:rgba(255,255,255,.9); border:1px solid var(--ll-border);
          border-radius:18px; padding:18px; box-shadow:0 7px 18px rgba(23,59,59,.06);
          border-top:4px solid #38a994; }
        [data-testid="stMetricValue"] { color:var(--ll-text) !important; font-weight:800;
          font-size:clamp(20px, 2.4vw, 30px); white-space:nowrap; }
        [data-testid="stMetricLabel"] { color:var(--ll-muted) !important; font-size:14px; font-weight:700; }
        .stButton > button { border-radius:12px; font-weight:700; min-height:46px;
          background:#087f72 !important; color:#fff !important; border:0; box-shadow:0 5px 12px rgba(8,127,114,.16); }
        .stButton > button p { color:#fff !important; }
        [data-testid="stFormSubmitButton"] button {
          border-radius:12px !important; font-weight:800 !important; min-height:48px !important;
          background:#087f72 !important; color:#fff !important; border:0 !important;
          box-shadow:none !important; }
        [data-testid="stFormSubmitButton"] button *,
        [data-testid="stFormSubmitButton"] button p {
          color:#fff !important; background:transparent !important; }
        .stTabs [role="tab"] { color:var(--ll-muted) !important; font-size:14px; font-weight:700;
          padding:10px 13px; border-radius:10px 10px 0 0; }
        .stTabs [role="tab"][aria-selected="true"] { color:#087f72 !important; background:#dff5ef; }
        [data-testid="stRadio"] > label { display:none; }
        [data-testid="stRadio"] { margin:0 0 27px; }
        [data-testid="stRadio"] [role="radiogroup"] {
          display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:8px; padding:7px;
          margin:0; background:rgba(255,255,255,.72); border:1px solid #c9dfdb;
          border-radius:19px; box-shadow:0 12px 28px rgba(23,59,59,.08);
          backdrop-filter:blur(14px);
        }
        [data-testid="stRadio"] [role="radiogroup"] label {
          min-height:54px; justify-content:center; border:1px solid transparent; border-radius:13px;
          padding:10px 14px; color:#64817d !important; font-size:13px; font-weight:800;
          line-height:1.2; transition:all .22s cubic-bezier(.22,1,.36,1);
        }
        [data-testid="stRadio"] [role="radiogroup"] label:hover {
          color:#087f72 !important; border-color:#b8ded7; background:#effaf7;
          transform:translateY(-2px); box-shadow:0 5px 12px rgba(8,127,114,.08);
        }
        [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) {
          border-color:#0a9180; color:#fff !important;
          background:linear-gradient(135deg,#087f72,#109985);
          box-shadow:0 8px 18px rgba(8,127,114,.24);
          transform:translateY(-1px);
        }
        [data-testid="stRadio"] [role="radiogroup"] label:has(input:checked) * { color:#fff !important; }
        [data-testid="stRadio"] [role="radiogroup"] label > div:first-child {
          width:0; min-width:0; margin:0; overflow:hidden; opacity:0;
        }
        [data-testid="stHeader"] { background:#eef4f3 !important; }
        [data-testid="stToolbar"] { background:transparent !important; }
        [data-testid="stDecoration"] { background:#087f72 !important; height:3px !important; }
        [data-testid="stDataFrame"] {
          border:1px solid var(--ll-border); border-radius:16px; overflow:visible;
          box-shadow:0 7px 18px rgba(23,59,59,.06);
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] {
          background:#fff !important; border:1px solid var(--ll-border) !important;
          border-radius:10px !important; box-shadow:0 4px 14px rgba(15,23,42,.16) !important;
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button {
          background:#fff !important; color:var(--ll-text) !important;
          border:0 !important; min-height:32px !important; min-width:32px !important;
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button:hover {
          background:#e2e8f0 !important;
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button[aria-label="Show/hide columns"]::after {
          content:"Columns"; font-size:12px; font-weight:700; color:var(--ll-text);
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button[aria-label="Download as CSV"]::after {
          content:"Download"; font-size:12px; font-weight:700; color:var(--ll-text);
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button[aria-label="Search"]::after {
          content:"Search"; font-size:12px; font-weight:700; color:var(--ll-text);
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button[aria-label="Fullscreen"]::after {
          content:"Full screen"; font-size:12px; font-weight:700; color:var(--ll-text);
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button[aria-label] {
          width:auto !important; padding:4px 8px !important; gap:4px !important;
        }
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] button *,
        [data-testid="stDataFrame"] [data-testid="stElementToolbar"] svg {
          color:var(--ll-text) !important; fill:var(--ll-text) !important;
          stroke:var(--ll-text) !important; opacity:1 !important;
        }
        input, textarea, [data-baseweb="select"] > div, [data-baseweb="input"] > div {
          color:var(--ll-text) !important; background:#fff !important; }
        [data-testid="stFileUploader"] section { background:#fff !important; border:2px dashed #94a3b8; }
        [data-testid="stFileUploader"] section * { color:var(--ll-text) !important; }
        .stAlert p { color:var(--ll-text) !important; }
        /* Motion system: calm, finance-native movement without changing workflow semantics. */
        html { scroll-behavior:smooth; }
        .stApp { overflow-x:hidden; }
        .stApp > header { backdrop-filter:blur(14px); }
        .block-container { animation:ll-page-in .65s cubic-bezier(.22,1,.36,1) both; }
        @keyframes ll-page-in { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:none; } }
        .ll-welcome { position:relative; overflow:hidden; isolation:isolate;
          background:linear-gradient(115deg,#073b43 0%,#087f72 54%,#2eae94 100%);
          min-height:180px; animation:ll-rise .75s cubic-bezier(.22,1,.36,1) both; }
        @keyframes ll-rise { from { opacity:0; transform:translateY(22px) scale(.985); } to { opacity:1; transform:none; } }
        .ll-welcome:before, .ll-welcome:after { content:""; position:absolute; z-index:-1;
          border:1px solid rgba(255,255,255,.18); border-radius:50%; pointer-events:none; }
        .ll-welcome:before { width:360px; height:360px; right:-72px; top:-102px;
          box-shadow:0 0 0 24px rgba(255,255,255,.035),0 0 0 48px rgba(255,255,255,.025);
          animation:ll-orbit 18s linear infinite; }
        .ll-welcome:after { width:145px; height:145px; right:72px; top:20px;
          background:radial-gradient(circle at 35% 30%,#c9fff2 0 2px,transparent 3px),
          radial-gradient(circle at 65% 66%,#b5f5e7 0 1px,transparent 2px),
          radial-gradient(circle at 20% 75%,#b5f5e7 0 1px,transparent 2px);
          box-shadow:0 0 32px rgba(170,255,231,.22); animation:ll-float 5s ease-in-out infinite; }
        @keyframes ll-orbit { to { transform:rotate(360deg); } }
        @keyframes ll-float { 0%,100% { transform:translateY(0) scale(1); } 50% { transform:translateY(-10px) scale(1.04); } }
        .ll-welcome-title, .ll-welcome-copy { animation:ll-copy-in .8s .12s cubic-bezier(.22,1,.36,1) both; }
        .ll-welcome-copy { animation-delay:.2s; }
        @keyframes ll-copy-in { from { opacity:0; transform:translateY(10px); } to { opacity:.92; transform:none; } }
        .ll-welcome-icon { position:relative; z-index:1; text-shadow:0 0 28px rgba(221,255,247,.35); animation:ll-icon-in 1s .18s cubic-bezier(.22,1,.36,1) both; }
        @keyframes ll-icon-in { from { opacity:0; transform:translateX(22px) rotate(-12deg); } to { opacity:.9; transform:none; } }
        .ll-eyebrow { animation:ll-fade-up .55s .04s both; }
        .ll-title { animation:ll-fade-up .65s .1s both; }
        .ll-subtitle { animation:ll-fade-up .65s .16s both; }
        @keyframes ll-fade-up { from { opacity:0; transform:translateY(8px); } to { opacity:1; transform:none; } }
        [data-testid="stMetric"] { position:relative; overflow:hidden; transition:transform .25s ease, box-shadow .25s ease, border-color .25s ease;
          animation:ll-card-in .65s cubic-bezier(.22,1,.36,1) both; }
        [data-testid="stMetric"]:after { content:""; position:absolute; right:-22px; bottom:-36px; width:100px; height:100px;
          border:1px solid rgba(8,127,114,.10); border-radius:50%; pointer-events:none; }
        [data-testid="stMetric"]:hover { transform:translateY(-5px); border-color:#78cdbd;
          box-shadow:0 14px 28px rgba(23,59,59,.12); }
        [data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(2) { animation-delay:.06s; }
        [data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(3) { animation-delay:.12s; }
        [data-testid="stHorizontalBlock"] [data-testid="stMetric"]:nth-child(4) { animation-delay:.18s; }
        @keyframes ll-card-in { from { opacity:0; transform:translateY(15px); } to { opacity:1; transform:none; } }
        .stTabs [role="tab"] { transition:color .2s ease, background .2s ease, transform .2s ease; }
        .stTabs [role="tab"]:hover { transform:translateY(-2px); }
        [data-testid="stDataFrame"] { animation:ll-table-in .7s .12s both; transition:box-shadow .25s ease, transform .25s ease; }
        [data-testid="stDataFrame"]:hover { box-shadow:0 13px 28px rgba(23,59,59,.1); transform:translateY(-2px); }
        [data-testid="stExpander"] { transition:border-color .2s ease, box-shadow .2s ease; }
        [data-testid="stExpander"]:hover { border-color:#8fd2c4; box-shadow:0 8px 20px rgba(23,59,59,.06); }
        @keyframes ll-table-in { from { opacity:0; transform:translateY(12px); } to { opacity:1; transform:none; } }
        .ll-loader { position:fixed; z-index:99999; inset:0; display:flex; align-items:center; justify-content:center;
          min-height:100vh; margin:0; overflow:hidden; border-radius:0; color:#e5fff8;
          background:radial-gradient(circle at 50% 45%,#124b57 0,#092d3b 42%,#061d2c 100%);
          animation:ll-loader-out .9s 1.35s cubic-bezier(.76,0,.24,1) forwards; }
        .ll-loader:before, .ll-loader:after { content:""; position:absolute; border:1px solid rgba(103,225,197,.18);
          border-radius:50%; pointer-events:none; }
        .ll-loader:before { width:52vw; height:52vw; animation:ll-loader-orbit 12s linear infinite; }
        .ll-loader:after { width:24vw; height:24vw; animation:ll-loader-orbit 7s linear infinite reverse; }
        .ll-loader-number { font:800 44px/1 'Plus Jakarta Sans',sans-serif; letter-spacing:-.08em;
          animation:ll-counter-glow 1.05s ease-out forwards; }
        .ll-loader-label { position:absolute; bottom:15px; color:#80b9ae; font-size:9px;
          font-weight:800; letter-spacing:.18em; }
        .ll-loader-bar { position:absolute; right:14%; bottom:13px; left:14%; height:2px; overflow:hidden; background:#1b5360; }
        .ll-loader-bar:after { content:""; display:block; width:100%; height:100%; background:#4dd0ae;
          transform:scaleX(0); transform-origin:left; animation:ll-load-bar 1.05s ease-out forwards; }
        @keyframes ll-load-bar { to { transform:scaleX(1); } }
        @keyframes ll-counter-glow { 0% { opacity:.25; transform:scale(.96); } 75% { opacity:1; transform:scale(1.04); } 100% { opacity:1; transform:scale(1); } }
        @keyframes ll-loader-orbit { to { transform:rotate(360deg) translateX(18px) rotate(-360deg); } }
        @keyframes ll-loader-out { to { opacity:0; visibility:hidden; transform:translateY(-100%); pointer-events:none; } }
        @media (prefers-reduced-motion:reduce) {
          *, *:before, *:after { animation-duration:.01ms !important; animation-iteration-count:1 !important;
            scroll-behavior:auto !important; transition-duration:.01ms !important; }
        }
        @media (max-width:800px) { .ll-title { font-size:24px; } .ll-welcome:before { right:-180px; }
          .ll-welcome:after { right:24px; opacity:.65; } .ll-loader-number { font-size:34px; } }
        /* Premium control surfaces */
        .stTextInput, .stNumberInput, .stDateInput, .stSelectbox, .stMultiSelect,
        .stTextArea, .stFileUploader, .stCheckbox { animation:ll-control-in .5s both; }
        @keyframes ll-control-in { from { opacity:0; transform:translateY(5px); } to { opacity:1; transform:none; } }
        .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {
          border-radius:11px !important; border:1px solid #d8e7e4 !important;
          box-shadow:0 3px 10px rgba(23,59,59,.025) !important; transition:border-color .2s, box-shadow .2s, transform .2s !important; }
        .stTextInput input:focus, .stNumberInput input:focus, .stDateInput input:focus, .stTextArea textarea:focus {
          border-color:#51bda8 !important; box-shadow:0 0 0 4px rgba(81,189,168,.12) !important; transform:translateY(-1px); }
        [data-baseweb="select"] > div { border-radius:11px !important; border-color:#d8e7e4 !important;
          box-shadow:0 3px 10px rgba(23,59,59,.025) !important; }
        .stButton > button, [data-testid="stFormSubmitButton"] button {
          position:relative; overflow:hidden; transition:transform .2s ease, box-shadow .2s ease, filter .2s ease !important; }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] button:hover {
          transform:translateY(-2px); filter:saturate(1.08); box-shadow:0 9px 20px rgba(8,127,114,.22) !important; }
        .stButton > button:active, [data-testid="stFormSubmitButton"] button:active { transform:translateY(0); }
        [data-testid="stSidebar"] { box-shadow:8px 0 30px rgba(23,59,59,.04); }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section { min-height:124px; border-radius:16px !important;
          border:1px dashed #82aba9 !important; background:rgba(255,255,255,.7) !important;
          transition:transform .2s ease, border-color .2s ease, background .2s ease; }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section:hover { transform:translateY(-2px);
          border-color:#42ad99 !important; background:#f0fbf8 !important; }
        [data-testid="stSidebar"] [data-testid="stFileUploader"] section small {
          color:#79928f !important; font-size:10px !important; }
        [data-testid="stSidebar"] .stButton > button {
          min-height:43px !important; border-radius:11px !important;
          background:linear-gradient(135deg,#1769e8,#2b7df0) !important;
          box-shadow:0 7px 15px rgba(37,99,235,.18) !important; }
        [data-testid="stSidebar"] .stDateInput input {
          min-height:43px !important; border-radius:12px !important; padding-left:13px !important;
          background:rgba(255,255,255,.82) !important; }
        [data-testid="stSidebar"] [data-baseweb="select"] > div {
          min-height:43px !important; border-radius:12px !important;
          background:rgba(255,255,255,.82) !important; }
        .stMarkdown h2, .stMarkdown h3 { letter-spacing:-.025em; }
        .stCaption { color:#75908e !important; }
        .stAlert { border-radius:13px !important; box-shadow:0 5px 15px rgba(23,59,59,.045); }
        /* LedgerLoop command-center redesign */
        .ll-command-header { position:relative; display:flex; align-items:flex-end; justify-content:space-between;
          gap:28px; min-height:170px; margin:0 0 25px; padding:28px 30px; overflow:hidden;
          border:1px solid rgba(145,210,199,.35); border-radius:25px;
          color:#effffb; background:linear-gradient(120deg,#071f30 0%,#0b3b49 52%,#087f72 100%);
          box-shadow:0 18px 42px rgba(8,63,76,.17); }
        .ll-command-header:before { content:""; position:absolute; inset:-90px -40px auto auto; width:300px; height:300px;
          border:1px solid rgba(151,255,226,.22); border-radius:50%;
          box-shadow:0 0 0 23px rgba(151,255,226,.035),0 0 0 47px rgba(151,255,226,.025);
          animation:ll-command-spin 22s linear infinite; }
        .ll-command-header:after { content:""; position:absolute; right:28px; bottom:24px; width:190px; height:90px;
          background:radial-gradient(circle at 18% 35%,#baffef 0 1px,transparent 2px),
          radial-gradient(circle at 42% 68%,#94dfd0 0 1px,transparent 2px),
          radial-gradient(circle at 68% 25%,#dbfff7 0 1px,transparent 2px),
          radial-gradient(circle at 88% 78%,#8ed9c9 0 1px,transparent 2px); opacity:.7; }
        @keyframes ll-command-spin { to { transform:rotate(360deg); } }
        .ll-command-copy { position:relative; z-index:1; max-width:620px; }
        .ll-command-kicker { margin:0 0 10px; color:#75d9c1; font-size:10px; font-weight:800; letter-spacing:.18em; }
        .ll-command-title { margin:0; color:#fff; font:800 clamp(24px,3vw,38px)/1.05 'Plus Jakarta Sans',sans-serif; letter-spacing:-.055em; }
        .ll-command-subtitle { margin:10px 0 0; color:#b8d9d7; font-size:13px; line-height:1.55; }
        .ll-command-status { position:relative; z-index:1; display:flex; flex-direction:column; gap:9px; min-width:210px;
          padding:15px 16px; border:1px solid rgba(188,255,239,.18); border-radius:16px;
          background:rgba(255,255,255,.08); backdrop-filter:blur(12px); }
        .ll-status-line { display:flex; align-items:center; gap:8px; color:#d9fff6; font-size:11px; font-weight:700; }
        .ll-status-line i { width:8px; height:8px; border-radius:50%; background:#54e0b8; box-shadow:0 0 0 5px rgba(84,224,184,.14); }
        .ll-status-meta { color:#9bc5c2; font-size:10px; }
        .ll-section-bar { display:flex; align-items:center; justify-content:space-between; gap:12px; margin:6px 0 18px; }
        .ll-section-bar .ll-eyebrow { margin:0; }
        .ll-section-bar .ll-rule { flex:1; height:1px; background:linear-gradient(90deg,#c3ded9,transparent); }
        .ll-source-chip { display:inline-flex; align-items:center; gap:6px; padding:7px 10px; border:1px solid #cbe2de;
          border-radius:999px; color:#4d7773; background:rgba(255,255,255,.72); font-size:10px; font-weight:700; }
        .ll-source-chip i { width:6px; height:6px; border-radius:50%; background:#22a789; }
        .ll-command-header + .ll-title { margin-top:4px; }
        .stRadio [role="radiogroup"] { backdrop-filter:blur(12px); }
        [data-testid="stMetric"] { background:linear-gradient(145deg,rgba(255,255,255,.96),rgba(246,251,249,.9)); }
        [data-testid="stMetric"]:first-child { border-top-color:#173953; }
        [data-testid="stMetric"]:nth-child(2) { border-top-color:#1ca587; }
        [data-testid="stMetric"]:nth-child(3) { border-top-color:#e0a62d; }
        [data-testid="stMetric"]:nth-child(4) { border-top-color:#6958a8; }
        [data-testid="stSidebar"] { background:
          radial-gradient(circle at 12% 0%,rgba(100,211,190,.14),transparent 30%),
          linear-gradient(180deg,#fbfefd 0%,#f0f8f6 100%) !important;
          box-shadow:10px 0 32px rgba(23,59,59,.07); }
        [data-testid="stSidebar"] [data-testid="stVerticalBlock"] { gap:.55rem; }
        [data-testid="stSidebar"] .block-container { padding:2rem 1.55rem 2.5rem; }
        [data-testid="stSidebar"] hr { margin:17px 0 19px !important; border-color:#cfe3df !important; }
        [data-testid="stSidebar"] .stSubheader, [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 { margin-top:8px !important; margin-bottom:7px !important; }
        [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color:#173b3b !important; letter-spacing:-.03em; }
        .ll-footer-note { display:flex; align-items:center; justify-content:center; gap:8px; margin:28px 0 0;
          padding:13px 16px; border-top:1px solid #d6e8e3; color:#698783; font-size:10px; text-align:center; }
        .ll-footer-note b { color:#2d665d; }
        .ll-login-shell { max-width:560px; margin:3.5rem auto 0; }
        .ll-login-brand { text-align:center; padding:0 0 1.4rem; }
        .ll-login-logo { width:72px; height:72px; display:grid; place-items:center; margin:0 auto 14px;
          border-radius:24px; background:linear-gradient(145deg,#087f72,#39b79b); color:#fff;
          font-size:36px; font-weight:800; box-shadow:0 16px 28px rgba(8,127,114,.24); }
        .ll-login-name { color:#173b3b; font-size:39px; font-weight:800; letter-spacing:-.05em; line-height:1; }
        .ll-login-tag { color:#087f72; font-size:11px; font-weight:800; letter-spacing:.13em; margin-top:12px; }
        .ll-login-copy { color:#64817d; font-size:13px; margin-top:10px; }
        .ll-login-kicker { display:flex; align-items:center; justify-content:center; gap:8px; margin:0 0 12px;
          color:#087f72; font-size:10px; font-weight:800; letter-spacing:.1em; text-transform:uppercase; }
        .ll-login-kicker:before, .ll-login-kicker:after { content:""; width:34px; height:1px; background:#b9d9d3; }
        [data-testid="stForm"] { border-radius:22px !important; border:1px solid #c9dfdb !important;
          background:rgba(255,255,255,.82) !important; box-shadow:0 18px 42px rgba(23,59,59,.09) !important;
          padding:24px !important; }
        [data-testid="stForm"] h4 { margin-top:0 !important; font-size:20px !important; letter-spacing:-.03em; }
        .ll-login-demo { margin-top:18px; padding:14px 16px; border:1px solid #d6e8e3; border-radius:16px;
          background:rgba(246,251,249,.88); color:#557070; font-size:11px; line-height:1.55; text-align:left; }
        .ll-login-demo b { color:#2d665d; }
        .ll-login-trust { display:flex; justify-content:center; gap:18px; flex-wrap:wrap; margin-top:18px;
          color:#789090; font-size:10px; font-weight:700; }
        .ll-login-trust span { display:inline-flex; align-items:center; gap:5px; }
        .ll-login-trust i { width:6px; height:6px; border-radius:50%; background:#20a786; }
        @media (max-width:800px) {
          .ll-login-shell { margin:1.5rem auto 0; }
          .ll-login-name { font-size:32px; }
          [data-testid="stForm"] { padding:18px !important; }
        }
        @media (max-width:800px) {
          [data-testid="stRadio"] [role="radiogroup"] { gap:4px; padding:5px; }
          [data-testid="stRadio"] [role="radiogroup"] label { min-height:48px; padding:8px 6px; font-size:11px; }
          .ll-command-header { display:block; min-height:205px; padding:22px; }
          .ll-command-status { min-width:0; width:max-content; max-width:100%; margin-top:18px; }
          .ll-command-header:after { right:18px; top:30px; opacity:.5; }
          .ll-footer-note { display:block; line-height:1.6; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_session_loader() -> None:
    """Show a short branded handoff animation once per Streamlit session."""
    if st.session_state.get("_ll_motion_loader_seen"):
        return
    st.session_state["_ll_motion_loader_seen"] = True
    st.markdown(
        '<div class="ll-loader" aria-label="Loading Hisaabset">'
        '<div class="ll-loader-number">000</div>'
        '<div class="ll-loader-label">CLEARING YOUR RECEIVABLES VIEW</div>'
        '<div class="ll-loader-bar"></div></div>',
        unsafe_allow_html=True,
    )


def _render_command_header(navigation: str, result: LoadResult) -> None:
    """Render the premium product shell while keeping Streamlit controls native."""
    page = {
        "＋ Add new bill": ("Build a clearer receivables picture", "Add a bill, import a source, and let the workflow surface the next safe action."),
        "▤ Your bills": ("Your receivables, in focus", "A calm, ranked view of what is collectible, protected, promised, or complete."),
        "♟ Customers": ("Know every account before you chase", "Evidence first: payment behavior, exposure, terms, and negotiated recovery in one place."),
    }[navigation]
    source_name = Path(st.session_state.get("source_name", "fixture")).name
    issue_text = f"{len(result.errors)} validation issue(s)" if result.errors else "Source validated"
    st.markdown(
        f'<div class="ll-command-header">'
        f'<div class="ll-command-copy">'
        f'<div class="ll-command-kicker">HISAABSET · RECEIVABLES COMMAND CENTER</div>'
        f'<div class="ll-command-title">{page[0]}</div>'
        f'<div class="ll-command-subtitle">{page[1]}</div>'
        f'</div>'
        f'<div class="ll-command-status">'
        f'<div class="ll-status-line"><i></i>Decision workspace ready</div>'
        f'<div class="ll-status-meta">{issue_text} · {len(result.invoices)} invoice(s) loaded</div>'
        f'<div class="ll-source-chip"><i></i>{source_name}</div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )


def _state_pill(state: str) -> str:
    classes = {"Paid":"ll-paid", "Under Review":"ll-review", "Promised":"ll-promised",
               "Collectable":"ll-overdue", "Not due":"ll-notdue"}
    return f'<span class="ll-pill {classes.get(state, "ll-notdue")}">{state}</span>'


def _money(value: Decimal) -> str:
    return f"₹{value:,.2f}"


def _load_source(
    uploaded_file,
    manual_due_date: date | None = None,
    manual_received_amount: Decimal = Decimal("0.00"),
):
    if uploaded_file is None:
        return load_fixture(DEFAULT_FIXTURE), str(DEFAULT_FIXTURE)
    with tempfile.NamedTemporaryFile(
        mode="wb", suffix=Path(uploaded_file.name).suffix, delete=False
    ) as handle:
        handle.write(uploaded_file.getbuffer())
        temp_path = handle.name
    if Path(uploaded_file.name).suffix.lower() == ".pdf":
        extraction, extraction_errors = extract_invoice_pdf(
            temp_path,
            as_of_date=st.session_state.get("as_of_date", date.today()),
            source_name=uploaded_file.name,
        )
        if extraction and manual_due_date is not None:
            invoice = extraction["records"]["invoices"][0]
            if not invoice.get("due"):
                invoice["due"] = manual_due_date.isoformat()
                extraction_errors = [
                    error
                    for error in extraction_errors
                    if error.field != "due_date"
                ]
        if extraction:
            extraction["records"]["invoices"][0]["received_inr"] = format(
                manual_received_amount, "f"
            )
        if not extraction:
            result = LoadResult(
                invoices=[],
                receipts=[],
                as_of_date=st.session_state.get("as_of_date", date.today()),
                errors=extraction_errors,
            )
        elif extraction_errors:
            result = LoadResult(
                invoices=[],
                receipts=[],
                as_of_date=st.session_state.get("as_of_date", date.today()),
                errors=extraction_errors,
            )
            return result, uploaded_file.name
        else:
            json_path = Path(temp_path).with_suffix(".json")
            json_path.write_text(
                json.dumps(extraction),
                encoding="utf-8",
            )
            result = load_fixture(json_path)
        result.errors = extraction_errors + result.errors
        return result, uploaded_file.name
    return load_fixture(temp_path), uploaded_file.name


def _initialize_state():
    if "load_result" not in st.session_state:
        result, source = _load_source(None)
        if result.as_of_date < date(1900, 1, 1):
            result.as_of_date = date.today()
        st.session_state.load_result = result
        st.session_state.source_name = source
        st.session_state.as_of_date = result.as_of_date
        st.session_state.reviewed_drafts = {}
        st.session_state.draft_text = {}
        st.session_state.negotiated_agreements = {}
        st.session_state.customer_contacts = {
            "Aarav General Store": "unnamedinsect424@gmail.com"
        }
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        starting = OUTPUT_DIR / "starting_state.json"
        if not starting.exists() and result.invoices:
            write_starting_state(
                evaluate_all(result.invoices, result.receipts, result.as_of_date),
                starting,
            )
    st.session_state.setdefault("negotiated_agreements", {})
    st.session_state.setdefault(
        "customer_contacts", {"Aarav General Store": "unnamedinsect424@gmail.com"}
    )
    st.session_state.setdefault("authenticated", False)
    st.session_state.setdefault("current_user", None)


def _safe_as_of_date(value: date | None) -> date:
    if value is None or value < date(1900, 1, 1):
        return date.today()
    return value


def _render_negotiated_recovery(
    customer: str,
    items,
    result: LoadResult,
    as_of: date,
) -> None:
    st.markdown("#### Negotiated next-order condition")
    st.caption(
        "Record the agreement reached by the distributor and retailer. "
        "Hisaabset tracks recovery and suggests eligibility; it never auto-approves an order."
    )
    invoice_options = [item.invoice_id for item in items]
    with st.expander("Create or update recovery agreement"):
        previous_invoice_id = st.selectbox(
            "Select the previous invoice", invoice_options,
            help="Choose the exact invoice whose recovery should be checked.",
        )
        selected = next(item for item in items if item.invoice_id == previous_invoice_id)
        detail_left, detail_right = st.columns(2)
        detail_left.metric("Invoice amount", _money(selected.invoice.amount))
        detail_right.metric("Amount collected", _money(selected.applied_receipts))
        detail_left.metric("Amount still outstanding", _money(selected.outstanding))
        detail_right.metric("Due date", selected.invoice.due_date.isoformat())
        st.caption(
            f"Status: {selected.state} · "
            f"Dispute: {'Yes' if selected.invoice.disputed else 'No'} · "
            f"Promise: {selected.promise_status}"
        )
        target_type = st.selectbox(
            "What did both parties agree to?",
            list(RecoveryTargetType),
            format_func=lambda item: {
                RecoveryTargetType.BEP_PLUS_AMOUNT: "BEP plus an agreed amount",
                RecoveryTargetType.EXACT_BEP: "Exactly the BEP amount",
                RecoveryTargetType.BEP_MULTIPLIER: "A percentage/multiple of BEP",
                RecoveryTargetType.CUSTOM_AMOUNT: "A custom agreed amount",
            }[item],
        )
        with st.form(f"negotiated-{customer}"):
            left, right = st.columns(2)
            with left:
                actual_bep: Decimal | None = None
                recovery_floor: Decimal | None = None
                extra: Decimal | None = None
                multiplier = 1.0
                custom: Decimal | None = None
                if target_type in {
                    RecoveryTargetType.BEP_PLUS_AMOUNT,
                    RecoveryTargetType.EXACT_BEP,
                    RecoveryTargetType.BEP_MULTIPLIER,
                }:
                    actual_bep = _decimal_input("Actual BEP (₹)", None)
                if target_type == RecoveryTargetType.BEP_PLUS_AMOUNT:
                    extra = _decimal_input("Additional agreed amount (₹)", None)
                elif target_type == RecoveryTargetType.BEP_MULTIPLIER:
                    multiplier = st.number_input(
                        "BEP multiplier", min_value=0.01, value=1.0, step=0.1,
                        format="%.2f",
                    )
                elif target_type == RecoveryTargetType.CUSTOM_AMOUNT:
                    custom = _decimal_input("Custom agreed recovery target (₹)", None)
                upfront = st.number_input(
                    "Next-order upfront (%)", min_value=0.0, max_value=100.0,
                    value=50.0, step=1.0,
                )
            with right:
                credit_days = st.number_input(
                    "Credit period (days)", min_value=1, value=90, step=1
                )
                if target_type in {
                    RecoveryTargetType.EXACT_BEP,
                    RecoveryTargetType.BEP_PLUS_AMOUNT,
                    RecoveryTargetType.BEP_MULTIPLIER,
                }:
                    st.info("Minimum recovery is set to the entered BEP.")
                else:
                    recovery_floor = _decimal_input(
                        "Minimum recovery floor (₹)", None
                    )
            note = st.text_area(
                "Negotiation note",
                placeholder="Optional: record who agreed and why these terms were accepted.",
            )
            save_agreement = st.form_submit_button("Save recovery agreement")
        if save_agreement:
            bep = actual_bep or Decimal("0.00")
            floor = (
                bep if target_type != RecoveryTargetType.CUSTOM_AMOUNT
                else recovery_floor or Decimal("0.00")
            )
            required_errors: list[str] = []
            if target_type != RecoveryTargetType.CUSTOM_AMOUNT and bep <= 0:
                required_errors.append("Enter the actual BEP amount.")
            if target_type == RecoveryTargetType.BEP_PLUS_AMOUNT and extra is None:
                required_errors.append("Enter the additional agreed amount.")
            if target_type == RecoveryTargetType.CUSTOM_AMOUNT and custom is None:
                required_errors.append("Enter the custom agreed recovery target.")
            if required_errors:
                for error in required_errors:
                    st.error(error)
                return
            try:
                target = calculate_target(
                    target_type, bep, extra or Decimal("0.00"),
                    Decimal(str(multiplier)), custom,
                )
                agreement = RecoveryAgreement(
                    agreement_id=f"AGR-{previous_invoice_id}",
                    retailer=customer,
                    previous_invoice_id=previous_invoice_id,
                    actual_bep=bep,
                    recovery_floor=floor,
                    target_type=target_type,
                    agreed_target=target,
                    upfront_percent=Decimal(str(upfront)).quantize(Decimal("0.01")),
                    credit_percent=(
                        Decimal("100.00") - Decimal(str(upfront))
                    ).quantize(Decimal("0.01")),
                    credit_period_days=int(credit_days),
                    baseline_collected=selected.applied_receipts,
                    agreement_date=as_of,
                    note=note.strip(),
                    status=AgreementStatus.PENDING_APPROVAL,
                )
                errors = validate_agreement(agreement)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.session_state.negotiated_agreements[customer] = agreement
                    st.success("Agreement saved and marked pending finance approval.")
                    st.rerun()
            except (ValueError, InvalidOperation) as error:
                st.error(f"Could not save agreement: {error}")

    agreement = st.session_state.negotiated_agreements.get(customer)
    if agreement is None:
        st.info("No negotiated recovery agreement has been recorded for this retailer.")
        return
    invoice = next(
        invoice for invoice in result.invoices
        if invoice.invoice_id == agreement.previous_invoice_id
    )
    progress = recovery_progress(agreement, invoice, result.receipts, as_of)
    st.write(
        f"**Target:** {_money(agreement.agreed_target)} · "
        f"**Recovered:** {_money(progress.recovered_amount)} · "
        f"**Target remaining:** {_money(progress.remaining_amount)}"
    )
    st.write(
        f"**Invoice outstanding:** {_money(progress.invoice_outstanding)} · "
        f"**Invoice balance after target payment:** "
        f"{_money(progress.invoice_balance_after_target)}"
    )
    st.caption(
        f"₹{agreement.baseline_collected:,.2f} was already collected before this "
        "agreement and is not counted toward the new recovery target."
    )
    st.write(
        f"**Status:** {progress.status.value} · "
        f"**Next order eligible:** {'Yes, subject to approval' if progress.next_order_eligible else 'Not yet'}"
    )
    st.caption(
        f"Suggested terms: {agreement.upfront_percent:.0f}% upfront / "
        f"{agreement.credit_percent:.0f}% credit for {agreement.credit_period_days} days. "
        f"Credit due date from a new order date is calculated as order date + "
        f"{agreement.credit_period_days} days."
    )
    if progress.excess_amount:
        st.warning(
            f"Recovery exceeds the target by {_money(progress.excess_amount)}. "
            "Review before applying the excess to another invoice."
        )
    if agreement.status != AgreementStatus.APPROVED:
        with st.form(f"approve-{customer}"):
            manager = st.text_input("Finance manager name")
            approval_note = st.text_area("Approval or override reason")
            approve = st.form_submit_button("Approve these terms")
        if approve:
            try:
                approved = approve_agreement(
                    agreement, manager, datetime.now(), approval_note
                )
                errors = validate_agreement(approved)
                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    st.session_state.negotiated_agreements[customer] = approved
                    st.success("Terms approved and audit details recorded.")
                    st.rerun()
            except ValueError as error:
                st.error(str(error))


def _apply_new_source(
    uploaded_file,
    manual_due_date: date | None = None,
    manual_received_amount: Decimal = Decimal("0.00"),
):
    result, source = _load_source(
        uploaded_file, manual_due_date, manual_received_amount
    )
    is_pdf = Path(uploaded_file.name).suffix.lower() == ".pdf"
    if is_pdf and not result.errors and result.invoices:
        existing = st.session_state.load_result
        existing_ids = {invoice.invoice_id for invoice in existing.invoices}
        new_invoices = [
            invoice for invoice in result.invoices
            if invoice.invoice_id not in existing_ids
        ]
        duplicate_count = len(result.invoices) - len(new_invoices)
        existing.invoices.extend(new_invoices)
        existing.receipts.extend(result.receipts)
        existing.errors.extend(result.errors)
        st.session_state.load_result = existing
        st.session_state.source_name = f"{st.session_state.source_name} + {source}"
        if duplicate_count:
            st.warning(
                f"{duplicate_count} PDF invoice(s) were skipped because the invoice number already exists."
            )
        st.session_state.reviewed_drafts = {}
        st.session_state.draft_text = {}
        st.session_state.negotiated_agreements = {}
        return
    st.session_state.load_result = result
    st.session_state.source_name = source
    st.session_state.as_of_date = result.as_of_date
    st.session_state.reviewed_drafts = {}
    st.session_state.draft_text = {}
    st.session_state.negotiated_agreements = {}


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


def _render_add_bill() -> None:
    st.subheader("Enter a bill manually")
    st.caption("Use this form when you do not have a file, or when a PDF field needs correction.")
    with st.form("add-manual-bill", clear_on_submit=False):
        st.markdown("#### 1. Customer and bill details")
        customer = st.text_input("Customer name *", placeholder="Example: Raj Electronics Pvt Ltd")
        invoice_id = st.text_input("Invoice number *", placeholder="Example: INV-1001")
        left, right = st.columns(2)
        with left:
            amount_value = st.number_input(
                "Invoice amount (₹) *", min_value=0.0, value=0.0, step=0.01, format="%.2f"
            )
            invoice_date = st.date_input(
                "Invoice date",
                value=date.today(),
                min_value=date(2000, 1, 1),
                key="new_invoice_date_v2",
            )
        with right:
            due_date = st.date_input(
                "Due date *",
                value=date.today(),
                min_value=date(2000, 1, 1),
                key="new_invoice_due_date_v2",
            )
            received_value = st.number_input(
                "Already received (₹)", min_value=0.0, value=0.0, step=0.01, format="%.2f"
            )

        st.markdown("#### 2. Optional dispute information")
        disputed = st.checkbox("Customer has a problem with this bill")
        disputed_amount: Decimal | None = None
        dispute_cause = None
        dispute_resolution = "none"
        credit_amount = Decimal("0.00")
        replacement_delivered = False
        if disputed:
            disputed_amount = _decimal_input("Amount in dispute (₹)", None)
            cause_options = sorted(VALID_CAUSES)
            dispute_cause = st.selectbox("Reason for dispute", cause_options)
            dispute_resolution = st.selectbox(
                "How is the dispute being handled?", sorted(VALID_RESOLUTIONS - {"none"})
            )
            if dispute_resolution == "replace_goods":
                replacement_delivered = st.checkbox("Replacement goods delivered")
            if dispute_resolution == "credit_note":
                credit_amount = _decimal_input("Credit note amount (₹)", None) or Decimal("0.00")

        st.markdown("#### 3. Optional payment promise")
        has_promise = st.checkbox("Customer promised to pay")
        promise_made_date = None
        promise_date = None
        promise_amount: Decimal | None = None
        if has_promise:
            promise_made_date = st.date_input(
                "Promise made date",
                value=date.today(),
                min_value=date(2000, 1, 1),
                key="new_promise_made_v2",
            )
            promise_date = st.date_input(
                "Promised payment date",
                value=date.today(),
                min_value=date(2000, 1, 1),
                key="new_promise_date_v2",
            )
            promise_amount = _decimal_input("Promised amount (₹)", None)

        save = st.form_submit_button("Save this bill")

    if not save:
        return
    errors: list[str] = []
    invoice_amount = Decimal(str(amount_value)).quantize(Decimal("0.01"))
    received_amount = Decimal(str(received_value)).quantize(Decimal("0.01"))
    existing_ids = {invoice.invoice_id for invoice in st.session_state.load_result.invoices}
    if not customer.strip():
        errors.append("Please enter the customer name.")
    if not invoice_id.strip():
        errors.append("Please enter the invoice number.")
    elif invoice_id.strip() in existing_ids:
        errors.append("This invoice number already exists.")
    if invoice_amount <= 0:
        errors.append("Invoice amount must be greater than zero.")
    if received_amount > invoice_amount:
        errors.append("Received amount cannot be greater than the invoice amount.")
    if due_date < invoice_date:
        errors.append("Due date cannot be before the invoice date.")
    invoice = Invoice(
        invoice_id=invoice_id.strip(),
        customer=customer.strip(),
        amount=invoice_amount,
        due_date=due_date,
        invoice_date=invoice_date,
        received_amount=received_amount,
        disputed=disputed,
        disputed_amount=disputed_amount,
        dispute_cause=dispute_cause,
        dispute_resolution=dispute_resolution,
        replacement_delivered=replacement_delivered,
        credit_amount=credit_amount,
        promise_made_date=promise_made_date,
        promise_date=promise_date,
        promise_amount=promise_amount,
    )
    errors.extend(validate_dispute(invoice, received_amount))
    if has_promise:
        if promise_made_date is None or promise_date is None or promise_amount is None:
            errors.append("Promise made date, promised date, and promised amount are required.")
        elif promise_date < promise_made_date:
            errors.append("Promised payment date cannot be before the promise made date.")
        elif promise_amount > max(
            Decimal("0.00"), invoice_amount - received_amount - credit_amount
        ):
            errors.append("Promised amount cannot exceed the remaining balance.")
    if errors:
        for error in errors:
            st.error(error)
        return
    st.session_state.load_result.invoices.append(invoice)
    st.success("Bill saved. It is now included in Customers, Your bills, priority, and exports.")
    st.rerun()


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
        due_date = st.date_input(
            "Agreed due date",
            value=_safe_as_of_date(invoice.due_date),
            min_value=date(2000, 1, 1),
            key=f"edit_due_date_{invoice.invoice_id}",
            help="Use this when you and the customer agree on a new payment date.",
        )
        received_amount = _decimal_input(
            "Already received amount", invoice.received_amount
        )
        settlement_agreed = st.checkbox(
            "Customer agreed to settle for less",
            value=invoice.settlement_agreed,
            help="Record the final amount the customer agreed to pay.",
        )
        settlement_amount = invoice.settlement_amount
        settlement_note = invoice.settlement_note
        if settlement_agreed:
            settlement_amount = _decimal_input(
                "Agreed final amount payable", invoice.settlement_amount
            )
            settlement_note = st.text_input(
                "Settlement note",
                value=invoice.settlement_note or "",
                placeholder="Example: Agreed by phone on 18 Oct 2026",
            )
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
        has_existing_promise = (
            invoice.promise_made_date is not None or invoice.promise_date is not None
        )
        has_promise = st.checkbox("Customer promised to pay", value=has_existing_promise)
        if has_promise:
            promise_made = st.date_input(
                "Promise made date",
                value=invoice.promise_made_date or date.today(),
                min_value=date(2000, 1, 1),
                key=f"edit_promise_made_{invoice.invoice_id}",
            )
            promise_date = st.date_input(
                "Promise date",
                value=invoice.promise_date or date.today(),
                min_value=date(2000, 1, 1),
                key=f"edit_promise_date_{invoice.invoice_id}",
            )
        else:
            promise_made = None
            promise_date = None
        promise_amount = _decimal_input("Promise amount", invoice.promise_amount)
        save = st.form_submit_button("Save review fields")
        if save:
            candidate = Invoice(
                **{
                    **invoice.__dict__,
                    "due_date": due_date,
                    "received_amount": received_amount or Decimal("0.00"),
                    "settlement_agreed": settlement_agreed,
                    "settlement_amount": settlement_amount,
                    "settlement_note": settlement_note or None,
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
            if due_date < (candidate.invoice_date or due_date):
                errors.append("Agreed due date cannot be before the invoice date.")
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
        email_key = f"customer-email-{customer}"
        recipient = st.text_input(
            "Customer email",
            value=st.session_state.customer_contacts.get(customer, ""),
            key=email_key,
            help="Use an address you control for the first test.",
        )
        st.session_state.customer_contacts[customer] = recipient.strip()
        reviewed = st.checkbox(
            "I reviewed the exact figures and approve this email",
            value=st.session_state.reviewed_drafts.get(customer, False),
            key=f"reviewed-{customer}",
        )
        st.session_state.reviewed_drafts[customer] = reviewed
        test_mode = os.getenv("HISAABSET_EMAIL_TEST_MODE", "true").lower() in {
            "1", "true", "yes", "on"
        }
        if test_mode:
            st.info(
                "Email test mode is enabled. Approval will validate the draft "
                "but will not deliver a message."
            )
        if st.button(
            "Approve and send email",
            key=f"send-email-{customer}",
            disabled=not reviewed,
        ):
            if not valid_email(recipient):
                st.error("Enter a valid customer email before sending.")
                continue
            result = send_via_ses(
                recipient=recipient,
                subject=draft["subject"],
                body=body,
            )
            if result.status == "sent":
                st.success(
                    f"Email sent to {recipient}. "
                    f"SES message ID: {result.provider_message_id}"
                )
            elif result.status == "test_blocked":
                st.warning(result.message)
            else:
                st.error(result.message)

def _render_login_page() -> None:
    st.markdown(
        """
        <div class="ll-login-shell">
          <div class="ll-login-brand">
            <div class="ll-login-logo">₹</div>
            <div class="ll-login-name">Hisaabset</div>
            <div class="ll-login-tag">HAR PAYMENT KA CLEAR HISAB</div>
            <div class="ll-login-copy">Receivables command center for finance teams</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login-form", clear_on_submit=False):
        st.markdown('<div class="ll-login-kicker">Secure workspace access</div>', unsafe_allow_html=True)
        st.markdown("#### Sign in to your account")
        username = st.text_input("Username or Email", placeholder="Enter your work email or username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        submit = st.form_submit_button("Sign in to Hisaabset", use_container_width=True)

        if submit:
            if not username.strip() or not password:
                st.error("Please enter both username and password.")
            else:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.current_user = user
                    st.success(f"Welcome back, {user.display_name}! Loading your workspace...")
                    st.rerun()
                else:
                    st.error("Invalid username or password. Please check your credentials.")

    if st.button("⚡  Continue with Finance Lead demo", use_container_width=True, key="demo-admin"):
        st.session_state.authenticated = True
        st.session_state.current_user = FINANCE_LEAD
        st.rerun()

    st.markdown(
        """
        <div class="ll-login-shell">
          <div class="ll-login-demo"><b>Demo access</b><br>
          Use the Finance Lead demo above, or sign in with the configured demo account.
          Production deployments should connect this screen to enterprise SSO.</div>
          <div class="ll-login-trust">
            <span><i></i>Session protected</span>
            <span><i></i>Finance workspace</span>
            <span><i></i>Review before action</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    st.set_page_config(page_title="Hisaabset | Har payment ka clear hisab", layout="wide")
    _initialize_state()
    _inject_styles()
    _render_session_loader()

    if not st.session_state.get("authenticated", False):
        _render_login_page()
        return
    result = st.session_state.load_result
    safe_as_of = _safe_as_of_date(st.session_state.get("as_of_date"))
    if result.as_of_date < date(1900, 1, 1):
        result.as_of_date = safe_as_of
    st.session_state.as_of_date = safe_as_of
    current_user: User = st.session_state.get("current_user", FINANCE_LEAD)

    with st.sidebar:
        st.markdown(
            '<div class="ll-brand"><div class="ll-logo">₹</div>'
            '<div class="ll-brand-name">Hisaabset</div></div>'
            '<div class="ll-brand-tagline">Har payment ka clear hisab</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div style="background:#eef7f5; border:1px solid #c8e4de; border-radius:14px; padding:10px 12px; margin-bottom:10px;">
                <div style="font-size:10px; font-weight:800; color:#087f72; letter-spacing:0.05em; text-transform:uppercase;">Signed In As</div>
                <div style="font-size:14px; font-weight:800; color:#173b3b;">{current_user.display_name}</div>
                <div style="font-size:11px; font-weight:700; color:#557070;">{current_user.role} · {current_user.email}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("Sign out", key="logout-btn", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.current_user = None
            st.rerun()

        st.markdown(
            '<div class="ll-side-hint">Use the menu above to move around.<br>'
            'Import files and set filters here.</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.subheader("Import data")
        upload = st.file_uploader(
            "Add JSON, CSV, or computer-generated PDF",
            type=["json", "csv", "pdf"],
            help=(
                "PDF uploads must contain selectable text. The extracted invoice "
                "number, customer, total, and due date are validated before use."
            ),
        )
        if upload is not None and Path(upload.name).suffix.lower() == ".pdf":
            st.info(
                "PDF mode: upload one computer-generated invoice. "
                "Scanned/image-only PDFs need OCR and will be reported for review."
            )
            has_manual_due_date = st.checkbox(
                "Provide a manual due date",
                help=(
                    "Enable this only when the contractual due date is known. "
                    "The application never invents a missing PDF due date."
                ),
            )
            manual_due_date = (
                st.date_input(
                    "Manual due date if PDF has no due date",
                    value=date.today(),
                    min_value=date(2000, 1, 1),
                    key="manual_pdf_due_date_v2",
                )
                if has_manual_due_date
                else None
            )
            manual_received_amount = Decimal(str(st.number_input(
                "Already received amount (₹)",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f",
                help="Enter payments already received for this invoice.",
            ))).quantize(Decimal("0.01"))
        else:
            manual_due_date = None
            manual_received_amount = Decimal("0.00")
        if st.button("Load selected file") and upload is not None:
            _apply_new_source(
                upload, manual_due_date, manual_received_amount
            )
            st.rerun()
        as_of = st.date_input(
            "As-of date",
            value=safe_as_of,
            min_value=date(1900, 1, 1),
            max_value=date(2100, 12, 31),
            key="as_of_date_picker_v2",
        )
        st.session_state.as_of_date = as_of
        customers = sorted({invoice.customer for invoice in result.invoices})
        customer_filter = st.multiselect("Customer filter", customers)
        st.markdown(
            '<div class="ll-note">Messages open in WhatsApp or email for your review. '
            'Nothing is sent automatically.</div>',
            unsafe_allow_html=True,
        )

    navigation = st.radio(
        "Main navigation",
        ["＋ Add new bill", "▤ Your bills", "♟ Customers"],
        horizontal=True,
        label_visibility="collapsed",
    )
    _render_command_header(navigation, result)

    if navigation == "＋ Add new bill":
        st.markdown('<div class="ll-eyebrow">WELCOME TO HISAABSET</div>', unsafe_allow_html=True)
        st.markdown('<div class="ll-title">Add a new bill</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ll-welcome"><div><div class="ll-welcome-title">Har payment ka clear hisab</div>'
            '<div class="ll-welcome-copy">Apne bills upload karein, payment track karein aur har customer ka status ek nazar mein samjhein.</div>'
            '</div><div class="ll-welcome-icon">₹</div></div>'
            '<div class="ll-subtitle">4 small steps. We work out the rest for you.</div>'
            '<div class="ll-help">Start here: upload one invoice file, then press '
            '<b>Load selected file</b>. We will calculate what is paid, what is due, '
            'and what needs attention.</div>',
            unsafe_allow_html=True,
        )
    elif navigation == "♟ Customers":
        st.markdown('<div class="ll-eyebrow">HISAABSET DIRECTORY</div>', unsafe_allow_html=True)
        st.markdown('<div class="ll-title">Customers</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ll-subtitle">See who owes you and open their invoices.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="ll-eyebrow">HISAABSET WORKSPACE</div>', unsafe_allow_html=True)
        st.markdown('<div class="ll-title">Your bills</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="ll-subtitle">Ranked by who is most late. Number 1 is the first to ask.</div>',
            unsafe_allow_html=True,
        )
    with st.expander("Show file and technical details"):
        st.caption(f"Loaded source: `{st.session_state.source_name}`")

    if navigation == "＋ Add new bill":
        _render_add_bill()

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

    if navigation == "♟ Customers":
        customer_rows = []
        reference_limit = Decimal(str(st.number_input(
            "Reference purchase amount (₹)",
            min_value=0.0,
            value=100000.0,
            step=1000.0,
            format="%.2f",
            help="Used only to show a suggested purchasing limit. Final approval stays with the finance manager.",
        ))).quantize(Decimal("0.01"))
        history_by_customer = retailer_history(
            result.invoices, result.receipts, as_of
        )
        for customer in sorted({item.customer for item in evaluations}):
            items = [item for item in evaluations if item.customer == customer]
            history = history_by_customer[customer]
            risk = retailer_risk(history)
            recommendation = credit_recommendation(risk, history, reference_limit)
            customer_rows.append({
                "Customer": customer,
                "Invoices": len(items),
                "Outstanding": _money(sum((item.outstanding for item in items), Decimal("0.00"))),
                "Collectable": _money(sum((item.collectable_amount for item in items), Decimal("0.00"))),
                "Under review": _money(sum((item.review_amount for item in items), Decimal("0.00"))),
                "Risk rating": (
                    str(risk.rating) if risk.rating is not None else "Not available"
                ),
                "Risk status": risk.category,
                "Suggested limit": _money(recommendation.purchasing_multiplier),
                "Upfront": f"{recommendation.upfront_percent:.0f}%",
                "Credit": f"{recommendation.credit_percent:.0f}%",
            })
        st.subheader("Customer directory")
        if customer_rows:
            st.dataframe(pd.DataFrame(customer_rows), hide_index=True, use_container_width=True)
            st.markdown(
                '<div class="ll-note"><b>Finance manager reminder:</b> these are '
                'evidence-based suggestions only. Review the retailer history before '
                'approving any new purchasing limit or credit terms.</div>',
                unsafe_allow_html=True,
            )
            selected_customer = st.selectbox(
                "View retailer evidence",
                sorted({item.customer for item in evaluations}),
            )
            selected_items = [
                item for item in evaluations if item.customer == selected_customer
            ]
            selected_history = history_by_customer[selected_customer]
            selected_risk = retailer_risk(selected_history)
            st.markdown(f"#### {selected_customer} payment evidence")
            if selected_risk.rating is None:
                st.info("Risk rating is not assigned until at least 3 invoices are completed.")
            else:
                selected_recommendation = credit_recommendation(
                    selected_risk, selected_history, reference_limit
                )
                st.write(
                    f"**Rating:** {selected_risk.rating}/100 · "
                    f"**Status:** {selected_risk.category}"
                )
                st.write(
                    f"**Suggested limit:** {_money(selected_recommendation.purchasing_multiplier)} · "
                    f"**Terms:** {selected_recommendation.upfront_percent:.0f}% upfront / "
                    f"{selected_recommendation.credit_percent:.0f}% credit"
                )
                for reason in selected_risk.explanation:
                    st.caption(reason)
                st.warning(
                    "This is a recommendation only. A distributor finance manager "
                    "must approve or override the terms."
                )
            _render_negotiated_recovery(
                selected_customer, selected_items, result, as_of
            )
        else:
            st.markdown(
                '<div class="ll-note">No customers yet. Add an invoice file to begin.</div>',
                unsafe_allow_html=True,
            )
        return

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
        negotiated_progress = []
        for agreement in st.session_state.negotiated_agreements.values():
            invoice = next(
                (
                    item for item in result.invoices
                    if item.invoice_id == agreement.previous_invoice_id
                ),
                None,
            )
            if invoice is not None:
                negotiated_progress.append(
                    recovery_progress(
                        agreement, invoice, result.receipts, as_of
                    )
                )
        write_negotiated_json(
            negotiated_progress, OUTPUT_DIR / "negotiated_recovery.json"
        )
        write_evidence_log(
            OUTPUT_DIR / "evidence_log.md",
            evaluations,
            fixture_name=st.session_state.source_name,
            receipt_count=len(result.receipts),
            validation_errors=result.errors,
        )
        st.success(
            "Exported result.json, result.csv, negotiated_recovery.json, and evidence_log.md."
        )
    st.caption(
        "Figures come from synthetic data. No cash recovery or production readiness "
        "is claimed. No message is sent without finance approval."
    )
    st.markdown(
        '<div class="ll-footer-note"><b>Built for clear decisions.</b> '
        'Every figure is recalculated from the selected as-of date. '
        'Disputed money stays visible. Nothing is sent automatically.</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
