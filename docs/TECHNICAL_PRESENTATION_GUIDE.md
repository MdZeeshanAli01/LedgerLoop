# Hisaabset (LedgerLoop) — Technical Architecture & Presentation Defense Guide

**Project Name:** Hisaabset (*Har payment ka clear hisab*)  
**Repository:** `https://github.com/MdZeeshanAli01/LedgerLoop.git`  
**Live Application URL:** `http://13.126.83.182:8501`  
**Document Purpose:** Complete technical reference, architectural defense, and Q&A handbook for technical evaluators, hackathon judges, and architecture reviews.

---

## 1. Executive Summary & Problem Engineering

### The Problem
In Indian B2B distributor-to-retailer commerce (*kiranas*, local electronics/pharma stores), distributors face recurring working capital bottlenecks. Standard accounting software (like Tally, Marg, or Zoho) treats every unpaid invoice as a delinquent debt. In reality:
- **Operational friction is not delinquency:** Deliveries often contain damaged cartons or short quantities, locking balances in operational disputes.
- **Premature follow-up destroys customer relationships:** Chasing a retailer who made a payment commitment or is waiting for replacement inventory creates mistrust.
- **Unapplied payments cause confusion:** Retailers frequently send lump-sum bank transfers without specifying invoice numbers.
- **Credit allocation is guesswork:** Distributors lack data-driven purchasing limits and upfront/credit terms.

### The Hisaabset Solution
Hisaabset is a **cloud-native, evidence-first decision-support platform** that:
1. Normalizes heterogenous incoming data (JSON, CSV, computer-generated PDFs).
2. Uses exact fixed-point `Decimal` arithmetic (`0.01` quantum) to eliminate floating-point drift.
3. Separates every invoice balance into `collectable_amount` (safe to chase) and `review_amount` (held for investigation).
4. Dynamically evaluates payment promises, ageing buckets, and tie-broken priority scores.
5. Computes transparent 0–100 retailer credit risk scores and suggests commercial terms.
6. Enforces Break-Even Point (BEP) guarded recovery agreements for repeat orders.
7. Deploys as a containerized microservice on **AWS ECS Fargate** with zero server management overhead.

---

## 2. Complete Technology Stack & Justification

| Layer | Technology | Why We Used It (Technical Rationale) |
| :--- | :--- | :--- |
| **User Interface & Presentation** | **Streamlit** (v1.66) | Allows rapid, stateful, reactive UI development in pure Python. Eliminates REST API glue code while providing real-time data filtering, dynamic metric cards, and responsive dataframes. Custom-styled with a high-contrast theme for non-technical finance leads. |
| **Core Calculation Engine** | **Python 3.14** | Modern, high-performance runtime. Leverages `dataclasses` (including `frozen=True` for immutability), `StrEnum`, strict type hinting, and the native `decimal` module for zero-error financial calculations. |
| **Data Manipulation** | **Pandas** (v3.0) | High-performance in-memory tabular manipulation for invoice rendering, CSV exports, multi-field filtering, and aggregation. |
| **PDF Extraction** | **pdfplumber** & **pypdf** | Hybrid extraction strategy: `pdfplumber` preserves complex invoice visual layouts and tables; falls back gracefully to `pypdf`. Safe lazy loading prevents module crashes if binaries are missing. |
| **Test Framework** | **Pytest** (v9.1) | Industry standard test runner. Drives 79 test cases spanning unit, integration, edge-case, and end-to-end regression runs. |
| **Containerization** | **Docker** (Multi-stage/Slim) | Containerizes the app using `python:3.14-slim`. Enforces reproducible environments across Windows development and AWS Linux production. Runs as a non-root user (`appuser`, UID 10001) for security hardening. |
| **Cloud Hosting & Runtime** | **AWS ECS on Fargate** | Serverless container execution. Eliminates EC2 instance provisioning, OS patching, and capacity planning. Automatic health checks via `/_stcore/health`. |
| **Container Registry** | **Amazon ECR** | Private, secure, encrypted Docker registry with native IAM authentication, tightly integrated into ECS for fast image pulling. |
| **Networking & Security** | **AWS VPC & Security Groups** | Virtual private cloud isolation with custom security groups restricting inbound traffic strictly to the Streamlit port (`8501`). |
| **Identity & Access** | **AWS IAM** | Strict Principle of Least Privilege: separates `ecsTaskExecutionRole` (infrastructure lifecycle) from `HisaabsetEcsTaskRole` (application runtime permissions). Zero hardcoded secrets. |
| **Observability** | **Amazon CloudWatch Logs** | Centralized stdout/stderr container log streaming (`/ecs/hisaabset`) enabling real-time monitoring and post-mortem debugging. |
| **Communication Gateway** | **Amazon SES** (Boto3) | High-deliverability transactional email service. Gated behind a human-in-the-loop review checkbox and an environment-level test safety flag. |

---

## 3. Detailed AWS Cloud Architecture

```
                       [ User / Browser ]
                               │
                        Port 8501 (HTTP)
                               │
                               ▼
        ┌────────────────────────────────────────────────────────┐
        │  AWS Cloud (Region: ap-south-1 Mumbai)                 │
        │                                                        │
        │   ┌────────────────────────────────────────────────┐   │
        │   │ AWS VPC (Default VPC / Public Subnets)         │   │
        │   │                                                │   │
        │   │   Security Group: hisaabset-sg                 │   │
        │   │   [ Inbound: TCP 8501 from 0.0.0.0/0 ]         │   │
        │   │                                                │   │
        │   │   ┌────────────────────────────────────────┐   │   │
        │   │   │ ECS Cluster: hisaabset-cluster         │   │   │
        │   │   │                                        │   │   │
        │   │   │   Fargate Service: hisaabset-service   │   │   │
        │   │   │   ┌────────────────────────────────┐   │   │   │
        │   │   │   │ Task: hisaabset:1              │   │   │   │
        │   │   │   │ (512 CPU / 1024 MiB Memory)    │   │   │   │
        │   │   │   │                                │   │   │   │
        │   │   │   │   Container: hisaabset         │   │   │   │
        │   │   │   │   - Non-root user (UID 10001)  │   │   │   │
        │   │   │   │   - Health: /_stcore/health    │   │   │   │
        │   │   │   └────────────────┬───────────────┘   │   │   │
        │   │   └────────────────────┼───────────────────┘   │   │
        │   └────────────────────────┼───────────────────────┘   │
        │                            │                           │
        │         Pulls Image        │ Streams Logs              │
        │              ▼             │                           │
        │      ┌──────────────┐      │     ┌───────────────────┐ │
        │      │  Amazon ECR  │      └────►│ Amazon CloudWatch │ │
        │      │  (hisaabset) │            │  (/ecs/hisaabset) │ │
        │      └──────────────┘            └───────────────────┘ │
        │                                                        │
        │      ┌─────────────────────────┐                       │
        │      │ Amazon SES (ap-south-1) │◄── Only on human      │
        │      │ [Verified Identities]   │    review approval    │
        │      └─────────────────────────┘                       │
        └────────────────────────────────────────────────────────┘
```

### Deep Dive into Every AWS Service Used

#### 1. Amazon Elastic Container Registry (ECR)
- **What it is:** A fully managed, highly available private Docker container registry.
- **Why we used it:** Securely hosts the `hisaabset:v1` Docker image. Avoids exposing proprietary business logic on public Docker Hub.
- **How it works:** Authenticates via `aws ecr get-login-password`, allowing Docker CLI to push directly from PowerShell.

#### 2. Amazon Elastic Container Service (ECS) with AWS Fargate
- **What it is:** A fully managed container orchestration platform running on serverless compute.
- **Why Fargate instead of EC2?**
  - **Zero Server Management:** No need to patch Linux AMIs, configure SSH keys, or manage EC2 instances.
  - **Cost-Efficiency:** You only pay for the exact vCPU (0.5 vCPU = 512 units) and Memory (1 GB = 1024 MiB) consumed while the container runs.
  - **Instant Elasticity & Fast Restarts:** Fargate automatically provisions isolated micro-VMs per task.

#### 3. AWS Identity and Access Management (IAM)
- **What it is:** The control plane for authentication and authorization across AWS.
- **Dual-Role Security Architecture:**
  1. **`ecsTaskExecutionRole` (Infrastructure Role):** Grants the ECS agent permission to pull container images from ECR and stream logs to CloudWatch.
  2. **`HisaabsetEcsTaskRole` (Application Role):** Grants the running Python container only the permissions it needs. Specifically, it has an inline policy (`hisaabset-ses-task-policy.json`) restricted to:
     ```json
     {
       "Effect": "Allow",
       "Action": ["ses:SendEmail", "ses:SendRawEmail"],
       "Resource": "*",
       "Condition": { "StringEquals": { "ses:FromAddress": "unnamedinsect424@gmail.com" } }
     }
     ```
- **Trust Policy (`ecs-tasks.amazonaws.com`):** Configured so that only the ECS task service principal can assume this role. Zero credentials exist inside source code or container environment variables.

#### 4. Amazon CloudWatch Logs
- **What it is:** Real-time log monitoring and aggregation.
- **Why we used it:** Container filesystems are ephemeral. CloudWatch log group `/ecs/hisaabset` captures all Streamlit access logs, unhandled exceptions, and diagnostic traces permanently.

#### 5. Virtual Private Cloud (VPC), Subnets, and Security Groups
- **What it is:** Virtual networking layer.
- **Security Rule:** A dedicated security group (`hisaabset-sg`) blocks all ports except `8501` (TCP), preventing unauthorized administrative access (e.g., blocking SSH port 22).

#### 6. Amazon Simple Email Service (SES)
- **What it is:** Cloud email gateway.
- **Why we used it:** Prepares professional email follow-ups with exact collectible balances.
- **Safety Gating:** Starts in `HISAABSET_EMAIL_TEST_MODE=true` by default so accidental sends during development are impossible.

---

## 4. Key Mathematical & Algorithmic Models

### A. The 3-Tier Priority Scoring Formula
To determine who to follow up with first, collectible invoices are scored on a scale from 0 to 100:

$$\text{Base Score} = 100 \times \left( 0.45 \cdot S_{\text{age}} + 0.35 \cdot S_{\text{amount}} + 0.20 \cdot S_{\text{promise}} \right)$$

1. **Age Score ($S_{\text{age}}$):** Normalized over a 90-day cap: $\min(\text{Days Overdue}, 90) / 90$.
2. **Amount Score ($S_{\text{amount}}$):** Normalized against the maximum collectible invoice in the current batch: $\text{Collectable} / \max(\text{Collectables})$.
3. **Promise Shortfall ($S_{\text{promise}}$):** If a customer made a commitment and broke it, their score spikes proportionally to the unpaid shortfall: $\text{Shortfall} / \text{Promised Amount}$.

**Non-Linear Escalation Curve ($>90$ Days):**  
Standard linear models fail when debt gets very old. After 90 days, debt risk accelerates exponentially. We apply an escalation multiplier $E$:
$$E = 0.25 + 0.50 \cdot \min\left(\frac{\text{Days Overdue} - 90}{90}, 1.0\right)$$
$$\text{Final Score} = \text{Base} + (100 - \text{Base}) \times E$$

**Deterministic Tie-Breaking:**  
`Priority Score (desc) → Days Overdue (desc) → Collectable Amount (desc) → Invoice ID (asc)`.

---

### B. Dispute Balance Splitting State Matrix

$$\text{Outstanding} = \max(0, \text{Amount} - \text{Applied Receipts} - \text{Credit Applied})$$

| Dispute Resolution | Replacement Delivered? | Held Under Review (`review_amount`) | Safe to Follow-up (`collectable_amount`) |
| :--- | :---: | :---: | :---: |
| **None / No Dispute** | N/A | ₹0.00 | Full Outstanding |
| **Pending Investigation** | N/A | Disputed Portion | Outstanding − Disputed |
| **Replace Goods** | **False** (Pending) | Disputed Portion | Outstanding − Disputed |
| **Replace Goods** | **True** (Delivered) | ₹0.00 | Full Outstanding |
| **Credit Note** | N/A | ₹0.00 (Credit applied) | Outstanding after credit |

---

### C. 0–100 Retailer Credit Risk Model

Retailers are evaluated across 5 objective historical dimensions:
1. **Lateness Ratio (Max 35 pts):** Proportion of completed invoices paid after due date.
2. **Lateness Severity (Max 25 pts):** Average days late, normalized over 90 days.
3. **Exposure Ratio (Max 15 pts):** Outstanding balance relative to total lifetime billing.
4. **Reliability Index (Max 15 pts):** Broken promise frequency.
5. **Complaint Record (Max 10 pts):** Verified retailer-fault complaints (5 pts each).

> **Safe Default Rule:** Retailers with fewer than 3 completed invoices are assigned **"Insufficient history"** and default to standard **50% Upfront / 50% Credit** terms. Unproven accounts cannot receive high credit limits.

---

### D. Next-Order Negotiated Recovery (BEP Protection)

When an indebted retailer needs new stock, Hisaabset structures a structured recovery plan:
- **Break-Even Point (BEP):** Minimum recovery floor ensuring goods are never sold below distributor cost.
- **Baseline Isolation Principle:** Payments made *prior* to the agreement date are recorded in `baseline_collected` and **strictly excluded** from satisfying the newly negotiated target.
- **Next-Order Eligibility:** The retailer is marked eligible for new dispatches only once post-agreement collections $\ge$ agreed target, and requires human finance manager sign-off.

---

## 5. Security & Defensive Engineering Highlights

1. **Zero Hardcoded Secrets:** AWS credentials, database strings, and API keys are completely absent from git history and container layers. Authentication relies entirely on IAM role assumption.
2. **Human-in-the-Loop Review:** Draft messages cannot be sent automatically. The UI disables sending until the finance manager explicitly checks: *"I reviewed the exact figures and approve this email"*.
3. **Fixed-Point Decimal Math:** Standard IEEE-754 binary floats (`0.1 + 0.2 = 0.30000000000000004`) cause cumulative penny rounding errors. All calculations use `decimal.Decimal` with `ROUND_HALF_UP` to `Decimal('0.01')`.
4. **Audit Trail Generation:** Every evaluation run produces reproducible export bundles: `result.json`, `result.csv`, `negotiated_recovery.json`, and `evidence_log.md`.

---

## 6. Anticipated Presentation Questions & Winning Answers

### Architecture & AWS Questions

#### Q1: "Why did you choose Streamlit instead of a separate React frontend and FastAPI backend?"
> **Answer:**  
> "Our target user is a small distributor's finance lead, not an API consumer. Streamlit allowed us to build a reactive, single-page decision desk with real-time session state without the latency, serialization overhead, or state synchronization bugs of a decoupled REST architecture. The underlying business rules are decoupled pure Python dataclasses and functions in `src/`, meaning we can plug in a React or mobile frontend in the future without changing a single line of calculation logic."

#### Q2: "Why deploy on AWS ECS Fargate rather than a simple EC2 instance or AWS Lambda?"
> **Answer:**  
> "Streamlit is a stateful, WebSocket-driven application. AWS Lambda is designed for short, stateless HTTP request-response cycles and causes WebSocket disconnects and cold-start delays. A traditional EC2 instance would require manual Linux patching, capacity provisioning, and 24/7 idle server costs. ECS Fargate provides the best of both worlds: dedicated serverless container execution with automated health checks, zero host maintenance, and sub-minute scaling."

#### Q3: "How do you handle security and credentials in the cloud?"
> **Answer:**  
> "We follow AWS Well-Architected Security Pillars:
> 1. We run the container as an unprivileged, non-root user (`appuser`, UID 10001).
> 2. Zero access keys or passwords are stored in code or environment variables.
> 3. We use IAM Task Roles (`HisaabsetEcsTaskRole`) with least-privilege scoping, permitting only SES sends from our verified business domain.
> 4. Inbound traffic is firewalled by a security group allowing traffic only on port 8501."

---

### Algorithm & Business Logic Questions

#### Q4: "How does your priority scoring prevent old, small invoices from burying large, fresh debts?"
> **Answer:**  
> "We use a multi-factor weighted formula with 45% weight on age, 35% on amount, and 20% on broken promises. Amount is normalized against the maximum collectible invoice in the batch. For invoices past 90 days, we apply an escalation factor that boosts urgency, ensuring uncollected debt doesn't stagnate while keeping large overdue balances at the top of the queue."

#### Q5: "What prevents the application from chasing a customer who received damaged goods?"
> **Answer:**  
> "Our dispute splitting algorithm in `src/disputes.py`. If an invoice has an open dispute or replacement goods pending delivery, the disputed balance is held in `review_amount`. The customer follow-up queue only looks at `collectable_amount`. Furthermore, our draft templates explicitly state: *'We are separately reviewing ₹X on your invoice and are not asking for that amount today'*, preserving customer trust."

#### Q6: "Why do you have a 3-invoice threshold for retailer risk rating?"
> **Answer:**  
> "In credit underwriting, lack of negative data is not evidence of good credit. A new retailer with 1 on-time payment should not receive a top-tier credit limit. Assigning 'Insufficient history' protects the distributor's working capital by enforcing a standard 50% upfront payment term until a track record is established."

#### Q7: "What is the 'Baseline Isolation Principle' in your negotiated recovery model?"
> **Answer:**  
> "When a distributor agrees to a recovery target for an old bill (e.g., recover ₹20,000 before dispatching the next order), payments made *before* the agreement cannot be retroactively credited toward that new target. Hisaabset locks `baseline_collected` at agreement creation, ensuring only fresh cash collections unlock next-order eligibility."

---

## 7. Single-Role Authentication Architecture & Navigation Flow

### Single Role Principle
Per business operational specifications, Hisaabset is intentionally architected with **only one authorized role**: **Finance Lead** (`admin` / Zeeshan Ali).
- **Rationale:** Small-to-medium Indian distributor firms do not have multi-tiered finance departments with disjoint roles. The business owner or designated Finance Lead oversees the entire ledger, invoice intake, customer communication, and dispute adjudication. Enforcing a single authorized role eliminates RBAC complexity, session switching errors, and accidental privilege escalation.
- **Authorized Identity:**
  - **Role:** `Finance Lead`
  - **Authorized User:** `Zeeshan Ali` (`admin` or `finance` or `sszeeshu@gmail.com`)
  - **Default Credentials:** `admin` / `hisaabset123`

### Page-to-Page Navigation Flow

```
                      ┌────────────────────────────┐
                      │    Public Browser Entry    │
                      └──────────────┬─────────────┘
                                     │
                                     ▼
                      ┌────────────────────────────┐
                      │   1. Emerald Login Gate    │
                      │   - Username & Password    │
                      │   - 1-Click Quick Demo     │
                      └──────────────┬─────────────┘
                                     │ Authenticated
                                     ▼
                      ┌────────────────────────────┐
                      │  Authenticated App Shell   │
                      │  - Profile: Zeeshan Ali    │
                      │  - Role: Finance Lead      │
                      │  - 🚪 Instant Sign Out     │
                      └──────────────┬─────────────┘
                                     │
           ┌─────────────────────────┼─────────────────────────┐
           ▼                         ▼                         ▼
┌─────────────────────┐   ┌─────────────────────┐   ┌─────────────────────┐
│ 2. Add New Bill     │   │ 3. Your Bills       │   │ 4. Customers        │
│ - Upload PDF/Images │   │ - Portfolio Ledger  │   │ - Directory Master  │
│ - OCR & LLM Parsing │   │ - Ageing Analysis   │   │ - Total Exposure    │
│ - Split Disputes    │   │ - Priority Queue    │   │ - Credit Risk Score │
│ - Auto-Save Customer│   │ - Payment Links     │   │ - Payment Promises  │
│ - Generate UPI Link │   │ - SES Email Followup│   │ - Negotiated Recov. │
└─────────────────────┘   └─────────────────────┘   └─────────────────────┘
```

1. **Gatekeeper Flow:**
   - Unauthenticated visitors are restricted strictly to the branded Emerald Login portal. All ledger data, customer information, and financial metrics are inaccessible until authenticated.
2. **Post-Authentication Landing:**
   - Authenticated sessions land on the main operations workspace.
   - The persistent sidebar displays user identity (`Signed In As: Zeeshan Ali · Finance Lead`) and provides an instant `🚪 Sign out` action that clears session state and redirects to the login screen.
3. **Seamless Screen Interconnections:**
   - **From `Add new bill` to `Your bills`:** Once an invoice is parsed and saved, it automatically populates the bills table in `Your bills` and creates or links the customer in `Customers`.
   - **From `Your bills` to Customer Follow-up:** Clicking on an invoice's follow-up or payment link allows generating dynamic UPI/Razorpay links and sending human-approved emails via AWS SES.
   - **From `Customers` to Customer Ledgers:** Viewing any customer profile aggregates their full lifetime transaction history, broken promises, and outstanding balance directly linked to `Your bills`.

---

## 8. Quick Presentation Checklist

- [x] **Live Demo URL:** `http://13.126.83.182:8501`
- [x] **GitHub Repository:** `https://github.com/MdZeeshanAli01/LedgerLoop`
- [x] **Test Suite:** 83 tests (82 passed, 1 skipped cleanly)
- [x] **Container Health Endpoint:** `http://13.126.83.182:8501/_stcore/health` (Returns `200 ok`)
- [x] **AWS Region:** `ap-south-1` (Mumbai)
- [x] **ECS Cluster / Service:** `hisaabset-cluster` / `hisaabset-service-iv1acua6`
- [x] **Role Architecture:** Single Authorized Role (**Finance Lead** / `admin`)

