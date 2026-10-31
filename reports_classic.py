"""
reports_classic.py
===========================================================
T&J THINK BIG MINING ENTERPRISE OS — Product PDF reports
Generated from System_Products + System_Transactions +
System_TransactionItems (read via batch read).

Formats:
  - Daily    : 8-column layout (DETAILS | TOTAL STOCK | UNIT PRICE |
               TOTAL SOLD | UNIT PRICE | SOLD AMOUNT | CURRENT STOCK |
               PROFIT/LOSS)
  - Weekly   : WIDE multi-day format split into BLOCKS of 5 days
               to fit A4 landscape
  - Monthly  : WIDE multi-day format split into BLOCKS of 5 days
  - Yearly   : WIDE multi-month format split into BLOCKS of 6 months

Colors:
  - Blue   #4472C4 for DETAILS
  - Orange #FFC000 for STOCK YOSE
  - Green  #E2EFDA for IBYAGURISHIJWE
  - LightBlue #DDEBF7 for IBYASIGAYE
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

# ---------------------------------------------------------
# Colors
# ---------------------------------------------------------
COLOR_BLUE = colors.HexColor("#4472C4")
COLOR_ORANGE = colors.HexColor("#FFC000")
COLOR_GREEN = colors.HexColor("#E2EFDA")
COLOR_LIGHTBLUE = colors.HexColor("#DDEBF7")
COLOR_GREY_HEAD = colors.HexColor("#F2F2F2")
COLOR_TOTAL_BG = colors.HexColor("#FFC000")
COLOR_GENERAL_BG = colors.HexColor("#FFC000")
COLOR_GENERAL_HL = colors.HexColor("#4472C4")

# ---------------------------------------------------------
# Styles
# ---------------------------------------------------------
_styles = getSampleStyleSheet()

report_title_style = ParagraphStyle(
    "ReportTitle", parent=_styles["Heading2"],
    alignment=TA_CENTER, fontSize=10, spaceAfter=5,
)
summary_title_style = ParagraphStyle(
    "SumTitle", parent=_styles["Normal"],
    fontSize=10, fontName="Helvetica-Bold", alignment=TA_CENTER,
)
footer_text_style = ParagraphStyle(
    "FooterText", parent=_styles["Normal"],
    alignment=TA_CENTER, fontSize=8, spaceAfter=10,
)
igihe_style = ParagraphStyle(
    "IgiheStyle", parent=_styles["Normal"],
    alignment=TA_CENTER, fontSize=7, textColor=colors.grey,
)
hdr_white = ParagraphStyle(
    "HdrWhite", parent=_styles["Normal"],
    fontName="Helvetica-Bold", fontSize=8, leading=10,
    textColor=colors.white, alignment=TA_CENTER,
)
hdr_dark = ParagraphStyle(
    "HdrDark", parent=_styles["Normal"],
    fontName="Helvetica-Bold", fontSize=8, leading=10,
    textColor=colors.black, alignment=TA_CENTER,
)
hdr_small = ParagraphStyle(
    "HdrSmall", parent=_styles["Normal"],
    fontName="Helvetica-Bold", fontSize=6.5, leading=8,
    textColor=colors.black, alignment=TA_CENTER,
)
cell_small = ParagraphStyle(
    "CellSmall", parent=_styles["Normal"],
    fontName="Helvetica", fontSize=6.5, leading=8,
    textColor=colors.black, alignment=TA_CENTER,
)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------
def _fmt_money(v):
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return str(v)


def _fmt_qty(v):
    try:
        return f"{float(v):,.0f}"
    except Exception:
        return str(v)


def _ensure_folder(folder):
    if not os.path.exists(folder):
        os.makedirs(folder)


def _load_product_data():
    """Batch-read everything we need in one go."""
    batch = system_db._batch_read_tabs([
        "System_Products",
        "System_Transactions",
        "System_TransactionItems",
    ])
    products = batch.get("System_Products", [])
    txs = batch.get("System_Transactions", [])
    items = batch.get("System_TransactionItems", [])
    return products, txs, items


def _aggregate_sales_by_day(txs, items, days_iso):
    """
    Returns: dict[product_id] -> dict[day_iso] -> {qty, unit_price, total, cost, profit}
    """
    # Index transaction items by transaction_id
    items_by_tx = {}
    for it in items:
        tid = it.get("transaction_id", "")
        items_by_tx.setdefault(tid, []).append(it)

    # Index transactions by date
    txs_by_date = {}
    for t in txs:
        ca = str(t.get("created_at", ""))
        if not ca:
            continue
        day = ca[:10]
        txs_by_date.setdefault(day, []).append(t)

    # product_id -> day -> aggregations
    result = {}
    for day in days_iso:
        day_txs = txs_by_date.get(day, [])
        for t in day_txs:
            if str(t.get("type", "")).upper() != "SALE":
                continue
            tid = t.get("id", "")
            for it in items_by_tx.get(tid, []):
                pid = it.get("product_id", "")
                if not pid:
                    continue
                if pid not in result:
                    result[pid] = {d: {"qty": 0, "unit_price": 0.0, "total": 0.0, "cost": 0.0} for d in days_iso}
                qty = system_db._to_int(it.get("quantity", 0))
                up = system_db._to_float(it.get("unit_price", 0))
                cp = system_db._to_float(it.get("cost_price", 0))
                sub = system_db._to_float(it.get("subtotal", 0))
                rec = result[pid][day]
                rec["qty"] += qty
                rec["total"] += sub
                rec["cost"] += qty * cp
                if up > 0:
                    rec["unit_price"] = up
    return result


def _build_summary_block(title, total_sales, total_profit, top_product, top_qty):
    profit_text = (
        f"{total_profit:,.0f} RWF" if total_profit >= 0
        else f"{total_profit:,.0f} RWF (Igihombo)"
    )
    summary_data = [
        ["IKIGERERANYO (METRIC)", "AGACIRO (VALUE)"],
        ["Amafaranga Yose Yinjiye (Total Sales)", f"{total_sales:,.0f} RWF"],
        ["Inyungu Yose Hamwe (Total Profit/Loss)", profit_text],
        ["Igicuruzwa Cyaguzwe Cyane", f"{top_product} ({top_qty:,.0f})"],
    ]
    t = Table(summary_data, colWidths=[4.5 * inch, 3 * inch])
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


def _collect_emp_names_from_txs(txs, target=None, days_iso=None):
    """Collect unique employee names from transactions in the report."""
    names = []
    seen = set()
    for t in txs or []:
        nm = str(t.get("employee_name", "") or "").strip()
        if nm and nm.lower() not in seen:
            seen.add(nm.lower())
            names.append(nm)
    return names


def _get_approver_for_employees(employee_names):
    """Look up the approver assigned to employees who made transactions.
    Reads employee_approvers.json + approvers.json.
    Returns (approver_name, approver_phone)."""
    import json, os
    try:
        emp_approvers_path = os.path.join(os.path.dirname(__file__), "employee_approvers.json")
        with open(emp_approvers_path, 'r') as f:
            emp_approvers = json.load(f)
        approvers_path = os.path.join(os.path.dirname(__file__), "approvers.json")
        with open(approvers_path, 'r') as f:
            approvers = json.load(f).get("approvers", [])
        # Load users to find employee IDs by name
        import system_db
        users = system_db.list_users()
        # Find approver for first matching employee
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
        # Fallback: default approver
        for a in approvers:
            if a.get("is_default"):
                return a.get("name", ""), a.get("phone", "")
        if approvers:
            return approvers[0].get("name", ""), approvers[0].get("phone", "")
    except:
        pass
    return None, None


def _footer_block(title_text, employee_names=None):
    """New footer: uses helpers.get_report_footer which includes
    employee (bottom-left, with phone+position), approver (bottom-right,
    with phone+title), digital signature image, and QR code with Google
    Drive link."""
    try:
        from helpers import get_report_footer
        return [get_report_footer(employee_names=employee_names, title_text=title_text)]
    except Exception as e:
        print(f"[reports_classic] get_report_footer failed, fallback: {e}")
        # Fallback to old behavior
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


# =========================================================
# DAILY REPORT — 8-column
# =========================================================
def create_daily_report(output_folder="reports", target_date=None):
    """
    target_date: ISO date string (YYYY-MM-DD) or None for today.
    """
    _ensure_folder(output_folder)
    if target_date is None:
        target_date = date.today().isoformat()
    target = datetime.fromisoformat(target_date).date()

    products, txs, items = _load_product_data()

    # Sales for the target day
    sales_by_pid = _aggregate_sales_by_day(txs, items, [target.isoformat()])
    day_sales = {pid: data[target.isoformat()] for pid, data in sales_by_pid.items()}

    amazina_yiminsi = [
        "kuwambere", "kuwakabiri", "kuwagatatu", "kuwakane",
        "kuwagatanu", "kuwagatandatu", "kucyumweru",
    ]
    izina_ry_umunsi = amazina_yiminsi[target.weekday()]

    output_pdf = os.path.join(
        output_folder,
        f"Daily_Report_{izina_ry_umunsi}_{target.isoformat()}.pdf",
    )

    doc = SimpleDocTemplate(
        output_pdf, pagesize=landscape(A4),
        rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15,
    )

    elements = [get_company_header(),
                Paragraph("<hr/>", _styles["Normal"]),
                Spacer(1, 5)]
    elements.append(Paragraph(
        f"<b>DAILY REPORT - {target.strftime('%m/%d/%Y')} ({izina_ry_umunsi.capitalize()})</b>",
        report_title_style,
    ))

    # Build 8-column table
    table_data = [
        [
            Paragraph("DETAILS", hdr_white),
            Paragraph("STOCK YOSE", hdr_dark), "",
            Paragraph("IBYAGURISHIJWE", hdr_dark), "", "",
            Paragraph("IBYASIGAYE MURI STOCK", hdr_dark), "",
        ],
        [
            "",
            Paragraph("TOTAL STOCK", hdr_dark),
            Paragraph("UNIT PRICE", hdr_dark),
            Paragraph("TOTAL SOLD", hdr_dark),
            Paragraph("UNIT PRICE", hdr_dark),
            Paragraph("SOLD AMOUNT", hdr_dark),
            Paragraph("CURRENT STOCK", hdr_dark),
            Paragraph("PROFIT/LOSS", hdr_dark),
        ],
    ]

    col_widths = [
        1.6 * inch, 1.1 * inch, 1.1 * inch,
        1.1 * inch, 1.1 * inch, 1.2 * inch,
        1.3 * inch, 1.3 * inch,
    ]

    table_styles = [
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BACKGROUND", (0, 0), (0, 1), COLOR_BLUE),
        ("BACKGROUND", (1, 0), (2, 0), COLOR_ORANGE),
        ("BACKGROUND", (3, 0), (5, 0), COLOR_GREEN),
        ("BACKGROUND", (6, 0), (7, 0), COLOR_LIGHTBLUE),
        ("BACKGROUND", (1, 1), (-1, 1), COLOR_GREY_HEAD),
        ("SPAN", (0, 0), (0, 1)),
        ("SPAN", (1, 0), (2, 0)),
        ("SPAN", (3, 0), (5, 0)),
        ("SPAN", (6, 0), (7, 0)),
    ]

    total_sales = 0.0
    total_profit = 0.0
    top_qty = 0
    top_product = "Nta gicuruzwa"

    row_num = 2
    for p in products:
        if str(p.get("hidden", "FALSE")).upper() in ("TRUE", "1", "YES"):
            continue
        pid = p.get("id", "")
        name = p.get("name", "")
        total_stock = system_db._to_int(p.get("quantity", 0))
        unit_price = system_db._to_float(p.get("unit_price", 0))
        cost_price = system_db._to_float(p.get("cost_price", 0))

        sold = day_sales.get(pid, {"qty": 0, "unit_price": 0.0, "total": 0.0, "cost": 0.0})
        qty_sold = sold["qty"]
        sold_amount = sold["total"]
        sold_cost = sold["cost"]
        profit = sold_amount - sold_cost
        current_stock = max(0, total_stock)  # already decremented by tx layer

        row = [
            name,
            _fmt_qty(total_stock),
            _fmt_money(unit_price),
            _fmt_qty(qty_sold) if qty_sold > 0 else "",
            _fmt_money(sold["unit_price"]) if qty_sold > 0 else "",
            _fmt_money(sold_amount) if sold_amount > 0 else "",
            _fmt_qty(current_stock),
            _fmt_money(profit) if qty_sold > 0 else "",
        ]
        table_data.append(row)

        total_sales += sold_amount
        total_profit += profit
        if qty_sold > top_qty:
            top_qty = qty_sold
            top_product = name
        row_num += 1

    # GENERAL TOTAL row
    table_data.append([
        "GENERAL TOTAL", "", "", "", "",
        _fmt_money(total_sales), "", _fmt_money(total_profit),
    ])
    table_styles.append(("SPAN", (0, row_num), (4, row_num)))
    table_styles.append(("BACKGROUND", (0, row_num), (-1, row_num), COLOR_TOTAL_BG))
    table_styles.append(("BACKGROUND", (5, row_num), (5, row_num), COLOR_GENERAL_HL))
    table_styles.append(("TEXTCOLOR", (5, row_num), (5, row_num), colors.white))
    table_styles.append(("FONTNAME", (0, row_num), (-1, row_num), "Helvetica-Bold"))

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle(table_styles))
    elements.append(table)

    # Summary block
    elements.append(Spacer(1, 15))
    for el in _build_summary_block(
        "<b>INCAMAKE Y'UMUNSI (DAILY SUMMARY)</b>",
        total_sales, total_profit, top_product, top_qty,
    ):
        elements.append(el)
    for el in _footer_block("BIKOREWE MU Ruhango", employee_names=_collect_emp_names_from_txs(txs)):
        elements.append(el)

    doc.build(elements)
    print(f"✅ Daily PDF saved: {output_pdf}")
    return output_pdf


# =========================================================
# WIDE FORMAT HELPERS (weekly/monthly/yearly)
# =========================================================
def _build_wide_table(block_days, products, sales_by_pid, day_labels, period_label):
    """
    block_days: list of ISO strings for THIS block only
    day_labels: list of short labels aligned with block_days
    products: list of product dicts
    sales_by_pid: full dict pid -> {day_iso: {...}}
    period_label: 'WEEKLY' | 'MONTHLY' | 'YEARLY'
    """
    n_days = len(block_days)

    # Header row 1: PRODUCT | day labels (span 3) | TOTAL (span 3)
    header_row1 = [Paragraph("PRODUCTS", hdr_white)]
    for lbl in day_labels:
        header_row1.append(Paragraph(lbl, hdr_small))
        header_row1.append("")
        header_row1.append("")
    header_row1.append(Paragraph("TOTAL", hdr_white))
    header_row1.append("")
    header_row1.append("")

    # Header row 2: blank | Qty/Price/Total for each day | Qty/Price/Total for total
    header_row2 = [""]
    for _ in range(n_days):
        header_row2 += [Paragraph("Qty", hdr_small), Paragraph("Price", hdr_small), Paragraph("Total", hdr_small)]
    header_row2 += [Paragraph("Qty", hdr_small), Paragraph("Price", hdr_small), Paragraph("Total", hdr_small)]

    table_data = [header_row1, header_row2]

    table_styles = [
        ("BACKGROUND", (0, 0), (0, 1), COLOR_BLUE),
        ("TEXTCOLOR", (0, 0), (0, 1), colors.white),
        ("BACKGROUND", (1, 0), (-1, 0), COLOR_ORANGE),
        ("BACKGROUND", (1, 1), (-1, 1), COLOR_GREY_HEAD),
        ("FONTNAME", (0, 0), (-1, 1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("SPAN", (0, 0), (0, 1)),
    ]
    # Spans for each day in the block
    for i in range(n_days):
        start_col = 1 + (i * 3)
        end_col = start_col + 2
        table_styles.append(("SPAN", (start_col, 0), (end_col, 0)))
    # Total span
    total_start = 1 + n_days * 3
    total_end = total_start + 2
    table_styles.append(("SPAN", (total_start, 0), (total_end, 0)))

    # Column widths
    col_widths = [1.25 * inch]
    for _ in range(n_days):
        col_widths += [0.32 * inch, 0.38 * inch, 0.41 * inch]
    col_widths += [0.42 * inch, 0.45 * inch, 0.55 * inch]

    grand_qty = 0
    grand_total = 0.0
    product_revenue = {}
    row_num = 2

    for p in products:
        if str(p.get("hidden", "FALSE")).upper() in ("TRUE", "1", "YES"):
            continue
        pid = p.get("id", "")
        name = p.get("name", "")
        row = [Paragraph(name[:30], cell_small)]
        prod_qty = 0
        prod_total = 0.0
        last_price = 0.0
        for d in block_days:
            data = sales_by_pid.get(pid, {}).get(d, {"qty": 0, "unit_price": 0.0, "total": 0.0})
            qty = data["qty"]
            price = data["unit_price"]
            total = data["total"]
            row.append(Paragraph(_fmt_qty(qty) if qty > 0 else "", cell_small))
            row.append(Paragraph(_fmt_money(price) if qty > 0 else "", cell_small))
            row.append(Paragraph(_fmt_money(total) if total > 0 else "", cell_small))
            prod_qty += qty
            prod_total += total
            if price > 0:
                last_price = price
        row.append(Paragraph(_fmt_qty(prod_qty) if prod_qty > 0 else "", cell_small))
        row.append(Paragraph(_fmt_money(last_price) if last_price > 0 else "", cell_small))
        row.append(Paragraph(_fmt_money(prod_total) if prod_total > 0 else "", cell_small))
        table_data.append(row)
        grand_qty += prod_qty
        grand_total += prod_total
        product_revenue[name] = prod_total
        row_num += 1

    # General total row
    total_row = [Paragraph("GENERAL TOTAL", hdr_small)]
    total_row += [""] * (n_days * 3)
    total_row += [
        Paragraph(_fmt_qty(grand_qty), hdr_small),
        "",
        Paragraph(_fmt_money(grand_total), hdr_small),
    ]
    table_data.append(total_row)
    # Spans
    total_span_end = 1 + n_days * 3 - 1  # last day col end
    table_styles.append(("SPAN", (0, row_num), (total_span_end, row_num)))
    table_styles.append(("BACKGROUND", (0, row_num), (-1, row_num), COLOR_GENERAL_BG))
    table_styles.append(("BACKGROUND", (total_start, row_num), (total_end, row_num), COLOR_GENERAL_HL))
    table_styles.append(("TEXTCOLOR", (total_start, row_num), (total_end, row_num), colors.white))
    table_styles.append(("FONTNAME", (0, row_num), (-1, row_num), "Helvetica-Bold"))

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle(table_styles))
    return table, grand_qty, grand_total, product_revenue


# =========================================================
# WEEKLY REPORT (blocks of 5 days)
# =========================================================
def create_weekly_report(output_folder="reports", target_date=None):
    _ensure_folder(output_folder)
    if target_date is None:
        target = date.today()
    else:
        target = datetime.fromisoformat(target_date).date()
    # Start of the week (Monday)
    start_of_week = target - timedelta(days=target.weekday())
    days = [(start_of_week + timedelta(days=i)) for i in range(7)]
    days_iso = [d.isoformat() for d in days]
    day_labels = [d.strftime("Day %d") for d in days]

    products, txs, items = _load_product_data()
    sales_by_pid = _aggregate_sales_by_day(txs, items, days_iso)

    start_str = start_of_week.strftime("%d/%m/%Y")
    end_str = (start_of_week + timedelta(days=6)).strftime("%d/%m/%Y")
    output_pdf = os.path.join(
        output_folder,
        f"Weekly_Report_{start_of_week.isoformat()}.pdf",
    )
    doc = SimpleDocTemplate(
        output_pdf, pagesize=landscape(A4),
        rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10,
    )
    elements = [get_company_header(),
                Paragraph("<hr/>", _styles["Normal"]),
                Spacer(1, 5)]
    elements.append(Paragraph(
        f"<b>WEEKLY REPORT - ({start_str} - {end_str})</b>",
        report_title_style,
    ))
    elements.append(Spacer(1, 5))

    # Split into blocks of 5 days
    block_size = 5
    grand_qty = 0
    grand_total = 0.0
    product_revenue = {}
    for bi in range(0, len(days), block_size):
        block_days = days_iso[bi:bi + block_size]
        block_labels = day_labels[bi:bi + block_size]
        if not block_days:
            break
        elements.append(Paragraph(
            f"<b>Block {bi // block_size + 1}: "
            f"{datetime.fromisoformat(block_days[0]).strftime('%d/%m')} - "
            f"{datetime.fromisoformat(block_days[-1]).strftime('%d/%m/%Y')}</b>",
            summary_title_style,
        ))
        elements.append(Spacer(1, 3))
        tbl, q, tot, rev = _build_wide_table(
            block_days, products, sales_by_pid, block_labels, "WEEKLY"
        )
        elements.append(tbl)
        grand_qty += q
        grand_total += tot
        for k, v in rev.items():
            product_revenue[k] = product_revenue.get(k, 0) + v
        elements.append(Spacer(1, 10))

    top = max(product_revenue, key=product_revenue.get) if product_revenue else "N/A"
    top_qty_val = max(product_revenue.values()) if product_revenue else 0

    for el in _build_summary_block(
        f"<b>INCAMAKE Y'ICYUMWERU (WEEKLY SUMMARY)</b>",
        grand_total, grand_total * 0.20, top, top_qty_val,
    ):
        elements.append(el)
    for el in _footer_block("BIKOREWE MU Ruhango", employee_names=_collect_emp_names_from_txs(txs)):
        elements.append(el)

    doc.build(elements)
    print(f"✅ Weekly PDF saved: {output_pdf}")
    return output_pdf


# =========================================================
# MONTHLY REPORT (blocks of 5 days)
# =========================================================
def create_monthly_report(output_folder="reports", target_date=None):
    _ensure_folder(output_folder)
    if target_date is None:
        target = date.today().replace(day=1)
    else:
        target = datetime.fromisoformat(target_date).date().replace(day=1)
    # All days in the month
    next_month = (target.replace(day=28) + timedelta(days=4)).replace(day=1)
    days = []
    d = target
    while d < next_month:
        days.append(d)
        d += timedelta(days=1)
    days_iso = [d.isoformat() for d in days]
    day_labels = [d.strftime("%d") for d in days]

    products, txs, items = _load_product_data()
    sales_by_pid = _aggregate_sales_by_day(txs, items, days_iso)

    output_pdf = os.path.join(
        output_folder,
        f"Monthly_Report_{target.strftime('%Y-%m')}.pdf",
    )
    doc = SimpleDocTemplate(
        output_pdf, pagesize=landscape(A4),
        rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10,
    )
    elements = [get_company_header(),
                Paragraph("<hr/>", _styles["Normal"]),
                Spacer(1, 5)]
    elements.append(Paragraph(
        f"<b>MONTHLY REPORT - {target.strftime('%B %Y')}</b>",
        report_title_style,
    ))
    elements.append(Spacer(1, 5))

    block_size = 5
    grand_qty = 0
    grand_total = 0.0
    product_revenue = {}
    for bi in range(0, len(days), block_size):
        block_days = days_iso[bi:bi + block_size]
        block_labels = day_labels[bi:bi + block_size]
        if not block_days:
            break
        elements.append(Paragraph(
            f"<b>Block {bi // block_size + 1}: "
            f"{datetime.fromisoformat(block_days[0]).strftime('%d')} - "
            f"{datetime.fromisoformat(block_days[-1]).strftime('%d %b %Y')}</b>",
            summary_title_style,
        ))
        elements.append(Spacer(1, 3))
        tbl, q, tot, rev = _build_wide_table(
            block_days, products, sales_by_pid, block_labels, "MONTHLY"
        )
        elements.append(tbl)
        grand_qty += q
        grand_total += tot
        for k, v in rev.items():
            product_revenue[k] = product_revenue.get(k, 0) + v
        elements.append(Spacer(1, 10))

    top = max(product_revenue, key=product_revenue.get) if product_revenue else "N/A"
    top_val = max(product_revenue.values()) if product_revenue else 0

    for el in _build_summary_block(
        f"<b>INCAMAKE Y'UKWEZI (MONTHLY SUMMARY)</b>",
        grand_total, grand_total * 0.20, top, top_val,
    ):
        elements.append(el)
    for el in _footer_block("BIKOREWE MU Ruhango", employee_names=_collect_emp_names_from_txs(txs)):
        elements.append(el)

    doc.build(elements)
    print(f"✅ Monthly PDF saved: {output_pdf}")
    return output_pdf


# =========================================================
# YEARLY REPORT (blocks of 6 months)
# =========================================================
def create_yearly_report(output_folder="reports", target_date=None):
    _ensure_folder(output_folder)
    if target_date is None:
        year = date.today().year
    else:
        year = datetime.fromisoformat(target_date).date().year

    months = []
    for m in range(1, 13):
        first = date(year, m, 1)
        if m == 12:
            last = date(year, 12, 31)
        else:
            last = date(year, m + 1, 1) - timedelta(days=1)
        days = []
        d = first
        while d <= last:
            days.append(d.isoformat())
            d += timedelta(days=1)
        months.append({
            "label": first.strftime("%b"),
            "iso": first.isoformat(),
            "days": days,
        })
    all_days = []
    for m in months:
        all_days += m["days"]

    products, txs, items = _load_product_data()
    sales_by_pid = _aggregate_sales_by_day(txs, items, all_days)

    # Aggregate per-month per-product
    monthly_sales = {}  # pid -> {month_iso: {qty,total,cost}}
    for pid, day_map in sales_by_pid.items():
        monthly_sales[pid] = {}
        for m in months:
            tot_qty = 0
            tot_total = 0.0
            last_price = 0.0
            for d in m["days"]:
                rec = day_map.get(d, {"qty": 0, "unit_price": 0.0, "total": 0.0})
                tot_qty += rec["qty"]
                tot_total += rec["total"]
                if rec["unit_price"] > 0:
                    last_price = rec["unit_price"]
            monthly_sales[pid][m["iso"]] = {
                "qty": tot_qty, "unit_price": last_price, "total": tot_total
            }

    output_pdf = os.path.join(output_folder, f"Yearly_Report_{year}.pdf")
    doc = SimpleDocTemplate(
        output_pdf, pagesize=landscape(A4),
        rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10,
    )
    elements = [get_company_header(),
                Paragraph("<hr/>", _styles["Normal"]),
                Spacer(1, 5)]
    elements.append(Paragraph(
        f"<b>YEARLY REPORT - {year}</b>",
        report_title_style,
    ))
    elements.append(Spacer(1, 5))

    grand_qty = 0
    grand_total = 0.0
    product_revenue = {}

    block_size = 6
    for bi in range(0, len(months), block_size):
        block = months[bi:bi + block_size]
        if not block:
            break
        block_isos = [m["iso"] for m in block]
        block_labels = [m["label"] for m in block]

        # Build pseudo sales_by_pid for this block (month-level)
        block_sales = {}
        for pid, mmap in monthly_sales.items():
            block_sales[pid] = {m_iso: mmap.get(m_iso, {"qty": 0, "unit_price": 0.0, "total": 0.0}) for m_iso in block_isos}

        elements.append(Paragraph(
            f"<b>Block {bi // block_size + 1}: "
            f"{block[0]['label']} - {block[-1]['label']} {year}</b>",
            summary_title_style,
        ))
        elements.append(Spacer(1, 3))
        tbl, q, tot, rev = _build_wide_table(
            block_isos, products, block_sales, block_labels, "YEARLY"
        )
        elements.append(tbl)
        grand_qty += q
        grand_total += tot
        for k, v in rev.items():
            product_revenue[k] = product_revenue.get(k, 0) + v
        elements.append(Spacer(1, 10))

    top = max(product_revenue, key=product_revenue.get) if product_revenue else "N/A"
    top_val = max(product_revenue.values()) if product_revenue else 0

    for el in _build_summary_block(
        f"<b>INCAMAKE Y'UMWAKA (YEARLY SUMMARY)</b>",
        grand_total, grand_total * 0.20, top, top_val,
    ):
        elements.append(el)
    for el in _footer_block("BIKOREWE MU Ruhango", employee_names=_collect_emp_names_from_txs(txs)):
        elements.append(el)

    doc.build(elements)
    print(f"✅ Yearly PDF saved: {output_pdf}")
    return output_pdf


if __name__ == "__main__":
    create_daily_report()
    create_weekly_report()
    create_monthly_report()
    create_yearly_report()
