import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

# Sheet 1: Base Case
ws1 = wb.active
ws1.title = "Base case"
ws1.views.sheetView[0].showGridLines = True

header_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
sub_header_fill = PatternFill(start_color="DBEAFE", end_color="DBEAFE", fill_type="solid")
sub_header_font = Font(name="Calibri", size=10, bold=True, color="1E3A8A")
bold_font = Font(name="Calibri", size=10, bold=True)
regular_font = Font(name="Calibri", size=10)
italic_font = Font(name="Calibri", size=9, italic=True, color="64748B")

thin_border = Border(
    left=Side(style='thin', color='CBD5E1'),
    right=Side(style='thin', color='CBD5E1'),
    top=Side(style='thin', color='CBD5E1'),
    bottom=Side(style='thin', color='CBD5E1')
)

ws1["A1"] = "Hisaabset (LedgerLoop) — Unit Economics & SaaS Pricing Model"
ws1["A1"].font = Font(name="Calibri", size=14, bold=True, color="0F172A")
ws1["A2"] = "FyndHacks 2026 — Track C28 (Editable Calculations, Sources & Assumptions)"
ws1["A2"].font = italic_font

# Section 1: Pricing Tiers & Unit Contribution
headers1 = ["Tier Plan", "Billing Cadence", "Price (INR)", "Effective / Mo", "Var Cost / Mo", "Unit Contribution", "Margin %", "Annual Value"]
for col_num, h in enumerate(headers1, 1):
    cell = ws1.cell(row=4, column=col_num, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center" if col_num > 2 else "left")

plans = [
    ("Silver Monthly", "Monthly", 899, "=C5", 145, "=D5-E5", "=F5/D5", "=D5*12"),
    ("Silver Quarterly", "Quarterly", 2499, "=C6/3", 145, "=D6-E6", "=F6/D6", "=D6*12"),
    ("Silver Annual", "Annual", 8499, "=C7/12", 145, "=D7-E7", "=F7/D7", "=C7"),
    ("Gold Quarterly", "Quarterly", 4999, "=C8/3", 220, "=D8-E8", "=F8/D8", "=D8*12"),
    ("Gold Annual", "Annual", 13999, "=C9/12", 220, "=D9-E9", "=F9/D9", "=C9"),
]

for row_idx, data in enumerate(plans, start=5):
    for col_idx, val in enumerate(data, start=1):
        cell = ws1.cell(row=row_idx, column=col_idx, value=val)
        cell.font = regular_font
        cell.border = thin_border
        if col_idx in [3, 4, 5, 6, 8]:
            cell.number_format = "₹#,##0"
        elif col_idx == 7:
            cell.number_format = "0.0%"

# Section 2: Variable Cost Breakdown (Silver Monthly)
ws1.cell(row=11, column=1, value="Variable Cost Breakdown per Active Customer (Silver Plan)").font = sub_header_font
ws1.cell(row=11, column=1).fill = sub_header_fill
ws1.merge_cells("A11:D11")

v_headers = ["Cost Component", "Specification / Basis", "Monthly Cost (INR)", "Share of Price %"]
for col_num, h in enumerate(v_headers, 1):
    cell = ws1.cell(row=12, column=col_num, value=h)
    cell.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    cell.font = bold_font
    cell.border = thin_border

v_costs = [
    ("AWS Compute Allocation", "Shared ECS Fargate container pod (30-50 tenants)", 45, "=C13/899"),
    ("Gemini AI OCR Extraction", "Google Gemini 1.5 Flash tokens for 50-100 invoices", 30, "=C14/899"),
    ("Amazon SES Email Dispatch", "Transactional collection notices with DKIM (~100 emails)", 10, "=C15/899"),
    ("Payment Gateway Fee", "Razorpay / Cashfree digital checkout (~2% transaction fee)", 18, "=C16/899"),
    ("Customer Ops & Support", "Onboarding guides & ticket triage buffer", 42, "=C17/899"),
]

for r_idx, v in enumerate(v_costs, start=13):
    for c_idx, val in enumerate(v, start=1):
        cell = ws1.cell(row=r_idx, column=c_idx, value=val)
        cell.font = regular_font
        cell.border = thin_border
        if c_idx == 3:
            cell.number_format = "₹#,##0"
        elif c_idx == 4:
            cell.number_format = "0.0%"

# Total Variable Cost Row
ws1.cell(row=18, column=1, value="Total Variable Cost").font = bold_font
ws1.cell(row=18, column=1).border = thin_border
ws1.cell(row=18, column=2, value="Sum of direct servicing costs").font = italic_font
ws1.cell(row=18, column=2).border = thin_border
cell_tot = ws1.cell(row=18, column=3, value="=SUM(C13:C17)")
cell_tot.font = bold_font
cell_tot.number_format = "₹#,##0"
cell_tot.border = thin_border
cell_tot_pct = ws1.cell(row=18, column=4, value="=C18/899")
cell_tot_pct.font = bold_font
cell_tot_pct.number_format = "0.0%"
cell_tot_pct.border = thin_border

# Section 3: Break-Even & Margin of Safety
ws1.cell(row=20, column=1, value="Fixed Cost Scenarios & Break-Even Analysis").font = sub_header_font
ws1.cell(row=20, column=1).fill = sub_header_fill
ws1.merge_cells("A20:F20")

be_headers = ["Scenario", "Team Composition", "Monthly Fixed Cost", "Direct Break-Even (Customers)", "With 20% CA Referral Fee", "Margin of Safety (Yr 1-3)"]
for col_num, h in enumerate(be_headers, 1):
    cell = ws1.cell(row=21, column=col_num, value=h)
    cell.fill = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")
    cell.font = bold_font
    cell.border = thin_border

be_scenarios = [
    ("Lean Team", "Founders only (dev + sales)", 150000, "=ROUNDUP(C22/754, 0)", 230, "65.0%"),
    ("Average Team", "Founders + 3 engineers/ops", 625000, "=ROUNDUP(C23/754, 0)", 990, "74.0%"),
    ("High-End Team", "Full engineering, sales & marketing", 1430000, "=ROUNDUP(C24/754, 0)", 2260, "80.0%"),
]

for r_idx, b in enumerate(be_scenarios, start=22):
    for c_idx, val in enumerate(b, start=1):
        cell = ws1.cell(row=r_idx, column=c_idx, value=val)
        cell.font = regular_font
        cell.border = thin_border
        if c_idx == 3:
            cell.number_format = "₹#,##0"
        elif c_idx in [4, 5]:
            cell.number_format = "#,##0"

# Sheet 2: AWS Infrastructure TCO
ws2 = wb.create_sheet(title="AWS TCO")
ws2.views.sheetView[0].showGridLines = True

ws2["A1"] = "Hisaabset (LedgerLoop) — AWS Cloud Infrastructure Cost Model"
ws2["A1"].font = Font(name="Calibri", size=14, bold=True, color="0F172A")
ws2["A2"] = "Region: ap-south-1 (Mumbai) | 24/7 Serverless Container Architecture"
ws2["A2"].font = italic_font

aws_headers = ["AWS Service", "Resource Specification", "Unit Rate", "Monthly Usage", "Monthly Cost (USD)", "Monthly Cost (INR)"]
for col_num, h in enumerate(aws_headers, 1):
    cell = ws2.cell(row=4, column=col_num, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center" if col_num > 2 else "left")

aws_items = [
    ("AWS ECS Fargate vCPU", "0.5 vCPU serverless container task", "$0.04048 / vCPU-hr", "365 vCPU-hrs (730 hrs * 0.5)", 14.78, "=E5*83"),
    ("AWS ECS Fargate Memory", "1.0 GB RAM allocated to task", "$0.004445 / GB-hr", "730 GB-hrs", 3.25, "=E6*83"),
    ("AWS ECR Container Registry", "Private Docker image storage", "$0.10 / GB-mo", "2.0 GB image", 0.20, "=E7*83"),
    ("Amazon Simple Email Service (SES)", "Transactional collection notice dispatch", "$0.10 / 1,000 emails", "2,500 emails / mo", 0.25, "=E8*83"),
    ("Amazon CloudWatch Logs", "Container logs & health telemetry", "$0.50 / GB ingested", "5.0 GB log stream", 2.68, "=E9*83"),
    ("AWS VPC & Data Transfer Out", "Outbound web application traffic", "$0.09 / GB after 100 GB free", "~10 GB egress", 1.00, "=E10*83"),
]

for r_idx, item in enumerate(aws_items, start=5):
    for c_idx, val in enumerate(item, start=1):
        cell = ws2.cell(row=r_idx, column=c_idx, value=val)
        cell.font = regular_font
        cell.border = thin_border
        if c_idx == 5:
            cell.number_format = "$#,##0.00"
        elif c_idx == 6:
            cell.number_format = "₹#,##0"

# AWS Total
ws2.cell(row=11, column=1, value="TOTAL AWS CLOUD TCO").font = bold_font
ws2.cell(row=11, column=1).border = thin_border
ws2.cell(row=11, column=2, value="24/7 Continuous Base Container Pod").font = bold_font
ws2.cell(row=11, column=2).border = thin_border
ws2.cell(row=11, column=3, value="USD / INR @ 83.0").font = italic_font
ws2.cell(row=11, column=3).border = thin_border
ws2.cell(row=11, column=4, value="730 Hours Continuous").font = italic_font
ws2.cell(row=11, column=4).border = thin_border

cell_tot_usd = ws2.cell(row=11, column=5, value="=SUM(E5:E10)")
cell_tot_usd.font = bold_font
cell_tot_usd.number_format = "$#,##0.00"
cell_tot_usd.border = thin_border

cell_tot_inr = ws2.cell(row=11, column=6, value="=SUM(F5:F10)")
cell_tot_inr.font = bold_font
cell_tot_inr.number_format = "₹#,##0"
cell_tot_inr.border = thin_border

# Sheet 3: 30-Day GTM Plan
ws3 = wb.create_sheet(title="30-Day GTM Sprint")
ws3.views.sheetView[0].showGridLines = True

ws3["A1"] = "Hisaabset (LedgerLoop) — 30-Day Go-To-Market Proof Sprint"
ws3["A1"].font = Font(name="Calibri", size=14, bold=True, color="0F172A")
ws3["A2"] = "Target: 20 Paying Customers | CAC < ₹3,000 | Blended Billing ₹1.0 Lakh+"
ws3["A2"].font = italic_font

gtm_headers = ["Sprint Week", "Strategic Objective", "Primary Channels & Moves", "Target Conversations", "Waitlist / Trials", "Paid Conversions", "Cumulative Revenue"]
for col_num, h in enumerate(gtm_headers, 1):
    cell = ws3.cell(row=4, column=col_num, value=h)
    cell.fill = header_fill
    cell.font = header_font
    cell.alignment = Alignment(horizontal="center" if col_num > 3 else "left")

gtm_data = [
    ("Week 1: Prove & Prepare", "20 customer interviews, landing page & late-payment calculator", "Direct founder outreach to local FMCG distributors", 20, 30, 2, "₹17,000"),
    ("Week 2: Seed with Trust", "Partner onboarding & CA referral network launch (15% referral fee)", "Pitch 10 CAs, LinkedIn post series on MSME 45-day payment rule", 15, 45, 5, "₹42,500"),
    ("Week 3: Public Launch", "Founding offer launch: first 100 get price locked for 2 years", "IndiaMART banner, LinkedIn demo video, WhatsApp community demo", 15, 40, 6, "₹76,500"),
    ("Week 4: Convert & Scale", "Free overdue invoice audit offer, daily follow-ups with warmest leads", "Follow up 150 trials, test annual vs quarterly plan mix", 10, 35, 7, "₹1,10,000"),
]

for r_idx, g in enumerate(gtm_data, start=5):
    for c_idx, val in enumerate(g, start=1):
        cell = ws3.cell(row=r_idx, column=c_idx, value=val)
        cell.font = regular_font
        cell.border = thin_border
        if c_idx in [4, 5, 6]:
            cell.number_format = "#,##0"

# Auto-fit column widths across all sheets
for sheet in [ws1, ws2, ws3]:
    for col in sheet.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            val_str = str(cell.value or '')
            if len(val_str) > max_len and not val_str.startswith("="):
                max_len = len(val_str)
        sheet.column_dimensions[col_letter].width = max(max_len + 4, 12)

excel_path = "docs/economics.xlsx"
wb.save(excel_path)
print(f"SUCCESS: Created editable Excel model at {excel_path}")
