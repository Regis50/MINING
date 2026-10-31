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
    
    list_of_files = glob.glob(f'{output_folder}/Daily_Report_*.csv')
    if not list_of_files:
        print("❌ Nta makuru ya Daily (.csv) abonetse muri 'reports'.")
        return

    df_list = []
    for file in list_of_files:
        try:
            # Gusoma dosiye ya CSV y'umunsi
            df = pd.read_csv(file)
            
            df = df.apply(lambda x: x.astype(str).str.strip() if x.dtype == "object" else x)
            
            # Gushaka itariki mu rukurikirane rw'izina rya file
            match = re.search(r'(\d{4}-\d{2}-\d{2})', file)
            if match:
                raw_date = match.group(0)
                df['Date'] = raw_date
                df_list.append(df)
        except Exception as e:
            print(f"⚠️ Error reading file {file}: {e}")

    if not df_list:
        print("❌ Nta makuru yasomwe neza muri daily files.")
        return

    df_all = pd.concat(df_list, ignore_index=True)
    
    # Gukura amakuru adakenewe mu gushungura imirongo
    df_all = df_all[df_all['DETAILS'].astype(str).str.upper().notna()]
    df_all = df_all[~df_all['DETAILS'].astype(str).str.upper().str.contains('TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE|T&J|TIN|GENERAL|ITEM', na=False)]

    # Guhindura amadata mu buryo bw'imibare (TODAY QUANTITY n'igiciro)
    df_all['Qty'] = df_all['TODAY QUANTITY'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df_all['Qty'] = pd.to_numeric(df_all['Qty'], errors='coerce').fillna(0)

    df_all['Unit_Price'] = df_all['AVG UNIT PRICE'].astype(str).str.replace(r'[^\d.]', '', regex=True)
    df_all['Unit_Price'] = pd.to_numeric(df_all['Unit_Price'], errors='coerce').fillna(0)

    df_all['Total'] = df_all['Qty'] * df_all['Unit_Price']
    
    today = datetime.now()
    start_of_week = today - timedelta(days=today.weekday())
    days_of_week = [(start_of_week + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
    
    # Shungura amakuru y'iki cyumweru gusa
    df_week = df_all[df_all['Date'].isin(days_of_week)]

    if df_week.empty:
        print("⚠️ Nta makuru y'iki cyumweru ahari, turakoresha amakuru yose ahari.")
        df_week = df_all

    unique_products = df_week['DETAILS'].unique()
    
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

    for product in unique_products:
        if pd.isna(product) or str(product).strip() == "": continue
            
        row = [str(product)]
        product_total_qty = 0
        product_amount = 0
        last_valid_price = 0
        
        for day in days_of_week:
            day_data = df_week[(df_week['DETAILS'] == product) & (df_week['Date'] == day)]
            
            if not day_data.empty:
                qty = day_data['Qty'].sum()
                price = day_data['Unit_Price'].mean()
                total = day_data['Total'].sum()
                
                row.extend([f"{qty:,.0f}" if qty > 0 else "", f"{price:,.0f}" if qty > 0 else "", f"{total:,.0f}" if total > 0 else ""])
                product_total_qty += qty
                product_amount += total
                if price > 0: last_valid_price = price
            else:
                row.extend(["", "", ""])
                
        row.extend([
            f"{product_total_qty:,.0f}" if product_total_qty > 0 else "", 
            f"{last_valid_price:,.0f}" if last_valid_price > 0 else "", 
            f"{product_amount:,.0f}" if product_amount > 0 else ""
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

    start_date_str = start_of_week.strftime('%d/%m/%Y')
    end_date_str = (start_of_week + timedelta(days=6)).strftime('%d/%m/%Y')
    output_pdf = f"{output_folder}/Weekly_Report_{start_of_week.strftime('%Y-%m-%d')}.pdf"
    
    doc = SimpleDocTemplate(output_pdf, pagesize=landscape(A4), rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10)
    elements = []
    
    # Header logic...
    styles = getSampleStyleSheet()
    report_title_style = ParagraphStyle('ReportTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=11, fontName='Helvetica-Bold')
    elements.append(Paragraph(f"WEEKLY REPORT - ({start_date_str} - {end_date_str})", report_title_style))
    elements.append(Spacer(1, 10))

    col_widths = [1.25*inch] + [0.35*inch, 0.40*inch, 0.41*inch] * 7 + [0.42*inch, 0.45*inch, 0.55*inch]
    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle(table_styles))
    elements.append(table)
    
    # Summary & Signatures...
    doc.build(elements)
    print(f"✅ STEP 4: Weekly PDF saved at {output_pdf}")

if __name__ == "__main__":
    create_weekly_report()
