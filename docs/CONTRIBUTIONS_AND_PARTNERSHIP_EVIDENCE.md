# Team Contributions and Partnership Evidence

**Challenge Track:** C28 Receivables Follow-Up Desk & Retailer Credit Decision Engine  
**Project:** Hisaabset (LedgerLoop) — *Har payment ka clear hisab*  
**Team Name:** Team Tyrants  
**Repository:** `https://github.com/MdZeeshanAli01/LedgerLoop`  
**Live URL:** `http://13.201.115.214:8501`  

---

## 1. Agreed Responsibilities & Individual Contributions Matrix

| Team Member | Role | Core Technical & Business Responsibilities | Key Commits & PRs | Concrete File Evidence |
| :--- | :--- | :--- | :--- | :--- |
| **Muhammad Khaja Zeeshan Ali** | Team Lead & Cloud Architect | • AWS ECS on Fargate 24/7 continuous deployment (`ap-south-1` Mumbai)<br/>• ECR container builds, Dockerfile multi-stage optimization<br/>• Amazon SES communication engine with in-app sandbox verification<br/>• Lead coordinator & repository maintenance | `1947a63`<br/>`e3c7b49`<br/>`e72ce14`<br/>`4bf8454` | • `deploy/aws/deploy.ps1`<br/>• `deploy/docker/Dockerfile`<br/>• `src/communications.py`<br/>• `docs/TECHNICAL_HANDOFF.md` |
| **Faiz Sayeed** | Frontend UX & AI OCR Lead | • Streamlit decision support desk layout & tab orchestration<br/>• Google Gemini 1.5 Flash multimodal AI invoice OCR extraction<br/>• PDF invoice dispute and promise capture workflows<br/>• Command center visual redesign & reactive filtering | `c735a0f`<br/>`5fea316`<br/>`57c4316`<br/>`ad1113b` | • `app/app.py`<br/>• `src/pdf_invoice.py`<br/>• `tests/test_pdf_invoice.py`<br/>• `data/source_documents/` |
| **Sai Kumar Reddy** | Financial Logic & Economics Lead | • Deterministic priority scoring math (0.45 age, 0.35 amount, 0.20 promises, >90d escalation)<br/>• SaaS pricing architecture & unit economics modeling (84% contribution margin)<br/>• 3-scenario break-even and cash-flow model in Excel<br/>• 90-test Pytest validation suite authoring | `cbf8fd5`<br/>`15fbbd0`<br/>`56581c8`<br/>`e3c7b49` | • `src/rules.py`<br/>• `src/disputes.py`<br/>• `src/payments.py`<br/>• `docs/economics.xlsx`<br/>• `tests/test_rules.py` |
| **Supporting Engineering Contributors** *(Md Rayyan, Syed Nohel, Aryan Gargava, Nikhil Dunna)* | Security, Review & Auditing | • Single-role PBKDF2-SHA256 authentication gate & session security<br/>• Independent security review & credentials sanitization<br/>• Fast-API production backend foundation & seed data | `6f4861f`<br/>`d3cb271`<br/>`197d90f`<br/>`13c7036` | • `SECURITY-REVIEW.md`<br/>• `backend/main.py`<br/>• `tests/test_auth.py` |

---

## 2. Partnership Strategy, Pitches & Negotiation Log

### 2.1 Strategic Channel Pitches: Chartered Accountants (CAs) as Distribution Arbitrage
* **Target Partner:** Local CA firms and Tax Practitioners representing wholesale distributors in trade hubs (Surat, Mumbai, Hyderabad, Ahmedabad).
* **The Pitch:** *"Your distributor clients are losing ₹15,000/mo in bank CC interest and struggling with Section 43B(h) MSME compliance. Offer them Hisaabset to automate debt prioritization and dispute ring-fencing."*
* **Negotiated Commercial Terms:**
  * **15% Lifetime Recurring Referral Commission** on paid subscriptions (or free Hisaabset Gold account for their internal practice).
  * **Co-branded Free Overdue Audit Tool:** CAs run a 5-minute receivable health-check for their clients, driving organic SaaS conversions at **CAC < ₹3,000**.

### 2.2 Accepted vs. Declined Strategic Decisions

| Decision Area | Proposed Approach | Verdict | Business Rationale & Trade-off |
| :--- | :--- | :--- | :--- |
| **Customer Acquisition** | Paid B2C / Broad Meta & Google Ads | **DECLINED** | B2C search ads yield low-intent kirana leads at CAC > ₹6,000. B2B wholesale distribution is relationship-driven; CA referrals and IndiaMART produce qualified leads at <₹3,000. |
| **Collection Channels** | Automated Robocalls & WhatsApp Spam | **DECLINED** | Distributors explicitly warned that aggressive bot calls destroy commercial goodwill with kirana buyers. Replaced with **human-in-the-loop, tone-calibrated email notices via Amazon SES**. |
| **Dispute Management** | Auto-matching unapplied receipts & balances | **DECLINED** | Silently guessing invoice-to-receipt allocations creates legal liability. Replaced with **strict dispute isolation** holding disputed funds apart while chasing uncontested cash. |
| **Product Delivery** | Multi-Branch Enterprise On-Premise Installation | **DECLINED** | Too slow to deploy and support. Standardized on **24/7 Serverless AWS ECS Fargate Web SaaS** (₹899–₹2,499/mo) with zero client-side setup. |

---

## 3. Cross-Functional Collaboration (Engineering + MBA Synthesis)

The team operated as a paired venture combining software systems engineering with business economics:
1. **From Tech Prototype to Business Defensibility:** The core Python domain engine (`src/rules.py`) was married to a defensible financial unit economics model (`docs/economics.xlsx` and `docs/BUSINESS_PRICING_AND_AWS_COST_MODEL.md`) showing an **84% contribution margin** (₹754/month per ₹899 subscriber).
2. **Deterministic Integrity:** Ensuring the financial calculations use exact Python `Decimal` arithmetic so that invoices, disputes, and receipt vouchers are legally auditable without floating-point precision loss.
3. **Reproducible Handoff:** All 90 automated tests pass in under 7 seconds, and deployment instructions are documented with single-command repeatability.
