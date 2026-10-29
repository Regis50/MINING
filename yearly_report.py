# yearly_report.py
import pandas as pd
import glob
import os
import re
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import A3, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def _to_num(series):
    """Convert a pandas series to numeric, stripping non-numeric chars first."""
    return pd.to_numeric(
        series.astype(str).str.replace(r'[^\d.\-]', '', regex=True),
        errors='coerce'
    ).fillna(0)

def create_yearly_report(output_folder="reports"):
    print("🔄 STEP 7: Import daily data to yearly format...")
    
    list_of_files = glob.glob(f'{output_folder}/daily_*.csv')
    if not list_of_files:
        print("❌ Nta makuru ya Daily abonetse muri 'reports'.")
        return

    df_list = []
    for file in list_of_files:
        try:
            # ✅ 1. SOMA NK'UKO BIRI (nka weekly na monthly)
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
    
    # ✅ 2. GUKURA IMIRONGO ITARI IY'IBICURUZWA
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

    # ✅ 3. GUHINDURA IMBARE (Qty, Unit Price, Profit)
    df_all['Qty'] = _to_num(df_all['TODAY QUANTITY']) if 'TODAY QUANTITY' in df_all.columns else 0
    df_all['Unit_Price'] = _to_num(df_all['AVG UNIT PRICE']) if 'AVG UNIT PRICE' in df_all.columns else 0
    
    if 'SOLD AMOUNT' in df_all.columns:
        df_all['Total'] = _to_num(df_all['SOLD AMOUNT'])
    else:
        df_all['Total'] = df_all['Qty'] * df_all['Unit_Price']
        
    df_all['Profit'] = _to_num(df_all['PROFIT/LOSS']) if 'PROFIT/LOSS' in df_all.columns else 0

    current_year = datetime.now().year
    months_of_year = [f"{current_year}-{str(i).zfill(2)}" for i in range(1, 13)]
    
    df_all['YearMonth'] = pd.to_datetime(df_all['Date']).dt.strftime('%Y-%m')
    df_year = df_all[df_all['YearMonth'].isin(months_of_year)].copy()

    if df_year.empty:
        print("⚠️ Nta makuru y'umwaka abonetse.")
        return

    unique_products = sorted(df_year['DETAILS'].unique())
    itariki_yakorewe = datetime.now().strftime('%d/%m/%Y saa %H:%M')
    output_pdf = f"{output_folder}/Yearly_Report_{current_year}.pdf"
    
    os.makedirs(output_folder, exist_ok=True)

    pagesize = landscape(A3)
    available_width = pagesize[0] - 20  

    doc = SimpleDocTemplate(
        output_pdf, 
        pagesize=pagesize, 
        rightMargin=10, leftMargin=10, topMargin=10, bottomMargin=10
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('Title', parent=styles['Normal'], alignment=TA_CENTER, fontSize=14, fontName='Helvetica-Bold', spaceAfter=2)
    subtitle_style = ParagraphStyle('SubTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=9, spaceAfter=1)
    report_title_style = ParagraphStyle('ReportTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold')
    date_style = ParagraphStyle('DateRight', parent=styles['Normal'], alignment=TA_RIGHT, fontSize=9, fontName='Helvetica')

    try:
        logo = Image("logo.png", width=1*inch, height=1*inch)
    except:
        logo = Paragraph("<b>T&J</b>", title_style) 

    company_details = [
        Paragraph("<b>T&J; THINK BIG MINING COMPANY LTD</b>", title_style),
        Paragraph("TIN: 121715003", subtitle_style),
        Paragraph("TEL: 0782992433 / 0788977442", subtitle_style),
        Paragraph("Email: uwijacky15@gmail.com", subtitle_style),
    ]
    
    date_paragraph = Paragraph(f"<b>Date:</b> {itariki_yakorewe}", date_style)
    
    header_table = Table([[logo, company_details, date_paragraph]], colWidths=[1.2*inch, 9*inch, 2.5*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),   
        ('ALIGN', (1, 0), (1, 0), 'CENTER'), 
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),  
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    
    elements.append(Paragraph("<hr/>", styles['Normal']))
    elements.append(Spacer(1, 5))
    
    elements.append(Paragraph(f"YEARLY REPORT - RAPPORT Y'UMWAKA {current_year}", report_title_style))
    elements.append(Spacer(1, 10))

    total_income_global = 0
    total_profit_global = 0 # ✅
    grand_total_qty_global = 0
    product_revenue_dict = {}
    product_profit_dict = {} # ✅

    for group_idx in range(0, len(months_of_year), 6):
        months_group = months_of_year[group_idx:group_idx+6]
        
        header_row1 = ["PRODUCTS"]
        header_row2 = [""]
        
        for i, month in enumerate(months_group):
            month_obj = datetime.strptime(month, '%Y-%m')
            month_name = month_obj.strftime('%B')
            header_row1.extend([month_name, "", "", ""]) # ✅ 4 cols
            header_row2.extend(["Qty", "Unit", "Total", "Profit"])
                
        header_row1.extend(["TOTAL", "", "", ""])
        header_row2.extend(["Qty", "Unit", "Total", "Profit"])
        
        table_data = [header_row1, header_row2]
        
        table_styles = [
            ('BACKGROUND', (0, 0), (-1, 1), colors.HexColor("#FFC000")),
            ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8), 
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ]

        table_styles.append(('SPAN', (0, 0), (0, 1)))
        for i in range(len(months_group)):
            start_col = 1 + (i * 4)
            end_col = start_col + 3
            table_styles.append(('SPAN', (start_col, 0), (end_col, 0)))
        table_styles.append(('SPAN', (len(months_group)*4 + 1, 0), (len(months_group)*4 + 4, 0)))

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
            
            for i, month in enumerate(months_group):
                month_data = df_year[(df_year['DETAILS'] == product) & (df_year['YearMonth'] == month)]
                
                if not month_data.empty:
                    qty = month_data['Qty'].sum()
                    price = month_data['Unit_Price'].mean() if not month_data['Unit_Price'].empty else 0
                    total = month_data['Total'].sum()
                    profit = month_data['Profit'].sum() # ✅
                    
                    product_total_qty += qty
                    product_amount += total
                    product_profit += profit
                    
                    if price > 0:
                        last_valid_price = price
                        
                    row.extend([
                        f"{qty:,.0f}" if qty > 0 else "", 
                        f"{price:,.0f}" if price > 0 else "", 
                        f"{total:,.0f}" if total > 0 else "",
                        f"{profit:,.0f}" if profit != 0 else ""
                    ])
                else:
                    row.extend(["", "", "", ""])
                    
            product_revenue_dict[str(product)] = product_revenue_dict.get(str(product), 0) + product_amount
            product_profit_dict[str(product)] = product_profit_dict.get(str(product), 0) + product_profit
            
            row.extend([
                f"{product_total_qty:,.0f}" if product_total_qty > 0 else "", 
                f"{last_valid_price:,.0f}" if last_valid_price > 0 else "", 
                f"{product_amount:,.0f}" if product_amount > 0 else "",
                f"{product_profit:,.0f}" if product_profit != 0 else ""
            ])
            table_data.append(row)
            
            group_total_qty += product_total_qty
            group_total_income += product_amount
            group_total_profit += product_profit
            row_num += 1

        # ✅ UMURONGO WA TOTAL KURI BURI TABLE
        total_row = ["TOTAL"]
        for i, month in enumerate(months_group):
            m_qty = df_year[df_year['YearMonth'] == month]['Qty'].sum()
            m_tot = df_year[df_year['YearMonth'] == month]['Total'].sum()
            m_prof = df_year[df_year['YearMonth'] == month]['Profit'].sum()
            if m_qty > 0 or m_tot > 0:
                total_row.extend([
                    f"{m_qty:,.0f}" if m_qty > 0 else "", 
                    "", 
                    f"{m_tot:,.0f}" if m_tot > 0 else "",
                    f"{m_prof:,.0f}" if m_prof != 0 else ""
                ])
            else:
                total_row.extend(["", "", "", ""])
                
        total_row.extend([
            f"{group_total_qty:,.0f}", "", 
            f"{group_total_income:,.0f}",
            f"{group_total_profit:,.0f}"
        ])
        table_data.append(total_row)
        
        table_styles.extend([
            ('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFF2CC")),
            ('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'),
        ])
        
        # Span kuri col za Qty na Unit kuri TOTAL row (Guhuza Qty na Unit)
        for i in range(len(months_group)):
            s_col = 1 + (i * 4)
            table_styles.append(('SPAN', (s_col, row_num), (s_col + 1, row_num)))
        table_styles.append(('SPAN', (len(months_group)*4 + 1, row_num), (len(months_group)*4 + 2, row_num)))
        
        num_cols = 1 + (len(months_group) * 4) + 4
        
        product_col_width = available_width * 0.12  
        remaining_width = available_width - product_col_width
        other_col_width = remaining_width / (num_cols - 1)
        
        col_widths = [product_col_width] + [other_col_width] * (num_cols - 1)
        
        t = Table(table_data, colWidths=col_widths, repeatRows=2)
        t.setStyle(TableStyle(table_styles))
        
        elements.append(t)
        elements.append(Spacer(1, 15))
        
        total_income_global += group_total_income
        grand_total_qty_global += group_total_qty
        total_profit_global += group_total_profit

    # =========================================================
    # SUMMARY TABLE / INYAMFUKAMUGAYO Y'UMWAKA
    # =========================================================
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>SUMMARY TABLE / INYAMFUKAMUGAYO Y'UMWAKA</b>", ParagraphStyle('SumTitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold', spaceAfter=8)))
    
    summary_data = [["PRODUCT / IGICURUZWA", "TOTAL REVENUE (Rwf)", "TOTAL PROFIT (Rwf)"]] # ✅
    for prod in product_revenue_dict.keys():
        rev = product_revenue_dict[prod]
        prof = product_profit_dict.get(prod, 0)
        summary_data.append([str(prod), f"{rev:,.0f} Rwf", f"{prof:,.0f} Rwf"])
        
    summary_data.append(["GENERAL TOTAL", f"{total_income_global:,.0f} Rwf", f"{total_profit_global:,.0f} Rwf"])

    summary_table = Table(summary_data, colWidths=[4*inch, 3*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 1), (-1, -2), colors.HexColor("#f9f9f9")),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor("#FFC000")),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(summary_table)

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<hr/>", styles['Normal']))
    elements.append(Spacer(1, 30))

    try:
        from helpers import get_signatures
        elements.append(get_signatures())
    except:
        pass
    
    doc.build(elements)
    print(f"✅ STEP 8: Yearly PDF saved at {output_pdf}")

if __name__ == "__main__":
    create_yearly_report()
