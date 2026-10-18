import { ChangeEvent, useMemo, useState } from "react";
import {
  AlertTriangle, ArrowDownToLine, ArrowUpRight, Bell, Check, ChevronRight,
  CircleDollarSign, CircleHelp, Clock3, FileText, FolderOpen, LayoutDashboard,
  Mail, Menu, Plus, Search, Settings2, ShieldCheck, SlidersHorizontal, Upload,
  Users, WalletCards, X,
} from "lucide-react";
import fixture from "../public/fixture.json";

type RawInvoice = {
  id: string; amount_inr: number; received_inr: number; due: string; disputed: boolean; customer: string;
  invoice_date?: string; disputed_amount?: number | null; dispute_cause?: string | null;
  dispute_resolution?: "none" | "pending" | "replace_goods" | "credit_note";
  replacement_delivered?: boolean; credit_amount?: number; settlement_agreed?: boolean;
  settlement_amount?: number | null; settlement_note?: string | null;
  promise_made_date?: string | null; promise_date?: string | null; promise_amount?: number | null;
  vendor_email?: string | null;
};
type Receipt = { receipt_id: string; invoice_id: string | null; customer: string | null; amount: number; receipt_date?: string | null; };
type Invoice = RawInvoice & { applied: number; creditApplied: number; outstanding: number; overpaid: number; collectible: number; review: number; state: State; daysOverdue: number; score: number | null; ageing: string; promiseStatus: "none" | "active" | "kept" | "broken"; promisedPaid: number; promiseShortfall: number; };
type State = "Paid" | "Under Review" | "Collectable" | "Not due" | "Promised";
type Navigation = "add" | "bills" | "customers";
type Tab = "priority" | "review" | "promised" | "safe" | "unapplied" | "drafts" | "detail";
type RecoveryAgreement = { id: string; retailer: string; invoiceId: string; bep: number; floor: number; target: number; upfront: number; credit: number; creditDays: number; baseline: number; note: string; approvedBy?: string; approvedAt?: string; approvalNote?: string; };

const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(value);
const money0 = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
const today = fixture.records.as_of;

function normalizeInvoice(item: Record<string, unknown>): RawInvoice {
  return {
    id: String(item.id ?? item.invoice_id ?? ""), amount_inr: Number(item.amount_inr ?? item.amount ?? 0),
    received_inr: Number(item.received_inr ?? item.received_amount ?? 0), due: String(item.due ?? item.due_date ?? ""),
    disputed: Boolean(item.disputed), customer: String(item.customer ?? ""), invoice_date: item.invoice_date ? String(item.invoice_date) : undefined,
    disputed_amount: item.disputed_amount == null ? null : Number(item.disputed_amount), dispute_cause: item.dispute_cause ? String(item.dispute_cause) : null,
    dispute_resolution: (item.dispute_resolution as RawInvoice["dispute_resolution"]) ?? (item.disputed ? "pending" : "none"),
    replacement_delivered: Boolean(item.replacement_delivered), credit_amount: Number(item.credit_amount ?? 0),
    settlement_agreed: Boolean(item.settlement_agreed), settlement_amount: item.settlement_amount == null ? null : Number(item.settlement_amount),
    settlement_note: item.settlement_note ? String(item.settlement_note) : null, promise_made_date: item.promise_made_date ? String(item.promise_made_date) : null,
    promise_date: item.promise_date ? String(item.promise_date) : null, promise_amount: item.promise_amount == null ? null : Number(item.promise_amount),
    vendor_email: item.vendor_email ? String(item.vendor_email) : null,
  };
}
function normalizeReceipt(item: Record<string, unknown>, index: number): Receipt {
  return { receipt_id: String(item.receipt_id ?? `receipt-${index + 1}`), invoice_id: item.invoice_id ? String(item.invoice_id) : null, customer: item.customer ? String(item.customer) : null, amount: Number(item.amount ?? 0), receipt_date: item.receipt_date ? String(item.receipt_date) : null };
}
function validateRows(invoices: RawInvoice[], receipts: Receipt[]): string[] {
  const errors: string[] = []; const ids = new Set<string>();
  invoices.forEach((item, index) => { if (!item.id) errors.push(`invoice ${index + 1}: invoice_id is required`); if (ids.has(item.id)) errors.push(`invoice ${index + 1}: duplicate invoice_id`); ids.add(item.id); if (item.amount_inr <= 0) errors.push(`${item.id}: amount must be greater than zero`); if (!item.due) errors.push(`${item.id}: due_date is required`); if (item.received_inr < 0) errors.push(`${item.id}: received amount cannot be negative`); if (item.disputed_amount != null && item.disputed_amount > item.amount_inr - item.received_inr) errors.push(`${item.id}: disputed amount exceeds balance`); if (item.dispute_resolution === "credit_note" && !(item.credit_amount && item.credit_amount > 0)) errors.push(`${item.id}: credit note requires credit_amount`); });
  receipts.forEach((receipt) => { if (receipt.amount <= 0) errors.push(`${receipt.receipt_id}: amount must be greater than zero`); if (receipt.invoice_id && !ids.has(receipt.invoice_id)) errors.push(`${receipt.receipt_id}: unknown invoice; kept as unapplied`); });
  return errors;
}

function evaluate(raw: RawInvoice[], receipts: Receipt[], asOf: string): Invoice[] {
  const asOfDate = new Date(`${asOf}T00:00:00`);
  const max = Math.max(...raw.map((item) => Math.max(0, item.amount_inr - item.received_inr)), 0);
  return raw.map((item) => {
    const due = new Date(`${item.due}T00:00:00`);
    const linked = receipts.filter((receipt) => receipt.invoice_id === item.id && (!receipt.receipt_date || receipt.receipt_date <= asOf));
    const applied = linked.length ? linked.reduce((sum, receipt) => sum + receipt.amount, 0) : item.received_inr;
    const creditApplied = item.settlement_agreed && item.settlement_amount != null
      ? Math.max(0, item.amount_inr - item.settlement_amount)
      : item.dispute_resolution === "credit_note" ? item.credit_amount ?? 0 : 0;
    const rawBalance = item.amount_inr - applied - creditApplied;
    const outstanding = Math.max(0, rawBalance);
    const disputedAmount = item.disputed_amount == null ? outstanding : Math.min(item.disputed_amount, outstanding);
    const review = item.dispute_resolution === "credit_note" || (item.dispute_resolution === "replace_goods" && item.replacement_delivered)
      ? 0 : (item.disputed || item.dispute_resolution === "pending" || item.dispute_resolution === "replace_goods" ? disputedAmount : 0);
    const collectible = outstanding - review;
    const daysOverdue = Math.max(0, Math.floor((asOfDate.getTime() - due.getTime()) / 86400000));
    const promisedPaid = linked.filter((receipt) => receipt.receipt_date && item.promise_made_date && receipt.receipt_date >= item.promise_made_date).reduce((sum, receipt) => sum + receipt.amount, 0);
    const promiseTarget = item.promise_amount ?? collectible;
    const promiseShortfall = Math.max(0, promiseTarget - promisedPaid);
    const promiseStatus: Invoice["promiseStatus"] = !item.promise_date || !item.promise_made_date || collectible <= 0 ? "none" : promiseShortfall <= 0 ? "kept" : asOf <= item.promise_date ? "active" : "broken";
    const state: State = outstanding === 0 ? "Paid" : review > 0 && collectible === 0 ? "Under Review" : promiseStatus === "active" ? "Promised" : asOfDate <= due ? "Not due" : "Collectable";
    const promiseScore = promiseStatus === "broken" && promiseTarget ? promiseShortfall / promiseTarget : 0;
    const base = 100 * (0.45 * Math.min(daysOverdue, 90) / 90 + 0.35 * (max ? collectible / max : 1) + 0.20 * promiseScore);
    const escalation = daysOverdue > 90 ? 0.25 + 0.5 * Math.min((daysOverdue - 90) / 90, 1) : 0;
    const score = state === "Collectable" && collectible > 0 ? base + (100 - base) * escalation : null;
    return { ...item, applied, creditApplied, outstanding, overpaid: Math.max(0, -rawBalance), collectible, review, state, daysOverdue, score, ageing: daysOverdue <= 0 ? "Not due" : daysOverdue <= 30 ? "1-30" : daysOverdue <= 60 ? "31-60" : daysOverdue <= 90 ? "61-90" : "90+", promiseStatus, promisedPaid, promiseShortfall };
  }).sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
}

function App() {
  const [navigation, setNavigation] = useState<Navigation>("add");
  const [tab, setTab] = useState<Tab>("priority");
  const [asOf, setAsOf] = useState(today);
  const [invoices, setInvoices] = useState<RawInvoice[]>(fixture.records.invoices as RawInvoice[]);
  const [receipts, setReceipts] = useState<Receipt[]>([]);
  const [agreements, setAgreements] = useState<Record<string, RecoveryAgreement>>({});
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [filter, setFilter] = useState<string[]>([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Invoice | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [toast, setToast] = useState("");
  const evaluations = useMemo(() => evaluate(invoices, receipts, asOf).filter((item) => !filter.length || filter.includes(item.customer)).filter((item) => `${item.id} ${item.customer}`.toLowerCase().includes(search.toLowerCase())), [invoices, receipts, asOf, filter, search]);
  const customers = [...new Set(invoices.map((item) => item.customer))].sort();
  const total = (key: "outstanding" | "collectible" | "review") => evaluations.reduce((sum, item) => sum + item[key], 0);
  const promised = evaluations.filter((item) => item.state === "Promised");
  const showToast = (message: string) => { setToast(message); window.setTimeout(() => setToast(""), 3000); };

  const loadFile = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (file.name.toLowerCase().endsWith(".json")) {
      const reader = new FileReader();
      reader.onload = () => {
        try {
          const data = JSON.parse(String(reader.result));
          const rows = data.records?.invoices ?? data.invoices ?? [];
          const loaded = rows.map((item: Record<string, unknown>) => normalizeInvoice(item));
          const loadedReceipts = (data.records?.receipts ?? data.receipts ?? []).map((item: Record<string, unknown>, index: number) => normalizeReceipt(item, index));
          setInvoices(loaded); setReceipts(loadedReceipts); setValidationErrors(validateRows(loaded, loadedReceipts));
          if (data.records?.as_of || data.as_of_date) setAsOf(String(data.records?.as_of ?? data.as_of_date));
          showToast(`${file.name} loaded successfully`);
        } catch { showToast("Could not read this JSON file"); }
      };
      reader.readAsText(file);
    } else if (file.name.toLowerCase().endsWith(".csv")) {
      const reader = new FileReader();
      reader.onload = () => {
        const lines = String(reader.result).trim().split(/\r?\n/);
        const headers = lines.shift()?.split(",") ?? [];
        const rows = lines.map((line) => Object.fromEntries(line.split(",").map((value, index) => [headers[index], value])));
        const loaded = rows.map((item) => normalizeInvoice(item)); setInvoices(loaded); setValidationErrors(validateRows(loaded, []));
        showToast(`${file.name} loaded successfully`);
      };
      reader.readAsText(file);
    } else showToast("PDF review is available in the Streamlit app; upload JSON or CSV here");
  };
  const addBill = (bill: RawInvoice) => { setInvoices((current) => [...current, bill]); setNavigation("bills"); showToast("Bill saved in this session"); };
  const exportResults = () => {
    const download = (content: string, name: string, type: string) => { const blob = new Blob([content], { type }); const url = URL.createObjectURL(blob); const link = document.createElement("a"); link.href = url; link.download = name; link.click(); URL.revokeObjectURL(url); };
    download(JSON.stringify({ records: { invoices: evaluations, receipts }, as_of: asOf, synthetic: true }, null, 2), "ledgerloop-result.json", "application/json");
    const columns = ["invoice_id", "customer", "amount", "received", "outstanding", "collectable", "under_review", "state", "due_date", "days_overdue", "ageing", "score", "promise_status", "promise_shortfall"];
    const csv = [columns.join(","), ...evaluations.map((item) => [item.id, item.customer, item.amount_inr, item.applied, item.outstanding, item.collectible, item.review, item.state, item.due, item.daysOverdue, item.ageing, item.score?.toFixed(2) ?? "", item.promiseStatus, item.promiseShortfall].map((value) => `"${String(value).replace(/"/g, '""')}"`).join(","))].join("\n");
    download(csv, "ledgerloop-result.csv", "text/csv");
    const evidence = `# LedgerLoop evidence log\n\n## Starting state\n\nFixture: browser-loaded synthetic data\n- Invoices evaluated: ${evaluations.length}\n- Receipts loaded: ${receipts.length}\n- As-of date: ${asOf}\n\n## Final evidence\n\n- Outstanding: ${money(total("outstanding"))}\n- Collectable: ${money(total("collectible"))}\n- Under review: ${money(total("review"))}\n- Priority weights: age 45%, amount 35%, broken promise 20%\n- Age cap: 90 days\n\n## Observed versus assumed\n\nFigures come from synthetic data. Drafts are review-only. No receipt is auto-applied and no message is sent automatically.\n`;
    download(evidence, "ledgerloop-evidence-log.md", "text/markdown");
    download(JSON.stringify(Object.values(agreements), null, 2), "ledgerloop-negotiated-recovery.json", "application/json");
    showToast("JSON, CSV, recovery, and evidence exports downloaded");
  };

  return <div className="app-shell">
    <aside className={sidebarOpen ? "sidebar open" : "sidebar"}>
      <div className="brand"><div className="brand-mark">₹</div><div><strong>Hisaabset</strong><span>Har payment ka clear hisab</span></div></div>
      <div className="side-hint">Use the menu above to move around.<br />Import files and set filters here.</div>
      <div className="side-section"><p>IMPORT DATA</p><label className="upload-control"><Upload size={16} /><span>Upload JSON, CSV or PDF</span><input type="file" accept=".json,.csv,.pdf" onChange={loadFile} /></label><button className="load-file" onClick={() => showToast("Choose a file above to load it")}><FolderOpen size={15} /> Load selected file</button></div>
      <div className="side-section"><p>WORKSPACE</p><label className="side-label">As-of date<input type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} /></label><div className="filter-select"><SlidersHorizontal size={14} /><select value={filter[0] ?? ""} onChange={(event) => setFilter(event.target.value ? [event.target.value] : [])}><option value="">All customers</option>{customers.map((customer) => <option key={customer}>{customer}</option>)}</select></div></div>
      <div className="side-note"><Mail size={15} /> Messages are for your review. Nothing is sent automatically.</div>
      <div className="sidebar-bottom"><button className="nav-item"><Settings2 size={17} /><span>Settings</span></button><div className="safe-card"><ShieldCheck size={18} /><div><b>Safe mode on</b><small>Source data stays protected</small></div></div></div>
    </aside>
    <main className="main">
      <header className="topbar"><button className="mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)}><Menu /></button><div className="breadcrumbs">Hisaabset <ChevronRight size={14} /> <b>{navigation === "add" ? "Add new bill" : navigation === "bills" ? "Your bills" : "Customers"}</b></div><div className="top-actions"><div className="search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search invoices..." /></div><button className="icon-btn"><Bell size={17} /><i /></button><div className="top-avatar">FL</div></div></header>
      <div className="content">
        {navigation === "add" && <AddBill onSave={addBill} />}
        {navigation === "bills" && <><PageHeading eyebrow="HISAABSET WORKSPACE" title="Your bills" subtitle="Ranked by who is most late. Number 1 is the first to ask." asOf={asOf} />{validationErrors.length > 0 && <div className="validation-banner"><AlertTriangle size={17} /><span><b>{validationErrors.length} validation error(s) found.</b> Invalid rows are excluded from calculations.<small>{validationErrors.slice(0, 3).join(" · ")}</small></span></div>}<div className="stats-grid compact"><Stat label="Outstanding" value={money(total("outstanding"))} tone="navy" icon={<WalletCards />} /><Stat label="Collectable" value={money(total("collectible"))} tone="teal" icon={<ArrowUpRight />} /><Stat label="Under review" value={money(total("review"))} tone="amber" icon={<AlertTriangle />} /><Stat label="Promised" value={String(promised.length)} tone="purple" icon={<Clock3 />} /></div><div className="tab-strip">{([["priority", "Priority list"], ["review", "Under review"], ["promised", "Promised"], ["safe", "Not yet due / Paid"], ["unapplied", "Unapplied receipts"], ["drafts", "Draft plan"], ["detail", "Invoice detail"]] as [Tab, string][]).map(([key, label]) => <button className={tab === key ? "tab active" : "tab"} key={key} onClick={() => setTab(key)}>{label}</button>)}</div><BillWorkspace tab={tab} evaluations={evaluations} receipts={receipts} onSelect={setSelected} onExport={exportResults} /></>}
        {navigation === "customers" && <Customers evaluations={evaluations} agreements={agreements} onAgreement={(agreement) => { setAgreements((current) => ({ ...current, [agreement.retailer]: agreement })); showToast("Recovery agreement saved for finance approval"); }} onSelect={setSelected} onToast={showToast} />}
      </div>
    </main>
    {selected && <Detail invoice={selected} onClose={() => setSelected(null)} onSave={(updated) => { setInvoices((items) => items.map((item) => item.id === updated.id ? updated : item)); setSelected(null); showToast("Review fields saved"); }} />}
    {toast && <div className="toast"><Check size={16} />{toast}</div>}
    <nav className="bottom-nav"><button className={navigation === "add" ? "active" : ""} onClick={() => setNavigation("add")}><Plus />Add bill</button><button className={navigation === "bills" ? "active" : ""} onClick={() => setNavigation("bills")}><LayoutDashboard />Your bills</button><button className={navigation === "customers" ? "active" : ""} onClick={() => setNavigation("customers")}><Users />Customers</button></nav>
  </div>;
}

function PageHeading({ eyebrow, title, subtitle, asOf }: { eyebrow: string; title: string; subtitle: string; asOf?: string }) { return <section className="page-heading"><div><p className="eyebrow">{eyebrow}</p><h1>{title}</h1><p>{subtitle}</p></div>{asOf && <div className="date-badge"><small>DATA AS OF</small><b>{asOf}</b></div>}</section>; }
function Stat({ label, value, tone, icon }: { label: string; value: string; tone: string; icon: React.ReactNode }) { return <div className={`stat-card ${tone}`}><div className="stat-head"><span>{label}</span><span className="stat-icon">{icon}</span></div><strong>{value}</strong><small>Current selected view</small></div>; }
function AddBill({ onSave }: { onSave: (bill: RawInvoice) => void }) { const [customer, setCustomer] = useState(""); const [id, setId] = useState(""); const [amount, setAmount] = useState(""); const [received, setReceived] = useState("0"); const [due, setDue] = useState(today); const [disputed, setDisputed] = useState(false); const [promise, setPromise] = useState(false); const [error, setError] = useState(""); const save = () => { const numeric = Number(amount); if (!customer.trim() || !id.trim()) return setError("Customer name and invoice number are required."); if (numeric <= 0) return setError("Invoice amount must be greater than zero."); if (Number(received) > numeric) return setError("Received amount cannot be greater than the invoice amount."); onSave({ id: id.trim(), customer: customer.trim(), amount_inr: numeric, received_inr: Number(received), due, disputed }); }; return <><PageHeading eyebrow="WELCOME TO HISAABSET" title="Add a new bill" subtitle="4 small steps. We work out the rest for you." /><section className="welcome-banner"><div><h2>Har payment ka clear hisab</h2><p>Apne bills upload karein, payment track karein aur har customer ka status ek nazar mein samjhein.</p></div><span>₹</span></section><div className="help-banner"><CircleHelp size={18} /><span>Start here: upload one invoice file, then press <b>Load selected file</b>. We calculate what is paid, what is due, and what needs attention.</span></div><section className="form-card"><FormTitle number="1" title="Customer and bill details" /><div className="form-grid"><Input label="Customer name *" value={customer} onChange={setCustomer} placeholder="Example: Raj Electronics Pvt Ltd" /><Input label="Invoice number *" value={id} onChange={setId} placeholder="Example: INV-1001" /><Input label="Invoice amount (₹) *" value={amount} onChange={setAmount} type="number" /><Input label="Already received (₹)" value={received} onChange={setReceived} type="number" /><Input label="Due date *" value={due} onChange={setDue} type="date" /></div><FormTitle number="2" title="Optional dispute information" /><label className="check-row"><input type="checkbox" checked={disputed} onChange={(event) => setDisputed(event.target.checked)} />Customer has a problem with this bill</label>{disputed && <div className="inline-callout"><AlertTriangle size={15} /> The disputed balance will be held under review and excluded from collection follow-up.</div>}<FormTitle number="3" title="Optional payment promise" /><label className="check-row"><input type="checkbox" checked={promise} onChange={(event) => setPromise(event.target.checked)} />Customer promised to pay</label>{promise && <div className="inline-callout teal"><Clock3 size={15} /> Promise detail fields can be completed in invoice review after saving.</div>}{error && <div className="form-error"><AlertTriangle size={15} />{error}</div>}<button className="primary-btn save-btn" onClick={save}><Check size={16} /> Save this bill</button></section></>; }
function FormTitle({ number, title }: { number: string; title: string }) { return <div className="form-title"><span>{number}</span><h3>{title}</h3></div>; }
function Input({ label, value, onChange, placeholder, type = "text" }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; type?: string }) { return <label className="field"><span>{label}</span><input type={type} value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} /></label>; }

function BillWorkspace({ tab, evaluations, receipts, onSelect, onExport }: { tab: Tab; evaluations: Invoice[]; receipts: Receipt[]; onSelect: (invoice: Invoice) => void; onExport: () => void }) { const ranked = evaluations.filter((item) => item.state === "Collectable"); if (tab === "drafts") return <DraftPlan evaluations={evaluations} />; if (tab === "detail") return <section className="panel full-panel"><PanelTitle eyebrow="INVOICE DETAIL" title="Select an invoice to inspect" /><InvoiceTable evaluations={evaluations} onSelect={onSelect} /></section>; if (tab === "review") return <DataPanel eyebrow="DISPUTE WORKFLOW" title="Under review" columns={["Invoice", "Customer", "Review", "Cause", "Resolution"]} rows={evaluations.filter((item) => item.review > 0).map((item) => [item.id, item.customer, money(item.review), item.dispute_cause ?? "dispute detail missing", item.dispute_resolution ?? "none"])} />; if (tab === "promised") return <DataPanel eyebrow="PROMISES TO PAY" title="Promised" columns={["Invoice", "Customer", "Promise date", "Promised", "Received", "Shortfall"]} rows={evaluations.filter((item) => item.promiseStatus !== "none").map((item) => [item.id, item.customer, item.promise_date ?? "-", money(item.promise_amount ?? item.collectible), money(item.promisedPaid), money(item.promiseShortfall)])} />; if (tab === "safe") return <><DataPanel eyebrow="SAFE TO WAIT" title="Not yet due" columns={["Invoice", "Customer", "Due date", "Outstanding"]} rows={evaluations.filter((item) => item.state === "Not due").map((item) => [item.id, item.customer, item.due, money(item.outstanding)])} /><DataPanel eyebrow="COMPLETED" title="Paid" columns={["Invoice", "Customer", "Paid amount"]} rows={evaluations.filter((item) => item.state === "Paid").map((item) => [item.id, item.customer, money(item.amount_inr)])} /> </>; if (tab === "unapplied") return <DataPanel eyebrow="RECONCILIATION" title="Unapplied receipts" columns={["Receipt", "Customer", "Amount", "Date"]} rows={receipts.filter((item) => !item.invoice_id).map((item) => [item.receipt_id, item.customer ?? "Unknown", money(item.amount), item.receipt_date ?? "Undated"])} empty="No unapplied receipts in this fixture." />; return <section className="panel full-panel"><div className="panel-title"><PanelTitle eyebrow="ACTION QUEUE" title="Priority list" subtitle="Ranked by who is most late. Disputed money stays protected." /><button className="filter-btn" onClick={onExport}><ArrowDownToLine size={15} /> Export results</button></div><div className="priority-table">{ranked.map((item, index) => <button className="priority-line" key={item.id} onClick={() => onSelect(item)}><b className="rank">{index + 1}</b><span className="customer-dot">{item.customer.slice(-1)}</span><span className="line-main"><b>{item.customer}</b><small>{item.id} · {item.daysOverdue} days overdue · {item.ageing}</small></span><span className="line-money"><b>{money(item.collectible)}</b><small>score {item.score?.toFixed(1)}</small></span><ChevronRight size={16} /></button>)}</div></section>; }
function PanelTitle({ eyebrow, title, subtitle }: { eyebrow: string; title: string; subtitle?: string }) { return <div><p className="eyebrow">{eyebrow}</p><h2>{title}</h2>{subtitle && <p className="muted">{subtitle}</p>}</div>; }
function DataPanel({ eyebrow, title, columns, rows, empty }: { eyebrow: string; title: string; columns: string[]; rows: string[][]; empty?: string }) { return <section className="panel full-panel data-panel"><PanelTitle eyebrow={eyebrow} title={title} />{rows.length ? <div className="data-table"><div className="data-row head">{columns.map((column) => <span key={column}>{column}</span>)}</div>{rows.map((row, index) => <div className="data-row" key={index}>{row.map((cell, cellIndex) => <span key={cellIndex}>{cell}</span>)}</div>)}</div> : <div className="empty-state"><Check size={22} />{empty ?? "Nothing to show in this view."}</div>}</section>; }
function InvoiceTable({ evaluations, onSelect }: { evaluations: Invoice[]; onSelect: (invoice: Invoice) => void }) { return <div className="data-table invoice-data"><div className="data-row head"><span>Invoice</span><span>Customer</span><span>Amount</span><span>Status</span><span>Due date</span></div>{evaluations.map((item) => <button className="data-row" key={item.id} onClick={() => onSelect(item)}><span><FileText size={14} /> {item.id}</span><span>{item.customer}</span><span>{money(item.outstanding)}</span><span><Status state={item.state} /></span><span>{item.due}</span></button>)}</div>; }
function Status({ state }: { state: State }) { return <span className={`status ${state.toLowerCase().replace(" ", "-")}`}><i />{state}</span>; }
function DraftPlan({ evaluations }: { evaluations: Invoice[] }) { return <section className="panel full-panel"><PanelTitle eyebrow="HUMAN REVIEW ONLY" title="Draft follow-up plan" subtitle="Template-generated messages. Every draft is labelled DRAFT - not sent." /><div className="draft-grid">{[...new Set(evaluations.map((item) => item.customer))].map((customer) => { const items = evaluations.filter((item) => item.customer === customer); const collectible = items.reduce((sum, item) => sum + item.collectible, 0); return <article className="draft-card" key={customer}><div className="draft-head"><Mail size={17} /><b>{customer}</b><span>DRAFT</span></div><h3>{collectible ? `Payment reminder: ${money(collectible)} due` : "Receivables update"}</h3><textarea defaultValue={collectible ? `Hello ${customer}, a friendly reminder regarding invoice ${items[0].id} totalling ${money(collectible)}. Could you please share the payment date?` : `We are reviewing the account for ${customer}. We will update you after the next change.`} /><div className="draft-footer"><label><input type="checkbox" /> I reviewed the exact figures</label><button onClick={() => alert("Test mode: no message was delivered")}>Approve draft</button></div><small className="draft-safe"><ShieldCheck size={13} /> DRAFT - not sent</small></article>; })}</div></section>; }
function Customers({ evaluations, agreements, onAgreement, onSelect, onToast }: { evaluations: Invoice[]; agreements: Record<string, RecoveryAgreement>; onAgreement: (agreement: RecoveryAgreement) => void; onSelect: (invoice: Invoice) => void; onToast: (message: string) => void }) { const customers = [...new Set(evaluations.map((item) => item.customer))].sort(); const [reference, setReference] = useState("100000"); const [selectedCustomer, setSelectedCustomer] = useState(customers[0] ?? ""); const items = evaluations.filter((item) => item.customer === selectedCustomer); return <><PageHeading eyebrow="HISAABSET DIRECTORY" title="Customers" subtitle="See who owes you and open their invoices." /><section className="panel full-panel"><div className="panel-title"><PanelTitle eyebrow="CUSTOMER DIRECTORY" title="Retailer evidence" subtitle="Recommendations are evidence-based only. Finance approval is required." /><label className="reference-limit">Reference purchase amount (₹)<input type="number" value={reference} onChange={(event) => setReference(event.target.value)} /></label></div><div className="customer-grid">{customers.map((customer) => { const rows = evaluations.filter((item) => item.customer === customer); const outstanding = rows.reduce((sum, item) => sum + item.outstanding, 0); const collectible = rows.reduce((sum, item) => sum + item.collectible, 0); const risk = rows.length >= 3 ? "Eligible history" : "Insufficient history"; return <button className={selectedCustomer === customer ? "customer-card selected" : "customer-card"} key={customer} onClick={() => setSelectedCustomer(customer)}><div className="customer-card-head"><span className="large-dot">{customer.slice(-1)}</span><span><b>{customer}</b><small>{rows.length} invoice{rows.length > 1 ? "s" : ""}</small></span></div><div className="customer-balance"><small>Outstanding</small><strong>{money(outstanding)}</strong></div><div className="customer-mini"><span>Collectable <b>{money(collectible)}</b></span><span>Risk <b>{risk}</b></span></div><div className="customer-card-foot"><Status state={rows[0].state} /><span>Open evidence <ChevronRight size={13} /></span></div></button>; })}</div>{customers.length === 0 && <div className="empty-state"><Users size={22} />No customers yet. Add an invoice file to begin.</div>}</section>{selectedCustomer && items.length > 0 && <RecoveryPanel customer={selectedCustomer} items={items} existing={agreements[selectedCustomer]} onSave={onAgreement} onSelect={onSelect} />}<div className="customer-reminder"><ShieldCheck size={18} /><span><b>Finance manager reminder:</b> these are evidence-based suggestions only. Review retailer history before approving any purchasing limit or credit terms. Reference suggestion: {money(Number(reference))}.</span></div><button className="export-wide" onClick={() => onToast("Customer evidence is ready for export")}><ArrowDownToLine size={15} /> Export customer evidence</button></>; }
function RecoveryPanel({ customer, items, existing, onSave, onSelect }: { customer: string; items: Invoice[]; existing?: RecoveryAgreement; onSave: (agreement: RecoveryAgreement) => void; onSelect: (invoice: Invoice) => void }) {
  const [invoiceId, setInvoiceId] = useState(existing?.invoiceId ?? items[0].id);
  const [targetType, setTargetType] = useState("exact_bep");
  const [bep, setBep] = useState(String(existing?.bep ?? ""));
  const [extra, setExtra] = useState("0");
  const [multiplier, setMultiplier] = useState("1");
  const [custom, setCustom] = useState("");
  const [floor, setFloor] = useState("");
  const [upfront, setUpfront] = useState("50");
  const [creditDays, setCreditDays] = useState("90");
  const [note, setNote] = useState(existing?.note ?? "");
  const [approval, setApproval] = useState(false);
  const [manager, setManager] = useState("");
  const [approvalNote, setApprovalNote] = useState("");
  const target = targetType === "bep_plus_amount" ? Number(bep) + Number(extra) : targetType === "bep_multiplier" ? Number(bep) * Number(multiplier) : targetType === "custom_amount" ? Number(custom) : Number(bep);
  const selected = items.find((item) => item.id === invoiceId) ?? items[0];
  const recovered = Math.max(0, selected.applied - (existing?.baseline ?? 0));
  const remaining = Math.max(0, target - recovered);
  const save = () => {
    if (!Number.isFinite(target) || target <= 0 || (target < Number(bep) && !note.trim())) return;
    onSave({ id: existing?.id ?? `AGR-${invoiceId}`, retailer: customer, invoiceId, bep: Number(bep), floor: targetType === "custom_amount" ? Number(floor || 0) : Number(bep), target, upfront: Number(upfront), credit: 100 - Number(upfront), creditDays: Number(creditDays), baseline: selected.applied, note, ...(approval && manager && approvalNote ? { approvedBy: manager, approvedAt: new Date().toISOString(), approvalNote } : {}) });
  };
  return <section className="panel recovery-panel"><div className="panel-title"><PanelTitle eyebrow="NEGOTIATED NEXT-ORDER CONDITION" title={`${customer} recovery agreement`} subtitle="Tracks recovery and suggests eligibility; it never auto-approves an order." /><Status state={remaining <= 0 ? "Paid" : "Under Review"} /></div><div className="recovery-metrics"><Fact label="Invoice amount" value={money(selected.amount_inr)} /><Fact label="Amount collected" value={money(selected.applied)} /><Fact label="Remaining target" value={money(remaining)} /><Fact label="Next order" value={remaining <= 0 ? "Eligible · approval required" : "Not yet eligible"} /></div><div className="recovery-grid"><label className="field"><span>Previous invoice</span><select value={invoiceId} onChange={(event) => setInvoiceId(event.target.value)}>{items.map((item) => <option key={item.id}>{item.id}</option>)}</select></label><label className="field"><span>Agreement target</span><select value={targetType} onChange={(event) => setTargetType(event.target.value)}><option value="exact_bep">Exactly BEP</option><option value="bep_plus_amount">BEP plus amount</option><option value="bep_multiplier">BEP multiplier</option><option value="custom_amount">Custom amount</option></select></label><Input label="Actual BEP (₹)" value={bep} onChange={setBep} type="number" />{targetType === "bep_plus_amount" && <Input label="Additional agreed amount (₹)" value={extra} onChange={setExtra} type="number" />}{targetType === "bep_multiplier" && <Input label="BEP multiplier" value={multiplier} onChange={setMultiplier} type="number" />}{targetType === "custom_amount" && <><Input label="Custom target (₹)" value={custom} onChange={setCustom} type="number" /><Input label="Minimum recovery floor (₹)" value={floor} onChange={setFloor} type="number" /></>}<Input label="Next-order upfront (%)" value={upfront} onChange={setUpfront} type="number" /><Input label="Credit period (days)" value={creditDays} onChange={setCreditDays} type="number" /></div><label className="field"><span>Negotiation note {target < Number(bep) && "(required below BEP)"}</span><textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Record who agreed and why these terms were accepted." /></label><div className="approval-row"><label className="check-row"><input type="checkbox" checked={approval} onChange={(event) => setApproval(event.target.checked)} />Finance approval recorded</label>{approval && <><Input label="Approved by" value={manager} onChange={setManager} /><Input label="Approval note" value={approvalNote} onChange={setApprovalNote} /></>}</div><div className="recovery-actions"><button className="primary-btn" onClick={save}><Check size={15} /> Save recovery agreement</button><button className="filter-btn" onClick={() => onSelect(selected)}>Open invoice detail</button></div></section>;
}
function Detail({ invoice, onClose, onSave }: { invoice: Invoice; onClose: () => void; onSave: (invoice: RawInvoice) => void }) { const [due, setDue] = useState(invoice.due); const [received, setReceived] = useState(String(invoice.received_inr)); const [disputed, setDisputed] = useState(invoice.disputed); const [disputedAmount, setDisputedAmount] = useState(String(invoice.disputed_amount ?? "")); const [cause, setCause] = useState(invoice.dispute_cause ?? ""); const [resolution, setResolution] = useState<NonNullable<RawInvoice["dispute_resolution"]>>(invoice.dispute_resolution ?? "none"); const [delivered, setDelivered] = useState(Boolean(invoice.replacement_delivered)); const [credit, setCredit] = useState(String(invoice.credit_amount ?? 0)); const [promiseMade, setPromiseMade] = useState(invoice.promise_made_date ?? ""); const [promiseDate, setPromiseDate] = useState(invoice.promise_date ?? ""); const [promiseAmount, setPromiseAmount] = useState(String(invoice.promise_amount ?? "")); return <div className="detail-overlay" onClick={onClose}><aside className="detail-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-head"><div><p className="eyebrow">INVOICE DETAIL</p><h2>{invoice.id} · {invoice.customer}</h2></div><button className="icon-btn" onClick={onClose}><X size={18} /></button></div><p className="explain">Invoice amount {money(invoice.amount_inr)}. Receipts applied {money(invoice.applied)}. Outstanding {money(invoice.outstanding)}: collectable {money(invoice.collectible)}, under review {money(invoice.review)}. Due {invoice.due}; {invoice.daysOverdue} days overdue ({invoice.ageing}).</p><div className="detail-facts"><Fact label="Amount" value={money(invoice.amount_inr)} /><Fact label="Receipts" value={money(invoice.applied)} /><Fact label="Outstanding" value={money(invoice.outstanding)} /><Fact label="Priority score" value={invoice.score?.toFixed(1) ?? "-"} /></div>{invoice.review > 0 && <div className="warning-box"><AlertTriangle size={17} /><span><b>Under review</b><small>{money(invoice.review)} is protected from collection follow-up.</small></span></div>}<div className="edit-fields"><h3>Dispute and promise review</h3><Input label="Agreed due date" value={due} onChange={setDue} type="date" /><Input label="Already received amount" value={received} onChange={setReceived} type="number" /><label className="check-row"><input type="checkbox" checked={disputed} onChange={(event) => setDisputed(event.target.checked)} />Invoice has an open dispute</label>{disputed && <><Input label="Disputed amount (optional)" value={disputedAmount} onChange={setDisputedAmount} type="number" /><label className="field"><span>Dispute cause</span><select value={cause} onChange={(event) => setCause(event.target.value)}><option value="">Choose cause</option><option value="damaged_goods">Damaged goods</option><option value="short_delivery">Short delivery</option><option value="wrong_price">Wrong price</option><option value="other">Other</option></select></label><label className="field"><span>Dispute resolution</span><select value={resolution} onChange={(event) => setResolution(event.target.value as NonNullable<RawInvoice["dispute_resolution"]>)}><option value="none">None</option><option value="pending">Pending</option><option value="replace_goods">Replace goods</option><option value="credit_note">Credit note</option></select></label>{resolution === "replace_goods" && <label className="check-row"><input type="checkbox" checked={delivered} onChange={(event) => setDelivered(event.target.checked)} />Replacement delivered</label>}{resolution === "credit_note" && <Input label="Credit amount" value={credit} onChange={setCredit} type="number" />}</>}<h3>Promise-to-pay</h3><Input label="Promise made date" value={promiseMade} onChange={setPromiseMade} type="date" /><Input label="Promise date" value={promiseDate} onChange={setPromiseDate} type="date" /><Input label="Promise amount" value={promiseAmount} onChange={setPromiseAmount} type="number" /></div><button className="primary-btn" onClick={() => { if (promiseDate && promiseMade && promiseDate < promiseMade) return; onSave({ ...invoice, due, received_inr: Number(received), disputed, disputed_amount: disputedAmount ? Number(disputedAmount) : null, dispute_cause: cause || null, dispute_resolution: resolution, replacement_delivered: delivered, credit_amount: Number(credit), promise_made_date: promiseMade || null, promise_date: promiseDate || null, promise_amount: promiseAmount ? Number(promiseAmount) : null }); }}><Check size={16} /> Save review fields</button></aside></div>; }
function Fact({ label, value }: { label: string; value: string }) { return <div><small>{label}</small><b>{value}</b></div>; }

export default App;
