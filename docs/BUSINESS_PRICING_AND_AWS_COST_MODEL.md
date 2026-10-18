# Hisaabset (LedgerLoop) — Business Pricing, AWS Cost Analysis & Subscription Model

**Project:** Hisaabset (*Har payment ka clear hisab*)  
**Live Endpoint:** `http://13.126.83.182:8501`  
**Target Market:** Indian B2B FMCG, Pharma, Hardware, and Electronics Distributors (SMBs)  
**Document Purpose:** Comprehensive cost analysis (Development, Cloud Deployment, Ongoing Maintenance), Unit Economics, and SaaS Subscription Pricing Strategy designed for MBA business case presentations, pitch decks, and investor defense.

---

## 1. Executive Summary & SaaS Value Proposition

### 1.1 The Core Business Problem (The Customer's Pain)
In traditional Indian B2B supply chains, distributors operate on razor-thin operating margins (3%–6%). A typical distributor doing ₹50 Lakhs (~$60,000) in monthly turnover faces:
- **₹10–15 Lakhs tied up in overdue receivables** (30–90+ days past due).
- **Working capital bank overdraft / Cash Credit (CC) interest:** 11%–14% per annum. Carrying ₹10 Lakhs in overdue invoices costs the distributor **₹10,000 to ₹12,000 per month in interest alone**.
- **Bad debt write-offs:** 1%–2% of gross sales (~₹25,000–₹50,000/month) written off due to unmonitored retailer defaults and disputes.
- **Manual reconciliation overhead:** 15–20 hours/week spent on calling retailers, arguing over damaged goods, and matching unapplied bank transfers.

### 1.2 The Return on Investment (ROI) Proposition
If Hisaabset costs a distributor **₹2,499/month**:
1. **Accelerates collection cycle (DSO reduction):** Collecting receivables just 7 days faster saves **₹3,000–₹5,000/month** in bank CC limit interest.
2. **Prevents 1 bad debt per quarter:** Saving a single unpaid invoice of ₹30,000 yields an annual saving of **₹1,20,000**.
3. **ROI Ratio:** For every ₹1 spent on Hisaabset, the distributor recovers **₹8 to ₹12 in preserved cash flow and saved interest**.

---

## 2. Complete Cost Breakdown: Development, Deployment & Maintenance

All AWS figures are grounded in **AWS Asia Pacific (Mumbai) `ap-south-1`** region pricing. (Conversion Rate benchmark: $1 USD ≈ ₹83.00 INR).

### 2.1 One-Time Development & Tooling Costs

| Expense Category | Tool / Service | Purpose | Cost to Team (Dev Phase) | Cost to Scale (Production) |
| :--- | :--- | :--- | :--- | :--- |
| **Development Machine** | Local Windows/Linux Workstation | Code development, container builds | $0 (Existing asset) | $0 |
| **Code Versioning** | **GitHub** (Free Tier / Public Repo) | Git VCS, remote branch synchronization | **$0.00** | Free tier is sufficient; Team tier ($4/user/mo) for private repos |
| **Container Engine** | **Docker Desktop** | Local multi-stage container build & testing | **$0.00** (Free for SMB/Open Source) | $0 |
| **Runtime & Libraries** | Python 3.14, Streamlit, Pandas, Pytest | Core logic, PDF extraction, UI, test suite | **$0.00** (Open-source MIT/Apache) | $0 |
| **OCR & LLM Extraction** | **Google Gemini 1.5 Flash API** | Intelligent bill extraction (PDF/Images) | **$0.00** (Free Tier: 15 req/min) | Pay-as-you-go (~₹0.012 per invoice) |
| **Local PDF Parsing** | `pdfplumber` & `pypdf` | Zero-cost deterministic PDF text extraction | **$0.00** | **$0.00** |
| **Total One-Time Dev Cost** | — | — | **$0.00 (₹0)** | **Negligible** |

---

### 2.2 Live AWS Cloud Deployment & Infrastructure Costs (COGS)

Here is the exact monthly cost to run the containerized cloud application on AWS Fargate in Mumbai (`ap-south-1`):

```
+--------------------------------------------------------------------------------------------------+
|                            AWS CLOUD INFRASTRUCTURE RUNNING COSTS                                |
+-------------------------------+--------------------------+---------------------+-----------------+
| AWS Service Component         | Dimension / Sizing       | Monthly Cost (USD)  | Monthly Cost (INR)|
+-------------------------------+--------------------------+---------------------+-----------------+
| AWS ECS on Fargate (vCPU)     | 0.5 vCPU x 730 hours/mo  | $14.77              | ₹1,226          |
|                               | ($0.04048 per vCPU-hr)   |                     |                 |
| AWS ECS on Fargate (Memory)   | 1.0 GB RAM x 730 hrs/mo  | $3.24               | ₹269            |
|                               | ($0.004445 per GB-hr)    |                     |                 |
| Amazon ECR (Container Storage)| ~150 MB image (Free 500MB| $0.00               | ₹0              |
|                               | then $0.10/GB/mo)        |                     |                 |
| Amazon SES (Transactional)    | 5,000 reminder emails/mo | $0.50               | ₹42             |
|                               | ($0.10 per 1,000 emails) |                     |                 |
| Amazon CloudWatch Logs        | Ingestion < 5 GB/mo      | $0.00               | ₹0 (Free Tier)  |
|                               | ($0.50/GB after 5 GB)    |                     |                 |
| AWS VPC & Data Transfer Out   | Egress < 100 GB/mo       | $0.00               | ₹0 (Free Tier)  |
|                               | (100 GB/mo free internet)|                     |                 |
| Public IP / ENI               | IPv4 attached to Fargate | $3.65               | ₹303            |
|                               | ($0.005/hr x 730 hrs)    |                     |                 |
+-------------------------------+--------------------------+---------------------+-----------------+
| BASE CLOUD RUNTIME TOTAL      | Single 24/7 Production   | $22.16 / month      | ₹1,840 / month  |
+-------------------------------+--------------------------+---------------------+-----------------+
```

#### Multi-Tenant Capacity of Base Pod:
- A single 0.5 vCPU / 1 GB Fargate task comfortably serves **15 to 25 simultaneous active distributor sessions** (or **50–80 registered distributor businesses**, since distributors access the portal in morning and evening batches).
- **Baseline Cloud Cost per Distributor:** At 30 distributors sharing a base instance:  
  $$\text{Hosting Cost per Tenant} = \frac{₹1,840}{30} = \mathbf{₹61.33 \text{ / month}} \quad (\approx \$0.74)$$

---

### 2.3 Ongoing Maintenance & Auxiliary Services

| Service / Item | Usage & Frequency | Monthly Cost (USD) | Monthly Cost (INR) |
| :--- | :--- | :--- | :--- |
| **Domain Name (e.g., hisaabset.in)** | Annual renewal (~₹800/year amortized) | $0.80 / mo | ₹66 / mo |
| **DNS Management (AWS Route 53)** | 1 Hosted Zone ($0.50/mo) | $0.50 / mo | ₹42 / mo |
| **SSL / TLS Certificate** | AWS Certificate Manager (ACM) | $0.00 (Free with AWS ALB/CloudFront) | ₹0 |
| **AI Bill Extraction (Gemini Flash)**| 1,000 invoices/month @ $0.075/1M input | $0.15 / mo | ₹12 / mo |
| **Payment Gateway Integration** | UPI QR (0% MDR) / Razorpay Link (2% on card) | Pass-through / 0 fixed fee | ₹0 fixed |
| **WhatsApp Business API (Optional)** | Meta Cloud API (1,000 service convs/mo free)| $0.00 – $5.00 / mo | ₹0 – ₹415 / mo |
| **Total Auxiliary Services** | — | **~$2.50 – $7.50 / mo** | **₹200 – ₹620 / mo** |

---

## 3. Total Cost of Ownership (TCO) & Unit Economics

### 3.1 Total Monthly Operational Cost (Baseline Scale: 1–50 Distributors)

$$\begin{aligned}
\text{Total Monthly COGS} &= \text{ECS Fargate} + \text{Public IPv4} + \text{SES} + \text{Route 53} + \text{AI Tokens} + \text{Domain} \\
&= \$18.01 + \$3.65 + \$0.50 + \$0.50 + \$0.15 + \$0.80 \\
&= \mathbf{\$23.61 \text{ / month}} \quad (\approx \mathbf{₹1,960 \text{ / month}})
\end{aligned}$$

### 3.2 Unit Economics (Cost per Invoice & Cost per Customer)

| Metric | Calculation | Unit Cost |
| :--- | :--- | :--- |
| **Cost per Invoice Processed (OCR + Math)** | AI API Tokens (~1,500 tokens) + CPU time | **₹0.025 per invoice** ($0.0003) |
| **Cost per Email Notification (Amazon SES)**| $0.10 per 1,000 emails | **₹0.008 per email** ($0.0001) |
| **Total Marginal Cost per Active Distributor** | 200 bills + 50 emails + amortized hosting | **₹75 to ₹95 per month** (~$0.90 - $1.15) |

> **Key Takeaway for Evaluators:**  
> The marginal cost of serving an additional distributor is less than **₹100/month**. This allows Hisaabset to price its subscription at standard SaaS price points while maintaining **Gross Margins above 88%–95%**.

---

## 4. Proposed Subscription Pricing Model for Distributors

To capture maximum value across varied business sizes, we implement a **Three-Tier SaaS Subscription Model** with monthly and annual billing (2 months free for annual upfront commitment to boost upfront cash flows).

```
┌───────────────────────────┐    ┌───────────────────────────┐    ┌───────────────────────────┐
│     CHHOTA VYAPAR         │    │      VYAPAR PRO ⭐        │    │       MAHA VYAPAR         │
│       (Starter)           │    │    (Most Popular)         │    │      (Enterprise)         │
├───────────────────────────┤    ├───────────────────────────┤    ├───────────────────────────┤
│ ₹999 / month              │    │ ₹2,499 / month            │    │ ₹6,999 / month            │
│ (₹9,999 / year billed)    │    │ (₹24,999 / year billed)   │    │ (₹69,999 / year billed)   │
├───────────────────────────┤    ├───────────────────────────┤    ├───────────────────────────┤
│ • Up to 100 Invoices/mo   │    │ • Up to 600 Invoices/mo   │    │ • Unlimited Invoices      │
│ • Up to 50 Retailers      │    │ • Up to 250 Retailers     │    │ • Unlimited Retailers     │
│ • Ageing Analysis Ledger  │    │ • AI Bill Extraction (OCR)│    │ • Multi-Warehouse/Branches│
│ • Priority Scoring Queue  │    │ • Dispute Split & Review  │    │ • Negotiated Recovery BEP │
│ • UPI Payment QR Links    │    │ • SES Email Reminders     │    │ • Tally / Marg ERP Export │
│ • 1 Finance Lead Login    │    │ • 0-100 Credit Risk Score │    │ • Dedicated Relationship  │
│                           │    │ • 1 Finance Lead Login    │    │   Manager + SLA Support   │
├───────────────────────────┤    ├───────────────────────────┤    ├───────────────────────────┤
│ Gross Margin: 90.5%       │    │ Gross Margin: 96.2%       │    │ Gross Margin: 97.8%       │
└───────────────────────────┘    └───────────────────────────┘    └───────────────────────────┘
```

### 4.1 Detailed Tier Breakdown

#### Tier 1: Chhota Vyapar (Starter)
- **Target Audience:** Micro-distributors and local sub-stockists operating 1 van or 1 delivery route (up to 50 retail shops).
- **Price:** **₹999 / month** (or ₹9,999 / year).
- **Core Value:** Replaces manual paper registers; gives clear ageing buckets (0–15, 16–30, 31–60, 60+) and daily follow-up priority list.
- **Gross Profit per Customer:** ₹999 − ₹95 (hosting/unit cost) = **₹904 / month (90.5% margin)**.

#### Tier 2: Vyapar Pro (Growth / Recommended)
- **Target Audience:** Standard FMCG, Pharma, and Consumer Goods distributors (100–300 retail counters).
- **Price:** **₹2,499 / month** (or ₹24,999 / year).
- **Core Value:** Automates invoice intake via OCR, splits damaged goods disputes (`review_amount`), generates dynamic payment links, computes 0–100 retailer credit risk scores, and sends email reminders via AWS SES.
- **Gross Profit per Customer:** ₹2,499 − ₹95 = **₹2,404 / month (96.2% margin)**.

#### Tier 3: Maha Vyapar (Enterprise & C&F Agents)
- **Target Audience:** Large multi-brand distributors, C&F (Carrying & Forwarding) agents, and multi-depot wholesalers managing 500+ counters.
- **Price:** **₹6,999 / month** (or ₹69,999 / year).
- **Core Value:** Complete risk scoring, negotiated next-order recovery agreements with baseline isolation, multi-branch support, and direct Tally/Marg export.
- **Gross Profit per Customer:** ₹6,999 − ₹150 = **₹6,849 / month (97.8% margin)**.

---

## 5. Financial Projections & P&L Model (Year 1 to Year 3)

### 5.1 Projected Customer Acquisition & Revenue Trajectory

| Metric | Month 3 | Month 6 | Year 1 (M12) | Year 2 (M24) | Year 3 (M36) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Active Paid Customers** | 15 | 45 | 120 | 400 | 1,200 |
| - *Starter (₹999)* | 5 | 15 | 35 | 100 | 250 |
| - *Pro (₹2,499)* | 9 | 26 | 75 | 260 | 800 |
| - *Enterprise (₹6,999)* | 1 | 4 | 10 | 40 | 150 |
| **Monthly Recurring Revenue (MRR)** | **₹34,486** | **₹1,07,955** | **₹2,92,455** | **₹10,29,600** | **₹32,98,250** |
| **Annual Run Rate (ARR)** | ₹4.14 Lakhs | ₹12.95 Lakhs | **₹35.09 Lakhs** | **₹1.23 Crores** | **₹3.95 Crores** |
| **Monthly AWS & Cloud COGS** | ₹1,960 | ₹2,800 | ₹7,500 | ₹24,000 | ₹70,000 |
| **Gross Profit Margin** | **94.3%** | **97.4%** | **97.4%** | **97.7%** | **97.9%** |

### 5.2 Unit Economics: LTV to CAC Analysis

```
                                 SAAS UNIT HEALTH METRICS
                 ┌────────────────────────────────────────────────────────┐
                 │ Customer Acquisition Cost (CAC):       ₹2,500          │
                 │ (Direct sales, trade associations, FMCG dealer hubs)   │
                 │                                                        │
                 │ Average Monthly ARPU (Blended):        ₹2,437 / mo     │
                 │ Gross Margin:                          97.4%           │
                 │ Average Customer Lifetime:             24 months       │
                 │                                                        │
                 │ Customer Lifetime Value (LTV):         ₹57,000         │
                 │                                                        │
                 │ LTV : CAC RATIO:                       22.8x           │
                 │ (Global SaaS Benchmark > 3.0x)                         │
                 │                                                        │
                 │ Payback Period:                        1.05 months     │
                 └────────────────────────────────────────────────────────┘
```

---

## 6. MBA Presentation Defense: Judges' Tough Q&A

### Q1: "Why would an Indian distributor pay ₹2,499/month for this when they already use Tally or Marg?"
> **Answer:**  
> "Tally and Marg are static *recording* systems—they tell you what happened in the past. They do not tell you who to call today, nor do they separate damaged-goods disputes from collectable debt. Tally treats a ₹50,000 invoice with ₹10,000 of broken stock as a delinquent customer. Hisaabset is an *active decision-support layer* that sits on top of Tally: it isolates the ₹10,000 dispute, prioritizes the ₹40,000 collectable portion, generates dynamic payment links, and enforces BEP recovery rules. If Hisaabset prevents just one bad debt of ₹25,000 per year or saves 7 days of interest on a ₹10 Lakh CC limit, it pays for itself 5 times over."

### Q2: "What happens to your cloud costs if your user base grows from 50 to 5,000 distributors?"
> **Answer:**  
> "Our architecture scales with sub-linear cost growth:
> 1. Streamlit and Python logic run on AWS ECS Fargate with container auto-scaling.
> 2. Because distributors use the software in short bursts (morning dispatch and evening tallying), average CPU utilization is low.
> 3. Serving 5,000 distributors requires approximately 8–10 Fargate tasks behind an AWS Application Load Balancer (ALB), costing ~$280–$350/month (₹25,000–₹30,000/month).
> 4. Meanwhile, 5,000 distributors at an average ARPU of ₹2,400 generate **₹1.20 Crores in monthly revenue**. Cloud infrastructure remains **under 0.3% of top-line revenue**."

### Q3: "Why not use a usage-based pricing model (e.g., ₹2 per invoice) instead of fixed monthly subscriptions?"
> **Answer:**  
> "In Indian SMB retail, usage-based pricing introduces hesitation: distributors would avoid entering invoices to save ₹2, compromising data integrity. A predictable flat subscription (₹999 or ₹2,499) fits into their fixed monthly operating budget, encourages full usage, and gives our business highly predictable Monthly Recurring Revenue (MRR) with upfront annual cash collection."

### Q4: "How do you defend against customer churn?"
> **Answer:**  
> "Hisaabset creates two powerful structural moats:
> 1. **Historical Repayment Memory:** Over time, the platform accumulates proprietary 0–100 retailer credit risk scores and promise-keeping track records that exist nowhere else. Churning means losing this credit intelligence.
> 2. **Baseline Recovery Contracts:** Active next-order recovery agreements lock retailers into clear repayment schedules that distributors rely on to release fresh goods safely."

---

## 7. Slide-by-Slide Presentation Cheat Sheet (For MBA Pitch)

| Slide # | Slide Title | Key Numbers to Call Out |
| :--- | :--- | :--- |
| **Slide 1** | **The Problem** | ₹15 Lakhs locked in receivables per distributor; 12% CC interest burden; ₹30,000 bad debt/mo. |
| **Slide 2** | **The Solution** | Hisaabset: Dispute splitting + Dynamic priority scoring + Automated payment follow-up. |
| **Slide 3** | **Cloud Architecture** | AWS ECS Fargate + ECR + SES (ap-south-1 Mumbai) — Serverless, secure, non-root user. |
| **Slide 4** | **Infrastructure Cost** | **$22.16 / month (~₹1,840/mo)** base cloud cost; only **₹0.025 per invoice** processing cost. |
| **Slide 5** | **Subscription Pricing**| Starter: **₹999/mo** · Pro: **₹2,499/mo** · Enterprise: **₹6,999/mo** (>90% Gross Margin). |
| **Slide 6** | **Unit Economics** | CAC: ₹2,500 · LTV: ₹57,000 · **LTV:CAC = 22.8x** · Payback period = 1.05 months. |
| **Slide 7** | **Customer ROI** | 1 bad debt prevented = ₹30,000 saved = **12x annual subscription ROI**. |
