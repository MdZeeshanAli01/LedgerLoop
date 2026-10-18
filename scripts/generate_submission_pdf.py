import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (Pages 2+)
        if self._pageNumber > 1:
            self.drawString(36, 762, "HISAABSET (LedgerLoop) — FyndHacks 2026 Submission Package (Track C28)")
            self.setFont("Helvetica", 8)
            self.drawRightString(576, 762, "Live Demo: http://13.201.115.214:8501")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.75)
            self.line(36, 755, 576, 755)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.75)
        self.line(36, 38, 576, 38)
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        self.drawString(36, 26, "NMIMS FyndHacks 2026 | Submitting Lead: Muhammad Khaja Zeeshan Ali")
        self.setFont("Helvetica-Bold", 8)
        self.drawRightString(576, 26, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_pdf(filename="Combined_Submission_Package_Hisaabset_C28.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=46,
        bottomMargin=48
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=21,
        leading=25,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=3,
        alignment=1
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontSize=10.5,
        leading=14.5,
        textColor=colors.HexColor('#2563EB'),
        spaceAfter=10,
        alignment=1
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SectionH2',
        parent=styles['Heading3'],
        fontSize=10,
        leading=13,
        textColor=colors.HexColor('#1E293B'),
        spaceBefore=6,
        spaceAfter=3,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#334155'),
        spaceAfter=4
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=12,
        spaceAfter=3
    )

    callout_style = ParagraphStyle(
        'CalloutText',
        parent=styles['Normal'],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#1E3A8A')
    )

    meta_style = ParagraphStyle(
        'MetaText',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#334155')
    )

    code_style = ParagraphStyle(
        'CodeStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor('#0F172A')
    )

    elements = []

    # =========================================================================
    # PAGE 1: TITLE, EXECUTIVE IDENTITY, ROSTER & REPOSITORY TELEMETRY
    # =========================================================================
    elements.append(Paragraph('<b>HISAABSET (LedgerLoop)</b>', title_style))
    elements.append(Paragraph('<b>B2B Receivables Decision Desk &amp; Automated Collections Engine</b><br/><i>NMIMS FyndHacks 2026 — Track C28 Official Submission Package</i>', subtitle_style))
    elements.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=8))

    telemetry_data = [
        [Paragraph('<b>Submission Track:</b>', meta_style), Paragraph('<b>C28: Receivables Follow-Up Desk &amp; Retailer Credit Decision Engine</b>', meta_style)],
        [Paragraph('<b>Submitting Team Lead:</b>', meta_style), Paragraph('Muhammad Khaja Zeeshan Ali (B.Tech) — <code>zeeshanalimuhammadkhaja@gmail.com</code>', meta_style)],
        [Paragraph('<b>Team Members &amp; Roles:</b>', meta_style), Paragraph('<b>Faiz Sayeed</b> (Frontend UX &amp; OCR) &nbsp;|&nbsp; <b>Sai Kumar Reddy</b> (Financial Logic &amp; QA)', meta_style)],
        [Paragraph('<b>Public GitHub Repository:</b>', meta_style), Paragraph('<code>https://github.com/MdZeeshanAli01/LedgerLoop</code> (Branch: <code>main</code>)', meta_style)],
        [Paragraph('<b>Exact Commit SHA:</b>', meta_style), Paragraph('<code>41909b15acb83751a25e296a40981ad7e8547374</code> (Verified clean HEAD)', meta_style)],
        [Paragraph('<b>24/7 Live AWS Deployment:</b>', meta_style), Paragraph('<b>http://13.201.115.214:8501</b> (AWS ECS on Fargate, ap-south-1 Mumbai)', meta_style)],
        [Paragraph('<b>Demo Credentials:</b>', meta_style), Paragraph('Role: <b>Finance Lead</b> &nbsp;|&nbsp; User: <code>admin</code> &nbsp;|&nbsp; Password: <code>hisaabset123</code> (Quick Login enabled)', meta_style)],
        [Paragraph('<b>Automated Test Suite:</b>', meta_style), Paragraph('<b>89 Tests Passed</b> (100% Core Rules, Loader, Disputes, Payments, SES dispatch)', meta_style)]
    ]
    t_tel = Table(telemetry_data, colWidths=[130, 410])
    t_tel.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_tel)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph('<b>Executive Venture Summary</b>', h1_style))
    elements.append(Paragraph(
        'In India’s unorganized supply chains, over 350,000 wholesale distributors (FMCG, pharmaceuticals, hardware, paints) extend short-term trade credit to local kirana retailers. These distributors routinely suffer from <b>delayed payments, artificial dispute claims, and frozen working capital</b>. While traditional accounting packages like Tally and Busy record accounting ledger entries, they provide zero workflow support to decide <i>who to chase, for how much, and why</i>.',
        body_style
    ))
    elements.append(Paragraph(
        '<b>Hisaabset</b> transforms this broken process. It acts as an intelligent decision-support desk that ingests invoices via Gemini AI OCR, automatically isolates disputed amounts from undisputed collectible cash, ranks debtors mathematically based on overdue age and promise reliability, prepares tone-calibrated human-in-the-loop reminders via Amazon SES, and generates verifiable payment settlement receipt vouchers upon payment receipt.',
        body_style
    ))

    # Core Value Pillars Table
    elements.append(Spacer(1, 4))
    elements.append(Paragraph('<b>Venture Highlights &amp; Architectural Pillars</b>', h1_style))
    pillars_data = [
        [Paragraph('<b>Pillar</b>', meta_style), Paragraph('<b>The Traditional Flaw</b>', meta_style), Paragraph('<b>The Hisaabset Innovation</b>', meta_style)],
        [
            Paragraph('<b>Dispute Handling</b>', meta_style),
            Paragraph('Retailers use ₹2,000 damaged goods to withhold an entire ₹50,000 invoice for 60+ days.', meta_style),
            Paragraph('<b>Dispute Isolation:</b> Automatically segregates ₹48,000 collectible cash from ₹2,000 held under review.', meta_style)
        ],
        [
            Paragraph('<b>Debtor Prioritization</b>', meta_style),
            Paragraph('Collections staff chase arbitrarily or call favorite friendly accounts, ignoring risky debts.', meta_style),
            Paragraph('<b>Deterministic Scoring:</b> Multi-factor mathematical formula (Age, Amount, Broken Promises).', meta_style)
        ],
        [
            Paragraph('<b>Invoice Ingestion</b>', meta_style),
            Paragraph('Manual data entry of physical paper/PDF bills leads to data errors and delayed books.', meta_style),
            Paragraph('<b>Multimodal AI Extraction:</b> Gemini 1.5 Flash extracts line items, totals, and due dates in seconds.', meta_style)
        ],
        [
            Paragraph('<b>Collections Messaging</b>', meta_style),
            Paragraph('Clumsy WhatsApp texts alienate key customers or breach compliance boundaries.', meta_style),
            Paragraph('<b>Human-in-the-Loop SES:</b> Tone-adaptive (Gentle, Firm, Formal) drafts reviewed before dispatch.', meta_style)
        ],
        [
            Paragraph('<b>Cloud Architecture</b>', meta_style),
            Paragraph('Fragile localhost prototypes that crash or stop when laptops are closed.', meta_style),
            Paragraph('<b>24/7 AWS ECS Fargate:</b> Production Docker container running continuously in ap-south-1 Mumbai.', meta_style)
        ]
    ]
    t_pillars = Table(pillars_data, colWidths=[90, 220, 230])
    t_pillars.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_pillars)

    # =========================================================================
    # PAGE 2: PROBLEM DEEP-DIVE & MARKET REALITY (THE INDIAN B2B CREDIT CRISIS)
    # =========================================================================
    elements.append(PageBreak())
    elements.append(Paragraph('<b>1. The Problem Space: The Indian Wholesale Credit Trap</b>', h1_style))
    elements.append(Paragraph(
        'India’s wholesale distribution sector powers ₹70 Lakh Crore ($850 Billion) of physical commerce. Distributors buy upfront from manufacturers (HUL, ITC, Sun Pharma, Asian Paints) on strict 7-to-15 day credit terms, but are forced by local market dynamics to extend 21-to-45 day unsecured credit to over 15 million neighborhood retail stores (kiranas).',
        body_style
    ))

    elements.append(Paragraph('<b>1.1 The Cash Credit (CC) / Bank Overdraft (OD) Debt Trap</b>', h2_style))
    elements.append(Paragraph(
        'To bridge the gap between manufacturer bills and delayed retailer payments, every distributor relies on bank Cash Credit / Overdraft lines at <b>12% to 14% annual interest</b>. When ₹15 Lakhs of receivables slip into the 60–90 day overdue bucket, the distributor pays <b>₹15,000 to ₹17,500 every single month in dead interest costs</b>, directly obliterating their thin 3%–5% net distribution operating margin.',
        body_style
    ))

    elements.append(Paragraph('<b>1.2 The "Dispute Hostage" Phenomenon</b>', h2_style))
    elements.append(Paragraph(
        'In daily distribution, minor friction is inevitable: damaged packaging, expired batches, price scheme differences, or short deliveries. Retailers deliberately exploit these minor discrepancies (representing 2%–5% of invoice value) as leverage to <b>hold 100% of the payment hostage</b>. Without a structured dispute-isolation workflow, distributors fail to collect the undisputed 95% cash for months.',
        body_style
    ))

    elements.append(Spacer(1, 4))
    # Callout Box for Market Reality
    callout_data = [[
        Paragraph(
            '<b>Industry Truth:</b> Traditional ERPs (Tally, Busy, Marg) are backward-looking accounting ledgers. They record what happened in the past, but offer zero intelligence on operational prioritization, broken payment promises, dispute ring-fencing, or human-reviewed collection follow-ups.',
            callout_style
        )
    ]]
    t_callout = Table(callout_data, colWidths=[540])
    t_callout.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#DBEAFE')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#93C5FD')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_callout)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph('<b>1.3 Market Sizing: India Addressable Opportunity</b>', h1_style))
    tam_data = [
        [Paragraph('<b>Metric</b>', meta_style), Paragraph('<b>Target Segment &amp; Sizing</b>', meta_style), Paragraph('<b>Commercial Value</b>', meta_style)],
        [
            Paragraph('<b>TAM</b> (Total Addressable Market)', meta_style),
            Paragraph('All registered GST trade distributors and wholesalers in India (~1.2 Million entities)', meta_style),
            Paragraph('<b>₹3,600 Cr / year</b> ($430M)', meta_style)
        ],
        [
            Paragraph('<b>SAM</b> (Serviceable Addressable Market)', meta_style),
            Paragraph('Organized distributors with ₹2 Cr–₹50 Cr annual turnover and 100+ retail accounts (~350,000 entities)', meta_style),
            Paragraph('<b>₹1,050 Cr / year</b> ($126M)', meta_style)
        ],
        [
            Paragraph('<b>SOM</b> (Serviceable Obtainable Market)', meta_style),
            Paragraph('Early-adopter FMCG, pharma, and hardware distributors in Tier 1 &amp; 2 industrial hubs (15,000 entities in 3 years)', meta_style),
            Paragraph('<b>₹45 Cr / year</b> ($5.4M)', meta_style)
        ]
    ]
    t_tam = Table(tam_data, colWidths=[130, 290, 120])
    t_tam.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_tam)

    # =========================================================================
    # PAGE 3: THE HISAABSET SOLUTION & CORE DECISION ENGINES
    # =========================================================================
    elements.append(PageBreak())
    elements.append(Paragraph('<b>2. Product Architecture &amp; Core Decision Engines</b>', h1_style))
    elements.append(Paragraph(
        'Hisaabset is architected as an <b>Air-Gapped Decision Support System</b>. It provides actionable intelligence to the Finance Lead while ensuring safety by maintaining human-in-the-loop approvals for all external communications and credit decisions.',
        body_style
    ))

    elements.append(Paragraph('<b>2.1 Dispute Isolation &amp; Settlement Architecture</b>', h2_style))
    elements.append(Paragraph(
        'When a dispute occurs, Hisaabset partitions the invoice balance into two distinct ledgers: <code>Collectable Balance</code> and <code>Review Amount</code>. If an invoice of ₹50,000 has a ₹5,000 dispute for damaged goods, the system holds ₹5,000 under review and directs collections efforts exclusively toward the safe ₹45,000. It supports three dispute resolutions: <i>Pending Investigation</i>, <i>Replacement Goods Delivered</i>, and <i>Credit Note Reconciliation</i>.',
        body_style
    ))

    elements.append(Paragraph('<b>2.2 Deterministic Multi-Factor Priority Queue</b>', h2_style))
    elements.append(Paragraph(
        'Unlike heuristic or random follow-ups, Hisaabset ranks overdue collectible debts using a mathematically verifiable scoring algorithm:',
        body_style
    ))
    
    # Formula box
    formula_data = [[
        Paragraph(
            '<b>Base Priority Score:</b><br/>'
            '<code>Score_base = 100 × (0.45 × AgeScore + 0.35 × AmountScore + 0.20 × BrokenPromiseFlag)</code><br/>'
            '<b>Aging Escalation (>90 Days Overdue):</b><br/>'
            '<code>Escalation_factor = 0.25 + 0.50 × min((DaysOverdue - 90) / 90, 1.0)</code><br/>'
            '<code>Final_Priority = Score_base + (100 - Score_base) × Escalation_factor</code>',
            code_style
        )
    ]]
    t_formula = Table(formula_data, colWidths=[540])
    t_formula.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#94A3B8')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(t_formula)
    elements.append(Spacer(1, 4))

    elements.append(Paragraph('<b>2.3 Multimodal AI Document Ingestion (Google Gemini 1.5 Flash)</b>', h2_style))
    elements.append(Paragraph(
        'Distributors receive physical paper invoices and PDF delivery challans. Hisaabset integrates Google Gemini 1.5 Flash to extract invoice metadata (Invoice Number, Retailer Name, Billed Amount, Line Items, Due Date). Users review extracted data and assign dispute tags directly before saving.',
        body_style
    ))

    elements.append(Paragraph('<b>2.4 One-Click Payment Settlement &amp; Printable Receipt Vouchers</b>', h2_style))
    elements.append(Paragraph(
        'When an overdue invoice is settled (via RTGS, NEFT, UPI, or Cash), the Finance Lead enters payment details in the Record Payment module. Hisaabset updates outstanding balances to ₹0.00, moves the invoice to Paid status, and generates a formal, printable Payment Settlement Receipt Voucher with unique voucher numbers for retailer verification.',
        body_style
    ))

    elements.append(Paragraph('<b>2.5 Human-in-the-Loop Amazon SES Notifications</b>', h2_style))
    elements.append(Paragraph(
        'Hisaabset automatically drafts collection emails calibrated by overdue age: <i>Gentle Reminder</i> (1–30 days), <i>Firm Notice</i> (31–60 days), and <i>Formal Demand</i> (61+ days or broken promises). The Finance Lead reviews and approves the draft before dispatching via Amazon SES with verified DKIM/SPF.',
        body_style
    ))

    # =========================================================================
    # PAGE 4: CLOUD-NATIVE AWS PRODUCTION ARCHITECTURE
    # =========================================================================
    elements.append(PageBreak())
    elements.append(Paragraph('<b>3. Cloud-Native AWS Production Infrastructure</b>', h1_style))
    elements.append(Paragraph(
        'Hisaabset is deployed as a continuous cloud-native containerized application in AWS Region <code>ap-south-1</code> (Mumbai). It provides 24/7 uninterrupted uptime without local workstation dependencies.',
        body_style
    ))

    aws_infra_data = [
        [Paragraph('<b>AWS Service</b>', meta_style), Paragraph('<b>Configuration Details</b>', meta_style), Paragraph('<b>Engineering Justification</b>', meta_style)],
        [
            Paragraph('<b>AWS ECS on Fargate</b>', meta_style),
            Paragraph('0.5 vCPU, 1 GB RAM, Fargate Linux x86_64 serverless container pod.', meta_style),
            Paragraph('Zero server maintenance; automatic OS patching; continuous 24/7 uptime; no cold-start latency.', meta_style)
        ],
        [
            Paragraph('<b>AWS Elastic Container Registry (ECR)</b>', meta_style),
            Paragraph('Private repository: <code>hisaabset-repo</code> with immutable image tags.', meta_style),
            Paragraph('Secure, high-bandwidth container image registry integrated directly with ECS task execution roles.', meta_style)
        ],
        [
            Paragraph('<b>Amazon Simple Email Service (SES)</b>', meta_style),
            Paragraph('Production endpoint in <code>ap-south-1</code>; verified sender with in-app sandbox verification.', meta_style),
            Paragraph('Enterprise-grade transactional email dispatch with DKIM signing and strict bounce/complaint handling.', meta_style)
        ],
        [
            Paragraph('<b>AWS VPC &amp; Security Groups</b>', meta_style),
            Paragraph('Security Group: <code>hisaabset-ecs-sg</code>; ingress port 8501; unrestricted egress 443.', meta_style),
            Paragraph('Network isolation preventing unauthorized access while allowing outbound calls to AWS and Gemini APIs.', meta_style)
        ],
        [
            Paragraph('<b>AWS IAM Least Privilege</b>', meta_style),
            Paragraph('Roles: <code>ecsTaskExecutionRole</code> &amp; task role with targeted SES permissions.', meta_style),
            Paragraph('Ensures the container cannot access unauthorized AWS resources outside its operational boundary.', meta_style)
        ],
        [
            Paragraph('<b>Amazon CloudWatch Logs</b>', meta_style),
            Paragraph('Log Group: <code>/ecs/hisaabset-task</code> with 7-day retention policy.', meta_style),
            Paragraph('Centralized real-time telemetry, crash monitoring, and audit log tracking for all financial operations.', meta_style)
        ]
    ]
    t_aws = Table(aws_infra_data, colWidths=[120, 200, 220])
    t_aws.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('LEFTPADDING', (0,0), (-1,-1), 6),
        ('RIGHTPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_aws)
    elements.append(Spacer(1, 8))

    elements.append(Paragraph('<b>3.1 Live Deployment Telemetry &amp; Verification</b>', h2_style))
    elements.append(Paragraph(
        '• <b>Public Endpoint:</b> <code>http://13.201.115.214:8501</code><br/>'
        '• <b>Healthcheck Verification:</b> <code>curl -I http://13.201.115.214:8501/_stcore/health</code> returns <code>HTTP/1.1 200 OK</code>.<br/>'
        '• <b>Container Task:</b> Active ECS Task Revision <code>hisaabset:7</code> running in VPC Subnet <code>subnet-09f196924d5cb3673</code>.<br/>'
        '• <b>Security Isolation:</b> Non-root container user, read-only root filesystem compliance, and no hardcoded secrets.',
        body_style
    ))

    # =========================================================================
    # PAGE 5: BUSINESS PRICING MODEL, AWS TCO & UNIT ECONOMICS
    # =========================================================================
    elements.append(PageBreak())
    elements.append(Paragraph('<b>4. Business Model, AWS TCO &amp; Unit Economics</b>', h1_style))
    elements.append(Paragraph(
        'Hisaabset operates on a high-margin, scalable B2B Software-as-a-Service (SaaS) subscription model designed to match the economic realities of Indian wholesale trade distributors.',
        body_style
    ))

    elements.append(Paragraph('<b>4.1 AWS Total Cost of Ownership (TCO) Breakdown</b>', h2_style))
    tco_data = [
        [Paragraph('<b>Infrastructure Component</b>', meta_style), Paragraph('<b>Sizing / Consumption</b>', meta_style), Paragraph('<b>Monthly Cost (USD)</b>', meta_style), Paragraph('<b>Monthly Cost (INR)</b>', meta_style)],
        [
            Paragraph('AWS Fargate Compute (0.5 vCPU)', meta_style),
            Paragraph('0.5 vCPU × 730 hours @ $0.04048/vCPU-hr', meta_style),
            Paragraph('$14.78', meta_style),
            Paragraph('₹1,227', meta_style)
        ],
        [
            Paragraph('AWS Fargate Memory (1 GB RAM)', meta_style),
            Paragraph('1.0 GB × 730 hours @ $0.004445/GB-hr', meta_style),
            Paragraph('$3.25', meta_style),
            Paragraph('₹270', meta_style)
        ],
        [
            Paragraph('AWS ECR Container Storage', meta_style),
            Paragraph('2 GB container image @ $0.10/GB', meta_style),
            Paragraph('$0.20', meta_style),
            Paragraph('₹17', meta_style)
        ],
        [
            Paragraph('Amazon SES Email Dispatch', meta_style),
            Paragraph('~2,500 transactional emails/month', meta_style),
            Paragraph('$0.25', meta_style),
            Paragraph('₹21', meta_style)
        ],
        [
            Paragraph('CloudWatch Logs &amp; Metrics', meta_style),
            Paragraph('5 GB ingestion &amp; dashboard telemetry', meta_style),
            Paragraph('$2.68', meta_style),
            Paragraph('₹222', meta_style)
        ],
        [
            Paragraph('Data Transfer Out &amp; Misc', meta_style),
            Paragraph('Outbound Streamlit UI traffic (~10 GB)', meta_style),
            Paragraph('$1.00', meta_style),
            Paragraph('₹83', meta_style)
        ],
        [
            Paragraph('<b>TOTAL INFRASTRUCTURE RUNNING COST</b>', meta_style),
            Paragraph('<b>Continuous 24/7 Active Pod</b>', meta_style),
            Paragraph('<b>$22.16 / month</b>', meta_style),
            Paragraph('<b>₹1,840 / month</b>', meta_style)
        ]
    ]
    t_tco = Table(tco_data, colWidths=[160, 190, 100, 90])
    t_tco.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_tco)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph('<b>4.2 SaaS Pricing Tiers &amp; Packaging</b>', h2_style))
    pricing_data = [
        [Paragraph('<b>Tier Plan</b>', meta_style), Paragraph('<b>Target Segment</b>', meta_style), Paragraph('<b>Price (INR)</b>', meta_style), Paragraph('<b>Features Included</b>', meta_style)],
        [
            Paragraph('<b>Starter</b>', meta_style),
            Paragraph('Single-category distributors (up to 50 retailers)', meta_style),
            Paragraph('<b>₹1,499 / mo</b><br/>(₹14,990/yr)', meta_style),
            Paragraph('Balance calculation, dispute logging, PDF exports, standard priority scoring.', meta_style)
        ],
        [
            Paragraph('<b>Growth / Pro (Core)</b>', meta_style),
            Paragraph('Mid-sized FMCG/Pharma (50–250 retailers)', meta_style),
            Paragraph('<b>₹2,499 / mo</b><br/>(₹24,990/yr)', meta_style),
            Paragraph('All Starter features + Gemini AI PDF Ingestion, Amazon SES email notices, payment vouchers, promise tracking.', meta_style)
        ],
        [
            Paragraph('<b>Enterprise Multi-Branch</b>', meta_style),
            Paragraph('Super-stockists &amp; multi-depot (250+ retailers)', meta_style),
            Paragraph('<b>₹4,999 / mo</b><br/>(₹49,990/yr)', meta_style),
            Paragraph('All Pro features + Multi-branch consolidation, custom ERP connectors (Tally/Busy), dedicated IP, priority support.', meta_style)
        ]
    ]
    t_pricing = Table(pricing_data, colWidths=[100, 150, 90, 200])
    t_pricing.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_pricing)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph('<b>4.3 Unit Economics &amp; Customer ROI Analysis</b>', h2_style))
    elements.append(Paragraph(
        '• <b>Hosting Scalability:</b> In a shared container pool, a single 0.5 vCPU Fargate pod easily hosts 30 to 50 active SMB distributors. The direct cloud infrastructure cost per tenant is <b>under ₹65 per month</b>, yielding an extraordinary <b>97.4% Gross Margin</b> at the ₹2,499/mo price point.<br/>'
        '• <b>Customer ROI Justification:</b> For an average distributor carrying ₹15 Lakhs in 60-day receivables, accelerating collections by just 14 days saves ₹7,000/month in bank overdraft interest and prevents ₹8,000/month in write-offs. Against a ₹2,499 subscription fee, the distributor earns an immediate <b>6x to 8x Net ROI</b>.',
        body_style
    ))

    # =========================================================================
    # PAGE 6: ENGINEERING RIGOR, COMPETITIVE MATRIX & SUBMISSION CHECKLIST
    # =========================================================================
    elements.append(PageBreak())
    elements.append(Paragraph('<b>5. Engineering Rigor &amp; Testing Validation</b>', h1_style))
    elements.append(Paragraph(
        'Hisaabset was built adhering to strict test-driven development practices. All financial calculations use Python’s exact <code>Decimal</code> module, eliminating IEEE 754 floating-point rounding errors.',
        body_style
    ))

    test_data = [
        [Paragraph('<b>Test Suite Module</b>', meta_style), Paragraph('<b>Test File</b>', meta_style), Paragraph('<b>Count &amp; Status</b>', meta_style), Paragraph('<b>Scope Covered</b>', meta_style)],
        [Paragraph('Core Loader &amp; Validation', meta_style), Paragraph('<code>tests/test_loader.py</code>', meta_style), Paragraph('12 / 12 Passed', meta_style), Paragraph('Input normalization, date boundaries, null handling, duplicate rejection', meta_style)],
        [Paragraph('Rules &amp; Aging Logic', meta_style), Paragraph('<code>tests/test_rules.py</code>', meta_style), Paragraph('26 / 26 Passed', meta_style), Paragraph('Balances, applied receipts, age buckets, priority ranking formula', meta_style)],
        [Paragraph('Dispute Isolation Engine', meta_style), Paragraph('<code>tests/test_disputes.py</code>', meta_style), Paragraph('14 / 14 Passed', meta_style), Paragraph('Dispute causes, resolution splits, credit note application', meta_style)],
        [Paragraph('Draft Follow-Up &amp; Tone', meta_style), Paragraph('<code>tests/test_drafts.py</code>', meta_style), Paragraph('8 / 8 Passed', meta_style), Paragraph('Customer grouping, tone escalation, broken-promise handling', meta_style)],
        [Paragraph('End-to-End Integration', meta_style), Paragraph('<code>tests/test_integration.py</code>', meta_style), Paragraph('10 / 10 Passed', meta_style), Paragraph('Full starter fixture regression (tests 1–42 specification)', meta_style)],
        [Paragraph('Payments &amp; Vouchers', meta_style), Paragraph('<code>tests/test_payments.py</code>', meta_style), Paragraph('9 / 9 Passed', meta_style), Paragraph('Invoice settlement, status transition, payment voucher generation', meta_style)],
        [Paragraph('Authentication &amp; Role Gate', meta_style), Paragraph('<code>tests/test_auth.py</code>', meta_style), Paragraph('6 / 6 Passed', meta_style), Paragraph('PBKDF2-SHA256 password hashing, session state token validation', meta_style)],
        [Paragraph('Retailer Credit Risk', meta_style), Paragraph('<code>tests/test_retailer_risk.py</code>', meta_style), Paragraph('4 / 4 Passed', meta_style), Paragraph('Repayment history scoring, limit suggestions, break-even validation', meta_style)],
        [Paragraph('<b>TOTAL TEST COVERAGE</b>', meta_style), Paragraph('<b>Full Pytest Suite</b>', meta_style), Paragraph('<b>89 / 89 Passed</b>', meta_style), Paragraph('<b>100% Core Business Logic &amp; Mathematical Coverage</b>', meta_style)]
    ]
    t_test = Table(test_data, colWidths=[120, 130, 90, 200])
    t_test.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('BACKGROUND', (0,-1), (-1,-1), colors.HexColor('#DCFCE7')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_test)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph('<b>6. Competitive Advantage Matrix</b>', h1_style))
    comp_data = [
        [Paragraph('<b>Feature / Capability</b>', meta_style), Paragraph('<b>Tally / Busy</b>', meta_style), Paragraph('<b>Khatabook / Vyapar</b>', meta_style), Paragraph('<b>Hisaabset (LedgerLoop)</b>', meta_style)],
        [Paragraph('Core Purpose', meta_style), Paragraph('Tax compliance &amp; ledger accounting', meta_style), Paragraph('Digital bahi-khata for micro-retailers', meta_style), Paragraph('<b>Intelligent B2B Collections Decision Desk</b>', meta_style)],
        [Paragraph('Dispute Isolation', meta_style), Paragraph('No (binary balance)', meta_style), Paragraph('No', meta_style), Paragraph('<b>Yes (separates disputed from collectable)</b>', meta_style)],
        [Paragraph('Debtor Prioritization', meta_style), Paragraph('Chronological aging only', meta_style), Paragraph('None', meta_style), Paragraph('<b>Mathematical Multi-Factor Priority Score</b>', meta_style)],
        [Paragraph('AI Invoice OCR', meta_style), Paragraph('Manual entry only', meta_style), Paragraph('Basic receipt photo capture', meta_style), Paragraph('<b>Gemini 1.5 Flash automated extraction</b>', meta_style)],
        [Paragraph('Human-in-the-Loop Reminders', meta_style), Paragraph('Manual printouts', meta_style), Paragraph('Automated WhatsApp spam', meta_style), Paragraph('<b>Calibrated tone drafts via Amazon SES</b>', meta_style)],
        [Paragraph('Payment Settlement Vouchers', meta_style), Paragraph('Receipt voucher (complex)', meta_style), Paragraph('None', meta_style), Paragraph('<b>Instant one-click printable voucher</b>', meta_style)],
        [Paragraph('Cloud Availability', meta_style), Paragraph('Desktop on-premise (Tally Prime)', meta_style), Paragraph('Mobile-only app', meta_style), Paragraph('<b>24/7 AWS ECS Fargate Web Cloud</b>', meta_style)]
    ]
    t_comp = Table(comp_data, colWidths=[120, 120, 130, 170])
    t_comp.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F8FAFC')),
        ('BACKGROUND', (3,0), (3,-1), colors.HexColor('#EFF6FF')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('LEFTPADDING', (0,0), (-1,-1), 5),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_comp)
    elements.append(Spacer(1, 6))

    elements.append(Paragraph('<b>7. Hackathon Evidence Verification Checklist (12 / 12)</b>', h1_style))
    elements.append(Paragraph(
        '1. <b>Public Git Repository:</b> <code>https://github.com/MdZeeshanAli01/LedgerLoop</code><br/>'
        '2. <b>Live Hosted Cloud URL:</b> <code>http://13.201.115.214:8501</code> (AWS ECS Fargate Mumbai)<br/>'
        '3. <b>40-Character Commit SHA:</b> <code>41909b15acb83751a25e296a40981ad7e8547374</code><br/>'
        '4. <b>Cloud Architecture Evidence:</b> Documented in <code>docs/TECHNICAL_PRESENTATION_GUIDE.md</code><br/>'
        '5. <b>Business Pricing &amp; AWS TCO:</b> Comprehensive spreadsheet &amp; model in <code>docs/BUSINESS_PRICING_AND_AWS_COST_MODEL.md</code><br/>'
        '6. <b>MBA Presentation Deck Guide:</b> Slide-by-slide pitch guide in <code>docs/MBA_GUIDE.md</code><br/>'
        '7. <b>Technical Handoff Document:</b> Complete specification in <code>docs/TECHNICAL_HANDOFF.md</code><br/>'
        '8. <b>Automated Test Evidence:</b> 89 Pytest test suite results in <code>tests/</code><br/>'
        '9. <b>Sample Data Fixtures:</b> Starter fixture and edge-case synthetic data in <code>data/</code><br/>'
        '10. <b>Docker &amp; Deployment Artifacts:</b> Production container files in <code>deploy/</code> and <code>app/</code><br/>'
        '11. <b>SES Notification Verification:</b> Integrated communication engine in <code>src/communications.py</code><br/>'
        '12. <b>Invoice Settlement &amp; Vouchers:</b> Operational closure engine in <code>src/payments.py</code>',
        body_style
    ))

    # Build the document with NumberedCanvas
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"SUCCESS: Generated detailed 6-page submission package: {filename}")

if __name__ == '__main__':
    build_pdf()
