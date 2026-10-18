from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import os

pdf_path = os.path.join(os.getcwd(), 'Combined_Submission_Package_Hisaabset_C28.pdf')
doc = SimpleDocTemplate(pdf_path, pagesize=letter,
                        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    'DocTitle',
    parent=styles['Heading1'],
    fontSize=20,
    leading=24,
    textColor=colors.HexColor('#0F172A'),
    spaceAfter=4,
    alignment=1
)

subtitle_style = ParagraphStyle(
    'DocSubTitle',
    parent=styles['Normal'],
    fontSize=11,
    leading=15,
    textColor=colors.HexColor('#2563EB'),
    spaceAfter=12,
    alignment=1
)

h1_style = ParagraphStyle(
    'SectionH1',
    parent=styles['Heading2'],
    fontSize=13,
    leading=17,
    textColor=colors.HexColor('#1E293B'),
    spaceBefore=10,
    spaceAfter=4
)

body_style = ParagraphStyle(
    'BodyTextCustom',
    parent=styles['Normal'],
    fontSize=9,
    leading=13,
    textColor=colors.HexColor('#334155'),
    spaceAfter=5
)

bullet_style = ParagraphStyle(
    'BulletCustom',
    parent=body_style,
    leftIndent=12,
    spaceAfter=3
)

meta_style = ParagraphStyle(
    'MetaText',
    parent=styles['Normal'],
    fontSize=8.5,
    leading=11.5,
    textColor=colors.HexColor('#475569')
)

elements = []

elements.append(Paragraph('<b>HISAABSET (LedgerLoop)</b>', title_style))
elements.append(Paragraph('B2B Receivables Decision Desk &amp; Automated Collections Engine<br/><b>FyndHacks 2026 — Track C28 Submission Package</b>', subtitle_style))
elements.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#2563EB'), spaceAfter=10))

summary_data = [
    [Paragraph('<b>Submission Track:</b>', meta_style), Paragraph('C28 Receivables Follow-Up Desk &amp; Retailer Credit Decision Engine', meta_style)],
    [Paragraph('<b>Submitting Lead:</b>', meta_style), Paragraph('Muhammad Khaja Zeeshan Ali (B.Tech) — zeeshanalimuhammadkhaja@gmail.com', meta_style)],
    [Paragraph('<b>Team Members:</b>', meta_style), Paragraph('Faiz Sayeed, Sai Kumar Reddy', meta_style)],
    [Paragraph('<b>Exact Commit SHA:</b>', meta_style), Paragraph('<code>1947a631125956e2f5db3c3d51b21232da984bfb</code>', meta_style)],
    [Paragraph('<b>GitHub Repository:</b>', meta_style), Paragraph('https://github.com/MdZeeshanAli01/LedgerLoop', meta_style)],
    [Paragraph('<b>Live Cloud URL:</b>', meta_style), Paragraph('http://13.201.115.214:8501 (AWS ECS Fargate ap-south-1 Mumbai)', meta_style)],
    [Paragraph('<b>Demo Credentials:</b>', meta_style), Paragraph('Role: Finance Lead | User: <b>admin</b> | Password: <b>hisaabset123</b>', meta_style)]
]

t_summary = Table(summary_data, colWidths=[130, 410])
t_summary.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
    ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ('TOPPADDING', (0,0), (-1,-1), 3),
    ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ('LEFTPADDING', (0,0), (-1,-1), 8),
    ('RIGHTPADDING', (0,0), (-1,-1), 8),
]))
elements.append(t_summary)
elements.append(Spacer(1, 10))

elements.append(Paragraph('<b>1. Executive Summary &amp; Problem Statement</b>', h1_style))
elements.append(Paragraph(
    'In India, over 350,000 organized B2B wholesale distributors (FMCG, pharmaceuticals, hardware, lubricants) operate under intense working capital strain. While accounting tools like Tally and Busy record invoices, they do not resolve the primary cash-leakage bottleneck: <b>trapped receivables and disputed collections</b>.',
    body_style
))
elements.append(Paragraph('• <b>Working Capital Trap:</b> Distributors routinely carry ₹10L–₹25L in 30–90+ day overdue credits, paying 12%–14% p.a. in bank cash-credit/overdraft interest (₹10,000–₹18,000/month in dead financing costs).', bullet_style))
elements.append(Paragraph('• <b>The Dispute Hostage Problem:</b> Retailers exploit minor delivery discrepancies (e.g., a ₹2,000 damaged jar on a ₹50,000 bill) to withhold 100% of the invoice payment for months.', bullet_style))
elements.append(Paragraph('• <b>Follow-up Paralysis:</b> Traditional collections rely on clumsy WhatsApp messages or aggressive phone calls that strain long-term distributor-retailer commercial goodwill.', bullet_style))

elements.append(Paragraph('<b>2. The Hisaabset Working Solution</b>', h1_style))
elements.append(Paragraph(
    'Hisaabset is an intelligent receivables decision-support desk designed for the distributor Finance Lead. Key operational capabilities include:',
    body_style
))
elements.append(Paragraph('• <b>Dispute Isolation Engine:</b> Instantly separates disputed claims (damaged goods, rate differences, short deliveries) from safe collectible cash. The undisputed ₹48,000 is collected immediately while the ₹2,000 discrepancy undergoes formal credit-note reconciliation.', bullet_style))
elements.append(Paragraph('• <b>Deterministic Priority Scoring:</b> Ranks debtors mathematically using a formula combining Age Score (0.45), Relative Balance Score (0.35), and Broken-Promise History (0.20), plus non-linear escalation for debts &gt;90 days.', bullet_style))
elements.append(Paragraph('• <b>AI Ingestion &amp; OCR:</b> Ingests PDF and physical invoices directly using Google Gemini 1.5 Flash, automatically extracting line items, dates, and amounts without manual keying.', bullet_style))
elements.append(Paragraph('• <b>One-Click Payment Settlement &amp; Vouchers:</b> Records incoming RTGS/NEFT/Cash payments, marks invoices as Closed/Paid, and generates printable Payment Settlement Vouchers.', bullet_style))
elements.append(Paragraph('• <b>Human-in-the-Loop Reminders:</b> Previews tone-adapted (Gentle, Firm, Formal) collection notices dispatched securely via Amazon SES with verified audit trails.', bullet_style))

elements.append(Spacer(1, 8))
elements.append(Paragraph('<b>3. Cloud-Native Production Architecture (AWS)</b>', h1_style))
arch_data = [
    [Paragraph('<b>Layer</b>', meta_style), Paragraph('<b>AWS Service</b>', meta_style), Paragraph('<b>Specification &amp; Role</b>', meta_style)],
    [Paragraph('Compute Runtime', meta_style), Paragraph('AWS ECS on Fargate', meta_style), Paragraph('0.5 vCPU, 1 GB RAM continuous container microservice (ap-south-1 Mumbai)', meta_style)],
    [Paragraph('Container Registry', meta_style), Paragraph('AWS ECR', meta_style), Paragraph('Immutable Docker image repository with automated digest scanning', meta_style)],
    [Paragraph('Communications', meta_style), Paragraph('Amazon SES', meta_style), Paragraph('Managed enterprise transactional email engine with verified DKIM/SPF', meta_style)],
    [Paragraph('Networking &amp; Security', meta_style), Paragraph('VPC Security Groups &amp; IAM', meta_style), Paragraph('Port 8501 restricted ingress; least-privilege IAM execution roles; CloudWatch logging', meta_style)],
    [Paragraph('Testing &amp; Quality', meta_style), Paragraph('Automated Pytest Suite', meta_style), Paragraph('89 unit and integration tests passing; zero Decimal money precision loss', meta_style)]
]
t_arch = Table(arch_data, colWidths=[100, 120, 320])
t_arch.setStyle(TableStyle([
    ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
    ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
    ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ('TOPPADDING', (0,0), (-1,-1), 2.5),
    ('BOTTOMPADDING', (0,0), (-1,-1), 2.5),
    ('LEFTPADDING', (0,0), (-1,-1), 6),
    ('RIGHTPADDING', (0,0), (-1,-1), 6),
]))
elements.append(t_arch)

elements.append(Spacer(1, 8))
elements.append(Paragraph('<b>4. Business Model, AWS TCO &amp; Unit Economics</b>', h1_style))
elements.append(Paragraph('• <b>SaaS Subscription Pricing:</b> ₹2,499 / month per distributor (or ₹24,990 / year upfront).', bullet_style))
elements.append(Paragraph('• <b>AWS Cloud TCO:</b> $22.16 / month (~₹1,840 / month) for 24/7 continuous hosting on AWS ECS Fargate.', bullet_style))
elements.append(Paragraph('• <b>Multi-Tenant Scalability:</b> A single 0.5 vCPU base pod serves 30–50 SMB distributors, reducing infrastructure cost to &lt;₹65 per tenant/month (&gt;97% gross margin).', bullet_style))
elements.append(Paragraph('• <b>Distributor ROI:</b> By accelerating payment cycles by 12–15 days and preventing ₹15,000+ in monthly overdraft interest, Hisaabset delivers an undeniable <b>6x–8x net ROI</b>.', bullet_style))

elements.append(Spacer(1, 8))
elements.append(Paragraph('<b>5. Key Repository Evidence Links</b>', h1_style))
elements.append(Paragraph('• <b>Live Application:</b> http://13.201.115.214:8501', bullet_style))
elements.append(Paragraph('• <b>GitHub Repository:</b> https://github.com/MdZeeshanAli01/LedgerLoop', bullet_style))
elements.append(Paragraph('• <b>Financial &amp; Cloud Cost Model:</b> <code>docs/BUSINESS_PRICING_AND_AWS_COST_MODEL.md</code>', bullet_style))
elements.append(Paragraph('• <b>Technical Handoff &amp; Architecture:</b> <code>docs/TECHNICAL_HANDOFF.md</code>', bullet_style))
elements.append(Paragraph('• <b>MBA Presentation Guide:</b> <code>docs/MBA_GUIDE.md</code>', bullet_style))

doc.build(elements)
print('SUCCESS: Generated Combined_Submission_Package_Hisaabset_C28.pdf')
