import { useMemo, useState } from "react";
import {
  ArrowUpRight, Bell, Check, ChevronRight, CircleAlert, Clock3, Download,
  FileText, LayoutDashboard, Mail, Menu, MoreHorizontal, Search, Settings2,
  ShieldCheck, SlidersHorizontal, WalletCards, X,
} from "lucide-react";
import fixture from "../public/fixture.json";

type RawInvoice = {
  id: string; amount_inr: number; received_inr: number; due: string;
  disputed: boolean; customer: string;
};
type Invoice = RawInvoice & {
  outstanding: number; collectible: number; review: number; state: State;
  daysOverdue: number; score: number | null; ageing: string;
};
type State = "Paid" | "Under Review" | "Collectable" | "Not due";
type View = "Overview" | "Priority" | "Customers" | "Drafts";

const currency = (value: number) =>
  new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);

function evaluate(asOf: string): Invoice[] {
  const today = new Date(`${asOf}T00:00:00`);
  const raw = fixture.records.invoices as RawInvoice[];
  const collectables = raw.map((item) => Math.max(0, item.amount_inr - item.received_inr))
    .filter((value) => value > 0);
  const maxCollectable = Math.max(...collectables, 0);
  return raw.map((item) => {
    const due = new Date(`${item.due}T00:00:00`);
    const outstanding = Math.max(0, item.amount_inr - item.received_inr);
    const review = item.disputed ? outstanding : 0;
    const collectible = outstanding - review;
    const daysOverdue = Math.max(0, Math.floor((today.getTime() - due.getTime()) / 86400000));
    const state: State = outstanding === 0 ? "Paid" : review > 0 && collectible === 0
      ? "Under Review" : today <= due ? "Not due" : "Collectable";
    const ranked = state === "Collectable" && collectible > 0;
    const score = ranked ? 100 * (0.45 * Math.min(daysOverdue, 90) / 90 +
      0.35 * (collectible / maxCollectable)) : null;
    return { ...item, outstanding, collectible, review, state, daysOverdue,
      score, ageing: daysOverdue <= 0 ? "Not due" : daysOverdue <= 30 ? "1-30" :
        daysOverdue <= 60 ? "31-60" : daysOverdue <= 90 ? "61-90" : "90+" };
  }).sort((a, b) => (b.score ?? -1) - (a.score ?? -1));
}

function App() {
  const [view, setView] = useState<View>("Overview");
  const [asOf, setAsOf] = useState(fixture.records.as_of);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<Invoice | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const invoices = useMemo(() => evaluate(asOf), [asOf]);
  const filtered = invoices.filter((item) => `${item.id} ${item.customer}`.toLowerCase().includes(query.toLowerCase()));
  const total = (key: "outstanding" | "collectible" | "review") =>
    invoices.reduce((sum, item) => sum + item[key], 0);
  const priority = invoices.filter((item) => item.state === "Collectable");

  return (
    <div className="app-shell">
      <aside className={sidebarOpen ? "sidebar open" : "sidebar"}>
        <div className="brand"><div className="brand-mark">L</div><div><strong>LedgerLoop</strong><span>Receivables OS</span></div></div>
        <div className="workspace"><div className="avatar">AK</div><div><b>Arjun Kapoor</b><small>Finance lead</small></div><ChevronRight size={16} /></div>
        <nav>{(["Overview", "Priority", "Customers", "Drafts"] as View[]).map((item) => {
          const Icon = item === "Overview" ? LayoutDashboard : item === "Priority" ? SlidersHorizontal : item === "Customers" ? WalletCards : Mail;
          return <button key={item} className={view === item ? "nav-item active" : "nav-item"} onClick={() => { setView(item); setSidebarOpen(false); }}>
            <Icon size={18} /><span>{item}</span>{item === "Priority" && <em>{priority.length}</em>}
          </button>;
        })}</nav>
        <div className="sidebar-bottom"><button className="nav-item"><Settings2 size={18} /><span>Settings</span></button><div className="safe-card"><ShieldCheck size={19} /><div><b>Safe mode on</b><small>Nothing is sent automatically</small></div></div></div>
      </aside>
      <main className="main">
        <header className="topbar"><button className="mobile-menu" onClick={() => setSidebarOpen(!sidebarOpen)}><Menu /></button><div className="breadcrumbs">Workspace <ChevronRight size={14} /> <b>{view}</b></div>
          <div className="top-actions"><div className="search"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search invoices..." /></div><button className="icon-btn"><Bell size={18} /><i /></button><div className="top-avatar">AK</div></div>
        </header>
        <div className="content">
          <section className="hero"><div><p className="eyebrow">MONDAY, 16 OCTOBER 2026</p><h1>Good morning, Arjun <span>✦</span></h1><p className="hero-copy">Here’s your receivables pulse. Focus on the accounts that need attention today.</p></div><div className="date-control"><label>Data as of</label><input type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} /></div></section>
          {view === "Overview" && <Overview invoices={filtered} total={total} onSelect={setSelected} />}
          {view === "Priority" && <Priority invoices={filtered} onSelect={setSelected} />}
          {view === "Customers" && <Customers invoices={filtered} onSelect={setSelected} />}
          {view === "Drafts" && <Drafts invoices={filtered} />}
        </div>
      </main>
      {selected && <Detail invoice={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function StatCard({ label, value, sub, tone, icon }: { label: string; value: string; sub: string; tone: string; icon: React.ReactNode }) {
  return <div className={`stat-card ${tone}`}><div className="stat-head"><span>{label}</span><span className="stat-icon">{icon}</span></div><strong>{value}</strong><small>{sub}</small></div>;
}

function Overview({ invoices, total, onSelect }: { invoices: Invoice[]; total: (key: "outstanding" | "collectible" | "review") => number; onSelect: (item: Invoice) => void }) {
  const attention = invoices.filter((item) => item.state === "Collectable").slice(0, 4);
  return <><div className="stats-grid"><StatCard label="Total outstanding" value={currency(total("outstanding"))} sub="Across 6 invoices" tone="navy" icon={<WalletCards />} /><StatCard label="Ready to collect" value={currency(total("collectible"))} sub="4 invoices need follow-up" tone="teal" icon={<ArrowUpRight />} /><StatCard label="Under review" value={currency(total("review"))} sub="1 dispute needs attention" tone="amber" icon={<CircleAlert />} /><StatCard label="Recovery this month" value="₹14,000" sub="↑ 18% vs last month" tone="purple" icon={<Check />} /></div>
    <div className="section-grid"><section className="panel focus-panel"><div className="panel-title"><div><p className="eyebrow">TODAY'S FOCUS</p><h2>Collection priority</h2></div><button className="text-btn">View all <ArrowUpRight size={15} /></button></div><div className="priority-list">{attention.map((item, index) => <InvoiceRow key={item.id} item={item} rank={index + 1} onSelect={onSelect} />)}</div></section><section className="panel health-panel"><div className="panel-title"><div><p className="eyebrow">PORTFOLIO HEALTH</p><h2>Receivables at a glance</h2></div><MoreHorizontal size={19} color="#8ba0b0" /></div><div className="donut-wrap"><div className="donut"><div><b>₹46k</b><span>outstanding</span></div></div><div className="legend"><Legend color="#18a889" label="Ready to collect" value="78%" /><Legend color="#f0ae35" label="Under review" value="22%" /><Legend color="#d8e3e9" label="Paid" value="0%" /></div></div><div className="health-note"><Clock3 size={16} /><span>Average collection time is <b>18 days</b></span></div></section></div>
    <section className="panel table-panel"><div className="panel-title"><div><p className="eyebrow">ALL INVOICES</p><h2>Recent receivables</h2></div><button className="filter-btn"><Download size={15} /> Export report</button></div><InvoiceTable invoices={invoices} onSelect={onSelect} /></section></>;
}
function Legend({ color, label, value }: { color: string; label: string; value: string }) { return <div className="legend-row"><i style={{ background: color }} /><span>{label}</span><b>{value}</b></div>; }
function InvoiceRow({ item, rank, onSelect }: { item: Invoice; rank: number; onSelect: (item: Invoice) => void }) {
  return <button className="invoice-row" onClick={() => onSelect(item)}><span className="rank">{String(rank).padStart(2, "0")}</span><span className="customer-dot">{item.customer.slice(-1)}</span><span className="invoice-main"><b>{item.customer}</b><small>{item.id} · {item.daysOverdue} days overdue</small></span><span className="row-amount"><b>{currency(item.collectible)}</b><small>{item.score?.toFixed(1)} priority score</small></span><ChevronRight size={17} className="row-arrow" /></button>;
}
function InvoiceTable({ invoices, onSelect }: { invoices: Invoice[]; onSelect: (item: Invoice) => void }) {
  return <div className="invoice-table"><div className="table-row table-head"><span>INVOICE</span><span>CUSTOMER</span><span>AMOUNT</span><span>STATUS</span><span>DUE DATE</span><span /></div>{invoices.map((item) => <button className="table-row" key={item.id} onClick={() => onSelect(item)}><span className="invoice-id"><FileText size={16} />{item.id}</span><span>{item.customer}</span><b>{currency(item.outstanding)}</b><span><Status state={item.state} /></span><span>{item.due}</span><ChevronRight size={16} /></button>)}</div>;
}
function Status({ state }: { state: State }) { return <span className={`status ${state.toLowerCase().replace(" ", "-")}`}><i />{state}</span>; }
function Priority({ invoices, onSelect }: { invoices: Invoice[]; onSelect: (item: Invoice) => void }) { const rows = invoices.filter((item) => item.state === "Collectable"); return <section className="panel full-panel"><div className="panel-title"><div><p className="eyebrow">ACTION QUEUE</p><h2>Priority collection list</h2><p className="muted">Only collectible balances are ranked. Disputed money stays protected.</p></div><button className="filter-btn"><SlidersHorizontal size={15} /> Filter</button></div><div className="priority-large">{rows.map((item, index) => <InvoiceRow key={item.id} item={item} rank={index + 1} onSelect={onSelect} />)}</div></section>; }
function Customers({ invoices, onSelect }: { invoices: Invoice[]; onSelect: (item: Invoice) => void }) { const customers = Array.from(new Set(invoices.map((item) => item.customer))); return <section className="panel full-panel"><div className="panel-title"><div><p className="eyebrow">CUSTOMER PORTFOLIO</p><h2>Customer accounts</h2><p className="muted">Evidence-based view of every retailer in the current fixture.</p></div><button className="filter-btn"><Download size={15} /> Export</button></div><div className="customer-grid">{customers.map((customer) => { const rows = invoices.filter((item) => item.customer === customer); const balance = rows.reduce((sum, item) => sum + item.outstanding, 0); const item = rows[0]; return <button className="customer-card" key={customer} onClick={() => onSelect(item)}><div className="customer-card-head"><span className="large-dot">{customer.slice(-1)}</span><span><b>{customer}</b><small>{rows.length} invoice{rows.length > 1 ? "s" : ""}</small></span><MoreHorizontal size={18} /></div><div className="customer-balance"><small>Outstanding</small><strong>{currency(balance)}</strong></div><div className="customer-card-foot"><Status state={item.state} /><span>View account <ChevronRight size={14} /></span></div></button>; })}</div></section>; }
function Drafts({ invoices }: { invoices: Invoice[] }) { return <section className="panel full-panel"><div className="panel-title"><div><p className="eyebrow">REVIEW BEFORE SENDING</p><h2>Follow-up drafts</h2><p className="muted">These messages are templates only. Nothing is sent automatically.</p></div><span className="draft-badge"><ShieldCheck size={15} /> Safe mode</span></div><div className="draft-grid">{Array.from(new Set(invoices.map((item) => item.customer))).map((customer) => { const items = invoices.filter((item) => item.customer === customer); const due = items.reduce((sum, item) => sum + item.collectible, 0); return <div className="draft-card" key={customer}><div className="draft-card-head"><Mail size={18} /><b>{customer}</b><span>DRAFT</span></div><h3>{due > 0 ? `Payment reminder: ${currency(due)} due` : "Receivables update"}</h3><p>Hello {customer}, a friendly reminder regarding your open invoice. Could you please share the expected payment date?</p><div className="draft-footer"><span>DRAFT · not sent</span><button>Review draft <ChevronRight size={14} /></button></div></div>; })}</div></section>; }
function Detail({ invoice, onClose }: { invoice: Invoice; onClose: () => void }) { return <div className="detail-overlay" onClick={onClose}><aside className="detail-drawer" onClick={(event) => event.stopPropagation()}><div className="drawer-head"><div><p className="eyebrow">INVOICE DETAIL</p><h2>{invoice.id}</h2></div><button className="icon-btn" onClick={onClose}><X size={19} /></button></div><div className="detail-customer"><span className="large-dot">{invoice.customer.slice(-1)}</span><div><b>{invoice.customer}</b><small>Customer account</small></div><Status state={invoice.state} /></div><div className="detail-amount"><small>Outstanding balance</small><strong>{currency(invoice.outstanding)}</strong><span>{invoice.collectible > 0 ? `${currency(invoice.collectible)} ready to collect` : "No collectible balance"}</span></div><div className="detail-facts"><Fact label="Invoice amount" value={currency(invoice.amount_inr)} /><Fact label="Received" value={currency(invoice.received_inr)} /><Fact label="Due date" value={invoice.due} /><Fact label="Ageing" value={`${invoice.daysOverdue} days · ${invoice.ageing}`} /></div>{invoice.disputed && <div className="warning-box"><CircleAlert size={18} /><div><b>Amount under review</b><p>{currency(invoice.review)} is held due to an open dispute. This amount is not included in follow-up drafts.</p></div></div>}<div className="explanation"><p className="eyebrow">WHY THIS STATUS</p><p>Invoice amount {currency(invoice.amount_inr)} less receipts of {currency(invoice.received_inr)}. {invoice.disputed ? "The disputed balance remains visible and protected." : "The remaining balance is eligible for collection."}</p></div><button className="primary-btn">Edit invoice details</button></aside></div>; }
function Fact({ label, value }: { label: string; value: string }) { return <div><small>{label}</small><b>{value}</b></div>; }

export default App;
