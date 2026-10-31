"""
service_reports.py
===========================================================
T&J THINK BIG MINING ENTERPRISE OS — Service PDF reports.
Reads from System_ServiceTransactions + System_Services.
For each service shows: # Clients, Price/Client, Total Revenue.
Summary: Total Clients, Total Revenue, Top/Least Service.
Functions: create_service_daily/weekly/monthly/yearly_report
===========================================================
"""

import os
from datetime import datetime, timedelta, date

from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.units import inch

import system_db
from helpers import get_company_header, get_signatures, get_report_submitter

# Colors (reuse classic palette)
COLOR_BLUE = colors.HexColor("#4472C4")
COLOR_ORANGE = colors.HexColor("#FFC000")
COLOR_GREEN = colors.HexColor("#E2EFDA")
COLOR_LIGHTBLUE = colors.HexColor("#DDEBF7")
COLOR_GREY_HEAD = colors.HexColor("#F2F2F2")

_styles = getSampleStyleSheet()

report_title_style = ParagraphStyle(
    "SvcReportTitle", parent=_styles["Heading2"],
    alignment=TA_CENTER, fontSize=10, spaceAfter=5,
)
summary_title_style = ParagraphStyle(
    "SvcSumTitle", parent=_styles["Normal"],
    fontSize=10, fontName="Helvetica-Bold", alignment=TA_CENTER,
)
footer_text_style = ParagraphStyle(
    "SvcFooterText", parent=_styles["Normal"],
    alignment=TA_CENTER, fontSize=8, spaceAfter=10,
)
igihe_style = ParagraphStyle(
    "SvcIgihe", parent=_styles["Normal"],
    alignment=TA_CENTER, fontSize=7, textColor=colors.grey,
)
hdr_white = ParagraphStyle(
    "SvcHdrWhite", parent=_styles["Normal"],
    fontName="Helvetica-Bold", fontSize=9, leading=11,
    textColor=colors.white, alignment=TA_CENTER,
)
hdr_dark = ParagraphStyle(
    "SvcHdrDark", parent=_styles["Normal"],
    fontName="Helvetica-Bold", fontSize=9, leading=11,
    textColor=colors.black, alignment=TA_CENTER,
)
cell_small = ParagraphStyle(
    "SvcCell", parent=_styles["Normal"],
    fontName="Helvetica", fontSize=8, leading=10,
    textColor=colors.black, alignment=TA_CENTER,
)
cell_left = ParagraphStyle(
    "SvcCellL", parent=_styles["Normal"],
    fontName="Helvetica", fontSize=8, leading=10,
    textColor=colors.black, alignment=TA_LEFT,
)


def _ensure_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def _fmt_money(v):
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return str(v)


def _load_service_txs():
    return system_db._batch_read_tabs([
        "System_ServiceTransactions",
        "System_Services",
    ])


def _aggregate_service_txs(svc_txs, period_days_iso):
    """
    Returns dict keyed by service_name with {clients, revenue, count, last_price}
    only for txs whose created_at falls within period_days_iso set.
    """
    period_set = set(period_days_iso)
    by_service = {}
    for t in svc_txs:
        ca = str(t.get("created_at", ""))
        day = ca[:10] if ca else ""
        if period_days_iso and day not in period_set:
            continue
        key = t.get("service_name", "Unknown")
        if key not in by_service:
            by_service[key] = {
                "name": key,
                "clients": 0,
                "revenue": 0.0,
                "count": 0,
                "last_price": 0.0,
            }
        rec = by_service[key]
        rec["clients"] += system_db._to_int(t.get("num_clients", 0))
        rec["revenue"] += system_db._to_float(t.get("total_amount", 0))
        rec["count"] += 1
        ppc = system_db._to_float(t.get("price_per_client", 0))
        if ppc > 0:
            rec["last_price"] = ppc
    return by_service


def _build_service_table(by_service):
    """8-column service table."""
    table_data = [
        [Paragraph("SERVICE", hdr_white),
         Paragraph("# CLIENTS", hdr_dark),
         Paragraph("PRICE / CLIENT", hdr_dark),
         Paragraph("TOTAL REVENUE", hdr_dark),
         Paragraph("# TRANSACTIONS", hdr_dark)],
    ]
    total_clients = 0
    total_revenue = 0.0
    total_count = 0
    for s in sorted(by_service.values(), key=lambda x: x["revenue"], reverse=True):
        table_data.append([
            Paragraph(s["name"], cell_left),
            str(s["clients"]),
            _fmt_money(s["last_price"]),
            _fmt_money(s["revenue"]),
            str(s["count"]),
        ])
        total_clients += s["clients"]
        total_revenue += s["revenue"]
        total_count += s["count"]
    table_data.append([
        Paragraph("TOTAL", hdr_dark),
        str(total_clients), "",
        _fmt_money(total_revenue),
        str(total_count),
    ])
    col_widths = [2.5 * inch, 1.4 * inch, 1.6 * inch, 1.8 * inch, 1.8 * inch]
    n_rows = len(table_data)
    last = n_rows - 1
    t = Table(table_data, colWidths=col_widths)
    style = [
        ("BACKGROUND", (0, 0), (0, 0), COLOR_BLUE),
        ("BACKGROUND", (1, 0), (-1, 0), COLOR_ORANGE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 1), (0, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 1), (-1, -1), COLOR_GREEN),
        ("BACKGROUND", (0, last), (-1, last), COLOR_ORANGE),
        ("FONTNAME", (0, last), (-1, last), "Helvetica-Bold"),
    ]
    t.setStyle(TableStyle(style))
    return t, total_clients, total_revenue, total_count


def _build_summary(title, total_clients, total_revenue, top, least, total_count):
    data = [
        ["IKIGERERANYO (METRIC)", "AGACIRO (VALUE)"],
        ["Abakiriya Bose (Total Clients)", f"{total_clients:,.0f}"],
        ["Amafaranga Yose Yinjiye (Total Revenue)", f"{total_revenue:,.0f} RWF"],
        ["Ibikorwa Byakozwe (Total Transactions)", f"{total_count:,.0f}"],
        ["Serivisi Yakunzwe Cyane (Top Service)", top or "N/A"],
        ["Serivisi Y'ingenzi (Least Service)", least or "N/A"],
    ]
    t = Table(data, colWidths=[4.5 * inch, 3 * inch])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), COLOR_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F9F9F9")),
    ]))
    return [Paragraph(title, summary_title_style), Spacer(1, 5), t]


def _collect_svc_emp_names(svc_txs):
    """Collect unique employee names from service transactions."""
    names = []
    seen = set()
    for t in svc_txs or []:
        nm = str(t.get("employee_name", "") or "").strip()
        if nm and nm.lower() not in seen:
            seen.add(nm.lower())
            names.append(nm)
    return names


def _get_approver_for_employees(employee_names):
    """Look up the approver assigned to employees who made transactions."""
    import json, os
    try:
        emp_approvers_path = os.path.join(os.path.dirname(__file__), "employee_approvers.json")
        with open(emp_approvers_path, 'r') as f:
            emp_approvers = json.load(f)
        approvers_path = os.path.join(os.path.dirname(__file__), "approvers.json")
        with open(approvers_path, 'r') as f:
            approvers = json.load(f).get("approvers", [])
        # Load users
        try:
            import system_db
            users = system_db.list_users()
        except:
            users = []
        for name in employee_names:
            emp_id = None
            for u in users:
                if str(u.get("name", "")).lower() == name.lower():
                    emp_id = u.get("id")
                    break
            if emp_id and emp_id in emp_approvers:
                approver_id = emp_approvers[emp_id]
                for a in approvers:
                    if a.get("id") == approver_id:
                        return a.get("name", ""), a.get("phone", "")
        for a in approvers:
            if a.get("is_default"):
                return a.get("name", ""), a.get("phone", "")
        if approvers:
            return approvers[0].get("name", ""), approvers[0].get("phone", "")
    except:
        pass
    return None, None


def _footer_block(title_text, employee_names=None):
    """New footer: uses helpers.get_report_footer — same as reports_classic.
    Includes employee (bottom-left), approver (bottom-right), digital
    signature image, and QR code with Google Drive link."""
    try:
        from helpers import get_report_footer
        return [get_report_footer(employee_names=employee_names, title_text=title_text)]
    except Exception as e:
        print(f"[service_reports] get_report_footer failed, fallback: {e}")
        out = []
        out.append(Spacer(1, 10))
        out.append(Paragraph(f"<b>{title_text}</b>", footer_text_style))
        ubu_gihe = datetime.now()
        out.append(Paragraph(
            f"<i>(Raporo yakozwe kuwa {ubu_gihe.strftime('%d/%m/%Y')} "
            f"saa {ubu_gihe.strftime('%H:%M')})</i>",
            igihe_style,
        ))
        out.append(Spacer(1, 20))
        out.append(get_signatures())
        ap_name, ap_phone = None, None
        if employee_names:
            ap_name, ap_phone = _get_approver_for_employees(employee_names)
        out.append(get_report_submitter(employee_names, approver_name=ap_name, approver_phone=ap_phone))
        return out


def _common_create(label, period_days_iso, output_pdf, header_subtitle):
    _ensure_folder(os.path.dirname(output_pdf))
    batch = _load_service_txs()
    svc_txs = batch.get("System_ServiceTransactions", [])
    by_service = _aggregate_service_txs(svc_txs, period_days_iso)
    table, total_clients, total_revenue, total_count = _build_service_table(by_service)
    if by_service:
        top = max(by_service.values(), key=lambda x: x["revenue"])["name"]
        least = min(by_service.values(), key=lambda x: x["revenue"])["name"]
    else:
        top = "N/A"
        least = "N/A"

    doc = SimpleDocTemplate(
        output_pdf, pagesize=landscape(A4),
        rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15,
    )
    elements = [get_company_header(),
                Paragraph("<hr/>", _styles["Normal"]),
                Spacer(1, 5)]
    elements.append(Paragraph(f"<b>{label}</b>", report_title_style))
    elements.append(Paragraph(header_subtitle, igihe_style))
    elements.append(Spacer(1, 10))
    elements.append(table)
    elements.append(Spacer(1, 15))
    for el in _build_summary(
        f"<b>INCAMAKE YA SERIVISI (SUMMARY)</b>",
        total_clients, total_revenue, top, least, total_count,
    ):
        elements.append(el)
    for el in _footer_block("BIKOREWE MU Ruhango", employee_names=_collect_svc_emp_names(svc_txs)):
        elements.append(el)
    doc.build(elements)
    print(f"✅ {label} PDF saved: {output_pdf}")
    return output_pdf


# ---------------------------------------------------------
# Public entry points
# ---------------------------------------------------------
def create_service_daily_report(output_folder="reports", target_date=None):
    if target_date is None:
        target = date.today()
    else:
        target = datetime.fromisoformat(target_date).date()
    days_iso = [target.isoformat()]
    output_pdf = os.path.join(
        output_folder,
        f"Service_Daily_Report_{target.isoformat()}.pdf",
    )
    header = f"Date: {target.strftime('%d/%m/%Y')}"
    return _common_create(
        "SERVICE DAILY REPORT", days_iso, output_pdf, header
    )


def create_service_weekly_report(output_folder="reports", target_date=None):
    if target_date is None:
        target = date.today()
    else:
        target = datetime.fromisoformat(target_date).date()
    start = target - timedelta(days=target.weekday())
    days = [(start + timedelta(days=i)) for i in range(7)]
    days_iso = [d.isoformat() for d in days]
    output_pdf = os.path.join(
        output_folder,
        f"Service_Weekly_Report_{start.isoformat()}.pdf",
    )
    end = (start + timedelta(days=6)).strftime("%d/%m/%Y")
    header = f"Period: {start.strftime('%d/%m/%Y')} - {end}"
    return _common_create(
        "SERVICE WEEKLY REPORT", days_iso, output_pdf, header
    )


def create_service_monthly_report(output_folder="reports", target_date=None):
    if target_date is None:
        target = date.today().replace(day=1)
    else:
        target = datetime.fromisoformat(target_date).date().replace(day=1)
    next_month = (target.replace(day=28) + timedelta(days=4)).replace(day=1)
    days = []
    d = target
    while d < next_month:
        days.append(d)
        d += timedelta(days=1)
    days_iso = [d.isoformat() for d in days]
    output_pdf = os.path.join(
        output_folder,
        f"Service_Monthly_Report_{target.strftime('%Y-%m')}.pdf",
    )
    header = f"Period: {target.strftime('%B %Y')}"
    return _common_create(
        "SERVICE MONTHLY REPORT", days_iso, output_pdf, header
    )


def create_service_yearly_report(output_folder="reports", target_date=None):
    if target_date is None:
        year = date.today().year
    else:
        year = datetime.fromisoformat(target_date).date().year
    days = []
    d = date(year, 1, 1)
    while d.year == year:
        days.append(d.isoformat())
        d += timedelta(days=1)
    output_pdf = os.path.join(output_folder, f"Service_Yearly_Report_{year}.pdf")
    header = f"Period: Year {year}"
    return _common_create(
        "SERVICE YEARLY REPORT", days, output_pdf, header
    )


if __name__ == "__main__":
    create_service_daily_report()
    create_service_weekly_report()
    create_service_monthly_report()
    create_service_yearly_report()
