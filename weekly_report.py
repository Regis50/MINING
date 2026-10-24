# weekly_report.py
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

def create_weekly_report(output_folder="reports"):
    print("🔄 STEP 3: Import daily data to weekly format...")
    
    list_of_files = glob.glob(f'{output_folder}/daily_*.csv')
    if not list_of_files:
        print("❌ Nta makuru ya Daily abonetse muri 'reports'.")
        return

    df_list = []
    for file in list_of_files:
        try:
            # ✅ 1. KURAHO skiprows=1 (Kuko umurongo wa 1 ari "T&J THINK BIG...")
            # ✅ 2. KURAHO UMURONGO WA MBERE WOSE (header=none) KUGIRA NGO TUBONE IMBARE
            df = pd.read_csv(file, header=None)
            
            # GUKURAHO UTWANYA (SPACES)
            df = df.apply(lambda x: x.astype(str).str.strip() if x.dtype == "object" else x)
            
            # GUSHAKA ITARIKI MU IZINA RYA FILE
            match = re.search(r'(\d{4}-\d{2}-\d{2})', file)
            if match:
                raw_date = match.group(0)
                try:
                    dt = pd.to_datetime(raw_date)
                    df['Date'] = dt.strftime('%Y-%m-%d')
                    df_list.append(df)
                except:
                    pass
        except Exception as e:
            print(f"⚠️ Error reading file {file}: {e}")

    if not df_list:
        print("❌ Nta makuru yasomwe neza muri daily files.")
        return

    df_all = pd.concat(df_list, ignore_index=True)
    
    # ✅ 3. GUKURAHO UMURONGO WA MBERE (Ufite "T&J THINK BIG..." cyangwa "Ibishyimbo 0 Kg")
    df_all = df_all[pd.to_numeric(df_all[1], errors='coerce').notna()]
    
    # ✅ 4. GUKURAHO IMIRONGO ITARI IY'IBICURUZWA (TOTAL, IMBOGA, etc.)
    df_all = df_all[~df_all[0].astype(str).str.upper().str.contains('TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE|T&J|TIN|GENERAL', na=False)]

    # ✅ 5. GUHINDURA IMBARE (Gukuraho "Kg", "ltrs", etc.)
    df_all['Qty'] = df_all[1].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df_all['Qty'] = pd.to_numeric(df_all['Qty'], errors='coerce').fillna(0)

    df_all['Unit_Price'] = df_all[2].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df_all['Unit_Price'] = pd.to_numeric(df_all['Unit_Price'], errors='coerce').fillna(0)

    # ✅ DORE URUHINDUTSO: Buri gihe ibara Total ukoresheje Qty * Unit_Price
    df_all['Total'] = df_all['Qty'] * df_all['Unit_Price']
    
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    days_of_week = [(start_of_week + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    # 6. GUSHUNGA AMAKURU Y'IKI CYUMWERU GUSA
    df_all = df_all[df_all['Date'].isin(days_of_week)]

    if df_all.empty:
        print("⚠️ Nta makuru y'icyumweru abonetse. Turakoresha amakuru yose ari muri files.")
        df_list_fallback = []
        for file in list_of_files:
            df = pd.read_csv(file, header=None) 
            df = df.apply(lambda x: x.astype(str).str.strip() if x.dtype == "object" else x)
            df_list_fallback.append(df)
        df_all = pd.concat(df_list_fallback, ignore_index=True)
        df_all = df_all[pd.to_numeric(df_all[1], errors='coerce').notna()]
        df_all = df_all[~df_all[0].astype(str).str.upper().str.contains('TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE|T&J|TIN|GENERAL', na=False)]
        df_all['Qty'] = df_all[1].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df_all['Qty'] = pd.to_numeric(df_all['Qty'], errors='coerce').fillna(0)
        df_all['Unit_Price'] = df_all[2].astype(str).str.replace(r'[^\d.]', '', regex=True)
        df_all['Unit_Price'] = pd.to_numeric(df_all['Unit_Price'], errors='coerce').fillna(0)
        # ✅ HANO NABYO: Ibara Total
        df_all['Total'] = df_all['Qty'] * df_all['Unit_Price']
        df_all['Date'] = days_of_week[0] 

    # 7. GUFATA IZINA RY'IBICURUZWA (Column A - index 0)
    unique_products = df_all[0].unique()
    
    header_row1 = ["PRODUCTS"] + ["Kuwa 1", "", "", "Kuwa 2", "", "", "Kuwa 3", "", "", "Kuwa 4", "", "", "Kuwa 5", "", "", "Kuwa 6", "", "", "Kuwa 7", "", "", "TOTAL", "", ""]
    header_row2 = [""] + ["Qty", "Unit Price", "Total"] * 8
    
    table_data = [header_row1, header_row2]
    
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor("#FFC000")),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 6.5),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 0.5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0.5),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]

    table_styles.append(('SPAN', (0, 0), (0, 1)))
    for i in range(7):
        start_col = 1 + (i * 3)
        end_col = start_col + 2
        table_styles.append(('SPAN', (start_col, 0), (end_col, 0)))
    table_styles.append(('SPAN', (22, 0), (24, 0)))

    total_income = 0
    grand_total_qty = 0 
    row_num = 2 
    product_revenue_dict = {}

    # 8. GUHINDURA AMAKURU MU MBONERAHAMWE
    for product in unique_products:
        if pd.isna(product) or str(product).strip() == "":
            continue
            
        row = [str(product)]
        product_total_qty = 0
        product_amount = 0
        last_valid_price = 0
        
        for i, day in enumerate(days_of_week):
            day_data = df_all[(df_all[0] == product) & (df_all['Date'] == day)]
            
            if not day_data.empty:
                qty = pd.to_numeric(day_data['Qty'], errors='coerce').sum()
                price = pd.to_numeric(day_data['Unit_Price'], errors='coerce').mean()
                total = pd.to_numeric(day_data['Total'], errors='coerce').sum()
                
                row.extend([int(qty) if qty > 0 else "", int(price) if qty > 0 else "", int(total) if total > 0 else ""])
                product_total_qty += qty
                product_amount += total
                if price > 0:
                    last_valid_price = price
            else:
                row.extend(["", "", ""])
                
        row.extend([
            int(product_total_qty) if product_total_qty > 0 else "", 
            int(last_valid_price) if last_valid_price > 0 else "", 
            int(product_amount) if product_amount > 0 else ""
        ])
        table_data.append(row)
        
        product_revenue_dict[str(product)] = product_amount
        grand_total_qty += product_total_qty
        total_income += product_amount
        row_num += 1

    total_row = ["GENERAL TOTAL"] + [""] * 21 + [f"{int(grand_total_qty):,}", "", f"{int(total_income):,}"] 
    table_data.append(total_row)

    table_styles.append(('SPAN', (0, row_num), (21, row_num)))
    table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
    table_styles.append(('BACKGROUND', (22, row_num), (24, row_num), colors.HexColor("#4472C4"))) 
    table_styles.append(('TEXTCOLOR', (22, row_num), (24, row_num), colors.white))
    table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))

    top_product = max(product_revenue_dict, key=product_revenue_dict.get) if product_revenue_dict else "N/A"
    least_product = min(product_revenue_dict, key=product_revenue_dict.get) if product_revenue_dict else "N/A"
    top_value = product_revenue_dict.get(top_product, 0)
    least_value = product_revenue_dict.get(least_product, 0)

    itariki_intangiriro = start_of_week.strftime('%d/%m/%Y')
    itariki_impera = (start_of_week + timedelta(days=6)).strftime('%d/%m/%Y')
    itariki_yakorewe = datetime.now().strftime('%d/%m/%Y saa %H:%M')

    output_pdf = f"{output_folder}/Weekly_Report_{start_of_week.strftime('%Y-%m-%d')}.pdf"
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    doc = SimpleDocTemplate(
        output_pdf, 
        pagesize=landscape(A4), 
        rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Normal'], alignment=TA_CENTER, fontSize=13, fontName='Helvetica-Bold', spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, spaceAfter=1)
    report_title_style = ParagraphStyle('ReportTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11, fontName='Helvetica-Bold')
    date_style = ParagraphStyle('DateRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=8, fontName='Helvetica')

    try:
        logo = Image("logo.png", width=0.8*inch, height=0.8*inch)
    except:
        logo = Paragraph("<b>T&J</b>", title_style) 

    company_details = [
        Paragraph("<b>T&J; THINK BIG MINING COMPANY LTD</b>", title_style),
        Paragraph("TIN: 121715003", subtitle_style),
        Paragraph("TEL: 0782992433 / 0788977442", subtitle_style),
        Paragraph("Email: uwijacky15@gmail.com", subtitle_style),
    ]
    
    date_paragraph = Paragraph(f"<b>Date:</b> {itariki_yakorewe}", date_style)
    
    header_table = Table([[logo, company_details, date_paragraph]], colWidths=[1*inch, 7*inch, 2*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),   
        ('ALIGN', (1, 0), (1, 0), 'CENTER'), 
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),  
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    
    elements.append(Paragraph("<hr/>", styles['Normal']))
    elements.append(Spacer(1, 5))
    
    elements.append(Paragraph(f"WEEKLY REPORT - RAPPORT Y'ICYUMWERU ({itariki_intangiriro} - {itariki_impera})", report_title_style))
    elements.append(Spacer(1, 5))

    col_widths = [1.25*inch] + [0.35*inch, 0.40*inch, 0.41*inch] * 7 + [0.42*inch, 0.45*inch, 0.55*inch]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle(table_styles))
    elements.append(table)
    
    elements.append(Spacer(1, 15))
    summary_title_style = ParagraphStyle('SummaryTitle', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    elements.append(Paragraph("<b>WEEKLY PERFORMANCE SUMMARY / INCAMAKE Y'ICYUMWERU</b>", summary_title_style))
    elements.append(Spacer(1, 5))
    
    summary_data = [
        [Paragraph("<b>Metric / Ikigereranyo</b>", subtitle_style), Paragraph("<b>Product Name / Izina</b>", subtitle_style), Paragraph("<b>Value / Amafaranga (RWF)</b>", subtitle_style)],
        ["Total Weekly Income (Ayo Icyumweru Cyose Cyinjije)", "All Products", f"{int(total_income):,}"],
        ["Top Performing Product (Icyayinjuje Menshi)", top_product, f"{int(top_value):,}"],
        ["Least Performing Product (Icyayinjuje Make)", least_product, f"{int(least_value):,}"]
    ]
    
    summary_table = Table(summary_data, colWidths=[3.5*inch, 3.5*inch, 3.0*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
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
    except:
        pass
    
    doc.build(elements)
    print(f"✅ STEP 4: Weekly PDF saved at {output_pdf}")

if __name__ == "__main__":
    create_weekly_report()