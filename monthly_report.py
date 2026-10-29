# monthly_report.py
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

def create_monthly_report(output_folder="reports"):
    print("🔄 STEP 5: Import daily data to monthly format...")
    
    list_of_files = glob.glob(f'{output_folder}/daily_*.csv')
    if not list_of_files:
        print("❌ Nta makuru ya Daily (.csv) abonetse muri 'reports'.")
        return

    df_list = []
    for file in list_of_files:
        try:
            df = pd.read_csv(file)
            df = df.apply(lambda x: x.astype(str).str.strip() if x.dtype == "object" else x)
            
            match = re.search(r'(\d{4}[-_]\d{2}[-_]\d{2})', os.path.basename(file))
            if match:
                raw_date = match.group(0).replace("_", "-")
                df['Date'] = raw_date
                df_list.append(df)
            else:
                print(f"⚠️ Nta itariki yabonetse muri: {file}")
        except Exception as e:
            print(f"⚠️ Error reading file {file}: {e}")

    if not df_list:
        print("❌ Nta makuru yasomwe neza muri daily files.")
        return

    df_all = pd.concat(df_list, ignore_index=True)
    
    # Gukura imirongo itari iy'ibicuruzwa
    df_all['DETAILS'] = df_all['DETAILS'].astype(str).str.strip()
    mask_valid = (
        df_all['DETAILS'].notna()
        & (df_all['DETAILS'] != "")
        & (df_all['DETAILS'].str.upper() != "NAN")
        & (~df_all['DETAILS'].str.upper().str.contains(
            'TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE|T&J|TIN|GENERAL|ITEM|SECTION',
            na=False))
    )
    df_all = df_all[mask_valid].copy()

    if df_all.empty:
        print("❌ Nta bicuruzwa byabonetse nyuma yo gushungura.")
        return

    # Guhindura imibare
    df_all['Qty'] = pd.to_numeric(
        df_all['TODAY QUANTITY'].astype(str).str.replace(r'[^\d.\-]', '', regex=True),
        errors='coerce'
    ).fillna(0)

    df_all['Unit_Price'] = pd.to_numeric(
        df_all['AVG UNIT PRICE'].astype(str).str.replace(r'[^\d.\-]', '', regex=True),
        errors='coerce'
    ).fillna(0)

    # INYUNGU (PROFIT/LOSS)
    if 'PROFIT/LOSS' in df_all.columns:
        df_all['Profit'] = pd.to_numeric(
            df_all['PROFIT/LOSS'].astype(str).str.replace(r'[^\d.\-]', '', regex=True),
            errors='coerce'
        ).fillna(0)
    else:
        df_all['Profit'] = 0.0

    df_all['Total'] = df_all['Qty'] * df_all['Unit_Price']

    # Shaka ukwezi
    today = datetime.now()
    start_of_month = today.replace(day=1)
    days_in_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    days_of_month = [(start_of_month + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((days_in_month - start_of_month).days + 1)]
    
    df_month = df_all[df_all['Date'].isin(days_of_month)].copy()

    if df_month.empty:
        print("⚠️ Nta makuru y'uku kwezi abonetse.")
        return

    unique_products = sorted(df_month['DETAILS'].unique())

    itariki_intangiriro = start_of_month.strftime('%d/%m/%Y')
    itariki_impera = days_in_month.strftime('%d/%m/%Y')
    itariki_yakorewe = datetime.now().strftime('%d/%m/%Y saa %H:%M')

    output_pdf = f"{output_folder}/Monthly_Report_{start_of_month.strftime('%Y-%m')}.pdf"
    os.makedirs(output_folder, exist_ok=True)

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
    
    elements.append(Paragraph(f"MONTHLY REPORT - RAPPORT Y'UKWEZI ({itariki_intangiriro} - {itariki_impera})", report_title_style))
    elements.append(Spacer(1, 10))

    total_income_global = 0
    total_profit_global = 0  # ✅ INYUNGU YOSE
    grand_total_qty_global = 0
    product_revenue_dict = {}

    # Gabanya iminsi 5 kuri buri table
    for group_idx in range(0, len(days_of_month), 5):
        days_group = days_of_month[group_idx:group_idx+5]
        
        header_row1 = ["PRODUCTS"]
        header_row2 = [""]
        
        for i, day in enumerate(days_group):
            day_number = datetime.strptime(day, '%Y-%m-%d').strftime('%d')
            header_row1.extend([f"Kuwa {day_number}", "", "", ""]) # ✅ 4 columns kuri buri munsi
            header_row2.extend(["Qty", "Unit", "Total", "Profit"]) # ✅ 4 columns kuri buri munsi
                
        header_row1.extend(["TOTAL", "", "", ""])
        header_row2.extend(["Qty", "Unit Price", "Total", "Profit"]) # ✅
        
        table_data = [header_row1, header_row2]
        
        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor("#FFC000")),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7), # ✅ Yagabanyijwe kugira ngo 4 cols zinjire
            ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]

        table_styles.append(('SPAN', (0, 0), (0, 1)))
        for i in range(len(days_group)):
            start_col = 1 + (i * 4) # ✅ 4 columns kuri buri munsi
            end_col = start_col + 3
            table_styles.append(('SPAN', (start_col, 0), (end_col, 0)))
        table_styles.append(('SPAN', (len(days_group)*4 + 1, 0), (len(days_group)*4 + 4, 0)))

        row_num = 2 
        group_total_income = 0
        group_total_qty = 0
        group_total_profit = 0 # ✅

        for product in unique_products:
            if pd.isna(product) or str(product).strip() == "":
                continue
                
            row = [str(product)]
            product_total_qty = 0
            product_amount = 0
            product_profit = 0 # ✅
            last_valid_price = 0
            
            for i, day in enumerate(days_group):
                day_data = df_month[(df_month['DETAILS'] == product) & (df_month['Date'] == day)]
                
                if not day_data.empty:
                    qty = pd.to_numeric(day_data['Qty'], errors='coerce').sum()
                    price = pd.to_numeric(day_data['Unit_Price'], errors='coerce').mean()
                    total = pd.to_numeric(day_data['Total'], errors='coerce').sum()
                    profit = pd.to_numeric(day_data['Profit'], errors='coerce').sum() # ✅
                    
                    row.extend([
                        int(qty) if qty > 0 else "", 
                        int(price) if price > 0 else "", 
                        int(total) if total > 0 else "",
                        int(profit) if profit != 0 else "" # ✅
                    ])
                    product_total_qty += qty
                    product_amount += total
                    product_profit += profit # ✅
                    if price > 0:
                        last_valid_price = price
                else:
                    row.extend(["", "", "", ""])
                    
            row.extend([
                int(product_total_qty) if product_total_qty > 0 else "", 
                int(last_valid_price) if last_valid_price > 0 else "", 
                int(product_amount) if product_amount > 0 else "",
                int(product_profit) if product_profit != 0 else "" # ✅
            ])
            table_data.append(row)
            
            group_total_qty += product_total_qty
            group_total_income += product_amount
            group_total_profit += product_profit # ✅
            row_num += 1

        # ✅ UMURONGO WA TOTAL
        total_row = ["GENERAL TOTAL"] + [""] * (len(days_group) * 4) + [f"{int(group_total_qty):,}", "", f"{int(group_total_income):,}", f"{int(group_total_profit):,}"] 
        table_data.append(total_row)

        table_styles.append(('SPAN', (0, row_num), (len(days_group)*4, row_num)))
        table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
        table_styles.append(('BACKGROUND', (len(days_group)*4 + 1, row_num), (len(days_group)*4 + 4, row_num), colors.HexColor("#4472C4"))) 
        table_styles.append(('TEXTCOLOR', (len(days_group)*4 + 1, row_num), (len(days_group)*4 + 4, row_num), colors.white))
        table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))

        grand_total_qty_global += group_total_qty
        total_income_global += group_total_income
        total_profit_global += group_total_profit # ✅

        for product in unique_products:
             if pd.isna(product) or str(product).strip() == "": continue
             prod_amount = df_month[df_month['DETAILS'] == product]['Total'].sum()
             if str(product) in product_revenue_dict:
                 product_revenue_dict[str(product)] += prod_amount
             else:
                 product_revenue_dict[str(product)] = prod_amount

        # ✅ Guhindura ubugari bw'inkingi kugira ngo 4 cols zinjire (Col Widths)
        col_widths = [1.3*inch] + [0.35*inch, 0.4*inch, 0.45*inch, 0.45*inch] * len(days_group) + [0.45*inch, 0.5*inch, 0.55*inch, 0.55*inch]
        table = Table(table_data, colWidths=col_widths, repeatRows=2)
        table.setStyle(TableStyle(table_styles))
        elements.append(table)
        
        if group_idx + 5 < len(days_of_month):
            elements.append(Spacer(1, 20)) 

    # =========================================================
    # SUMMARY YA NYUMA (INCAMAKE Y'UKWEZI)
    # =========================================================
    elements.append(Spacer(1, 15))
    summary_title_style = ParagraphStyle(
        'SummaryTitle', 
        parent=styles['Normal'], 
        fontSize=10, 
        fontName='Helvetica-Bold',
        alignment=TA_CENTER 
    )
    elements.append(Paragraph("<b>MONTHLY PERFORMANCE SUMMARY / INCAMAKE Y'UKWEZI</b>", summary_title_style))
    elements.append(Spacer(1, 5))

    top_product = max(product_revenue_dict, key=product_revenue_dict.get) if product_revenue_dict else "N/A"
    least_product = min(product_revenue_dict, key=product_revenue_dict.get) if product_revenue_dict else "N/A"
    top_value = product_revenue_dict.get(top_product, 0)
    least_value = product_revenue_dict.get(least_product, 0)

    summary_data = [
        [Paragraph("<b>Metric / Ikigereranyo</b>", subtitle_style), Paragraph("<b>Product Name / Izina</b>", subtitle_style), Paragraph("<b>Value / Amafaranga (RWF)</b>", subtitle_style)],
        ["Total Monthly Income (Ayo Ukwezi Kose Cyinjije)", "All Products", f"{int(total_income_global):,}"],
        ["Total Monthly Profit (Inyungu Yose Hamwe)", "All Products", f"{int(total_profit_global):,}"], # ✅ INYUNGU
        ["Top Performing Product (Icyinjije Menshi)", top_product, f"{int(top_value):,}"],
        ["Least Performing Product (Icyinjije Make)", least_product, f"{int(least_value):,}"]
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

    elements.append(Spacer(1, 30)) 
    elements.append(Paragraph("<hr/>", styles['Normal'])) 
    elements.append(Spacer(1, 40)) 

    try:
        from helpers import get_signatures
        elements.append(get_signatures())
    except:
        pass
    
    doc.build(elements)
    print(f"✅ STEP 6: Monthly PDF saved at {output_pdf}")

if __name__ == "__main__":
    create_monthly_report()
