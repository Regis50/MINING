import pandas as pd
import glob
import os
import re
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def _to_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(r'[^\d.\-]', '', regex=True),
        errors='coerce'
    ).fillna(0)

def create_weekly_report(output_folder="reports"):
    print("🔄 Turafata amakuru ya daily muri weekly format...")

    list_of_files = glob.glob(f'{output_folder}/daily_*.csv')
    if not list_of_files:
        print("❌ Nta makuru ya Daily (.csv) abonetse muri 'reports'.")
        return

    df_list = []
    file_dates = []
    for file in list_of_files:
        try:
            df = pd.read_csv(file)
            df = df.apply(lambda x: x.astype(str).str.strip() if x.dtype == "object" else x)
            match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', os.path.basename(file))
            if match:
                raw_date = match.group(0).replace("_", "-")
                df['Date'] = raw_date
                df_list.append(df)
                file_dates.append(raw_date)
        except Exception as e:
            print(f"⚠️ Error reading file {file}: {e}")

    if not df_list:
        print("❌ Nta makuru yasomwe neza muri daily files.")
        return

    df_all = pd.concat(df_list, ignore_index=True)
    unique_dates = sorted(set(file_dates))
    selected_dates = unique_dates[-7:]
    
    if 'DETAILS' not in df_all.columns:
        print("❌ Col 'DETAILS' ntabwo iri muri CSV.")
        return

    df_all = df_all[~df_all['DETAILS'].astype(str).str.upper().str.contains(
        'TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE|T&J|TIN|GENERAL|ITEM', na=False
    )]

    df_all['Qty'] = _to_num(df_all['TODAY QUANTITY']) if 'TODAY QUANTITY' in df_all.columns else 0
    df_all['Unit_Price'] = _to_num(df_all['AVG UNIT PRICE']) if 'AVG UNIT PRICE' in df_all.columns else 0
    df_all['Total'] = _to_num(df_all['SOLD AMOUNT']) if 'SOLD AMOUNT' in df_all.columns else df_all['Qty'] * df_all['Unit_Price']
    df_all['Profit'] = _to_num(df_all['PROFIT/LOSS']) if 'PROFIT/LOSS' in df_all.columns else 0

    df_week = df_all[df_all['Date'].isin(selected_dates)]
    if df_week.empty:
        df_week = df_all

    unique_products = df_week['DETAILS'].unique()

    def fmt_date(d):
        try:
            return datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m')
        except Exception:
            return d

    day_labels = [fmt_date(d) for d in selected_dates]
    while len(day_labels) < 7:
        day_labels.append("")

    header_row1 = ["PRODUCTS"]
    for label in day_labels:
        header_row1.extend([label, "", "", ""]) 
    header_row1.extend(["TOTAL", "", "", ""])

    header_row2 = [""] + ["Qty", "Unit", "Total", "Profit"] * 8 

    table_data = [header_row1, header_row2]

    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor("#FFC000")),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 5.5), # ✅ Font yagabanyijwe kugira ngo 33 cols zinjire
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 1),  # ✅ Padding yagabanyijwe
        ('RIGHTPADDING', (0, 0), (-1, -1), 1),
        ('SPAN', (0, 0), (0, 1)),
    ]

    for i in range(7):
        start_col = 1 + (i * 4)
        end_col = start_col + 3
        if i < len(day_labels) and day_labels[i]:
            table_styles.append(('SPAN', (start_col, 0), (end_col, 0)))
    
    table_styles.append(('SPAN', (29, 0), (32, 0)))

    total_income = 0
    grand_total_qty = 0
    row_num = 2
    product_revenue_dict = {}
    daily_totals = [0.0] * 7
    daily_profits = [0.0] * 7

    for product in unique_products:
        if pd.isna(product) or str(product).strip() == "":
            continue

        row = [str(product)]
        product_total_qty = 0
        product_amount = 0
        product_profit = 0 
        last_valid_price = 0

        for i, day in enumerate(selected_dates):
            day_data = df_week[(df_week['DETAILS'] == product) & (df_week['Date'] == day)]

            if not day_data.empty:
                qty = day_data['Qty'].sum()
                price = day_data['Unit_Price'].mean() if not day_data['Unit_Price'].empty else 0
                total = day_data['Total'].sum()
                profit = day_data['Profit'].sum()

                row.extend([
                    f"{qty:,.0f}" if qty > 0 else "",
                    f"{price:,.0f}" if qty > 0 else "",
                    f"{total:,.0f}" if total > 0 else "",
                    f"{profit:,.0f}" if profit != 0 else "" 
                ])
                product_total_qty += qty
                product_amount += total
                product_profit += profit
                if price > 0:
                    last_valid_price = price
                daily_totals[i] += total
                daily_profits[i] += profit
            else:
                row.extend(["", "", "", ""])

        row.extend([
            f"{product_total_qty:,.0f}" if product_total_qty > 0 else "",
            f"{last_valid_price:,.0f}" if last_valid_price > 0 else "",
            f"{product_amount:,.0f}" if product_amount > 0 else "",
            f"{product_profit:,.0f}" if product_profit != 0 else "" 
        ])
        table_data.append(row)

        product_revenue_dict[str(product)] = product_amount
        grand_total_qty += product_total_qty
        total_income += product_amount
        row_num += 1

    # DAILY TOTAL
    daily_total_row = ["DAILY TOTAL"]
    for i in range(7):
        if i < len(selected_dates) and selected_dates[i]:
            daily_total_row.extend(["", "", f"{int(daily_totals[i]):,}", ""])
        else:
            daily_total_row.extend(["", "", "", ""])
    daily_total_row.extend([f"{int(grand_total_qty):,}", "", f"{int(total_income):,}", f"{int(sum(daily_profits)):,}"])
    table_data.append(daily_total_row)
    table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#9DC3E6")))
    table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
    row_num += 1

    # DAILY PROFIT
    total_profit = sum(daily_profits)
    daily_profit_row = ["DAILY PROFIT"]
    for i in range(7):
        if i < len(selected_dates) and selected_dates[i]:
            daily_profit_row.extend(["", "", "", f"{int(daily_profits[i]):,}"])
        else:
            daily_profit_row.extend(["", "", "", ""])
    daily_profit_row.extend(["", "", "", f"{int(total_profit):,}"])
    table_data.append(daily_profit_row)
    table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#A9D08E")))
    table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
    row_num += 1

    # GENERAL TOTAL
    total_row = ["GENERAL TOTAL"] + [""] * 28 + [f"{int(grand_total_qty):,}", "", f"{int(total_income):,}", f"{int(total_profit):,}"]
    table_data.append(total_row)
    table_styles.append(('SPAN', (0, row_num), (28, row_num)))
    table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
    table_styles.append(('BACKGROUND', (29, row_num), (32, row_num), colors.HexColor("#4472C4")))
    table_styles.append(('TEXTCOLOR', (29, row_num), (32, row_num), colors.white))
    table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))

    # PDF layout
    top_product = max(product_revenue_dict, key=product_revenue_dict.get) if product_revenue_dict else "N/A"
    least_product = min(product_revenue_dict, key=product_revenue_dict.get) if product_revenue_dict else "N/A"
    top_value = product_revenue_dict.get(top_product, 0)
    least_value = product_revenue_dict.get(least_product, 0)

    real_dates = [d for d in selected_dates if d]
    if real_dates:
        try:
            start_date_obj = datetime.strptime(real_dates[0], '%Y-%m-%d')
            end_date_obj = datetime.strptime(real_dates[-1], '%Y-%m-%d')
            start_date_str = start_date_obj.strftime('%d/%m/%Y')
            end_date_str = end_date_obj.strftime('%d/%m/%Y')
        except Exception:
            start_date_str = real_dates[0]
            end_date_str = real_dates[-1]
    else:
        start_date_str = ""
        end_date_str = ""

    itariki_yakorewe = datetime.now().strftime('%d/%m/%Y saa %H:%M')
    last_date_str = real_dates[-1] if real_dates else datetime.now().strftime('%Y-%m-%d')
    output_pdf = f"{output_folder}/Weekly_Report_{last_date_str}.pdf"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=landscape(A4),
        rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15
    )
    elements = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Normal'], alignment=TA_CENTER, fontSize=13, fontName='Helvetica-Bold', spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, spaceAfter=1)
    report_title_style = ParagraphStyle('ReportTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11, fontName='Helvetica-Bold')
    date_style = ParagraphStyle('DateRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8, fontName='Helvetica')

    if os.path.exists("logo.png"):
        logo = Image("logo.png", width=0.8 * inch, height=0.8 * inch)
    elif os.path.exists(os.path.join("static", "logo.png")):
        logo = Image(os.path.join("static", "logo.png"), width=0.8 * inch, height=0.8 * inch)
    else:
        logo = Paragraph("<b>T&amp;J</b>", title_style)

    company_details = [
        Paragraph("<b>T&amp;J; THINK BIG MINING COMPANY LTD</b>", title_style),
        Paragraph("TIN: 121715003", subtitle_style),
        Paragraph("TEL: 0782992433 / 0788977442", subtitle_style),
        Paragraph("Email: uwijacky15@gmail.com", subtitle_style),
    ]

    date_paragraph = Paragraph(f"<b>Date:</b> {itariki_yakorewe}", date_style)
    header_table = Table([[logo, company_details, date_paragraph]], colWidths=[1 * inch, 7 * inch, 2 * inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    elements.append(Paragraph("<hr/>", styles['Normal']))
    elements.append(Spacer(1, 5))

    elements.append(Paragraph(
        f"WEEKLY REPORT - RAPPORT Y'ICYUMWERU ({start_date_str} - {end_date_str})",
        report_title_style
    ))
    elements.append(Spacer(1, 10))

    # =========================================================
    # ✅ GUTUNGANYA LAYOUT (COL WIDTHS) 
    # A4 Landscape ifite ubugari bwa 11.69 inches. 
    # Dukuraho margins 2 (15+15) = 11.39 inches zisigaye.
    # =========================================================
    available_width = 11.39 * inch
    product_col_width = 1.0 * inch
    total_col_width = 1.2 * inch  # 4 cols za TOTAL zihuye
    
    # Iminsi 7 isigaye: (Available - Product - Total) / 7
    # Buri munsi ufite cols 4 (Qty, Unit, Total, Profit)
    day_col_width = (available_width - product_col_width - total_col_width) / 7
    sub_col_width = day_col_width / 4  # Ubugari bwa buri nkingi imwe muri 4

    # ✅ Dosiye y'ubugari bw'inkingi (Col Widths Array)
    col_widths = [product_col_width] + [sub_col_width] * 28 + [sub_col_width] * 4
    
    table = Table(table_data, colWidths=col_widths, repeatRows=2)
    table.setStyle(TableStyle(table_styles))
    elements.append(table)

    # Summary section...
    elements.append(Spacer(1, 15))
    summary_title_style = ParagraphStyle('SummaryTitle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    elements.append(Paragraph("<b>WEEKLY PERFORMANCE SUMMARY / INCAMAKE Y'ICYUMWERU</b>", summary_title_style))
    elements.append(Spacer(1, 5))

    summary_data = [
        [Paragraph("<b>Metric / Ikigereranyo</b>", subtitle_style), Paragraph("<b>Value / Agaciro</b>", subtitle_style)],
        ["Total Weekly Income (Amafaranga Yinjiye)", f"{int(total_income):,} RWF"],
        ["Total Weekly Profit (Inyungu z'Icyumweru)", f"{int(total_profit):,} RWF"],
        ["Top Performing Product (Icyinjije Menshi)", f"{top_product} ({int(top_value):,} RWF)"],
        ["Least Performing Product (Icyinjije Make)", f"{least_product} ({int(least_value):,} RWF)"],
    ]

    summary_table = Table(summary_data, colWidths=[5 * inch, 3 * inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f9f9f9")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(summary_table)

    elements.append(Spacer(1, 20))
    try:
        from helpers import get_signatures
        elements.append(get_signatures())
    except Exception:
        pass

    doc.build(elements)
    print(f"✅ Weekly PDF yakozwe: {output_pdf}")

if __name__ == "__main__":
    create_weekly_report()
