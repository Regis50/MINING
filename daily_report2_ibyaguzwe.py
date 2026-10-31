# daily_report2.py
import pandas as pd
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
import sheets_invetory_reader as sheets_reader 
from helpers import *

def create_daily_report(output_folder="reports"):
    print("🔄 Turafata amakuru muri Google Sheets...")
    
    # ✅ HINDURA HANO: Sheet yahindutse "Copy of ibyaguzwe"
    df = sheets_reader.read_as_table("Copy of ibyaguzwe", header_row=4, data_start_row=5)
    
    if df.empty:
        print("❌ Nta makuru yabonetse.")
        return

    # Gushaka itariki
    itariki_iri_muri_sheet = ""
    for i in range(min(10, len(df))):
        try:
            for col in df.columns:
                val = str(df.iloc[i][col]).strip()
                if "/" in val and len(val) >= 8:
                    datetime.strptime(val.split(" ")[0], "%m/%d/%Y")
                    itariki_iri_muri_sheet = val.split(" ")[0]
                    break
            if itariki_iri_muri_sheet: break
        except:
            continue

    if not itariki_iri_muri_sheet:
        itariki_iri_muri_sheet = datetime.now().strftime("%m/%d/%Y")

    try:
        itariki_obj = datetime.strptime(itariki_iri_muri_sheet, "%m/%d/%Y")
        umunsi_num = itariki_obj.weekday()
        amazina_yiminsi = ["kuwambere", "kuwakabiri", "kuwagatatu", "kuwakane", "kuwagatanu", "kuwagatandatu", "kucyumweru"]
        izina_ry_umunsi = amazina_yiminsi[umunsi_num]
        itariki_fmt = itariki_obj.strftime("%Y-%m-%d")
    except:
        izina_ry_umunsi = "umunsi"
        itariki_fmt = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    output_pdf = f"{output_folder}/Daily_Report_{izina_ry_umunsi}_{itariki_fmt}.pdf"
    
    doc = SimpleDocTemplate(output_pdf, pagesize=landscape(A4), rightMargin=15, leftMargin=15, topMargin=15, bottomMargin=15)
    elements = [get_company_header(), Paragraph("<hr/>", styles['Normal']), Spacer(1, 5)]
    
    elements.append(Paragraph(f"<b>DAILY REPORT - {itariki_iri_muri_sheet} ({izina_ry_umunsi.capitalize()})</b>", report_title_style))

    # =========================================================
    # IMBOONERAHAMWE (Gukoresha inkingi 8 n'amabara y'umwimerere)
    # =========================================================
    table_data = [
        ["DETAILS", "STOCK YOSE", "", "", "IBYAGURISHIJWE", "", "", "IBISIGAYE MURI STOCK", ""],
        ["", "TOTAL STOCK", "UNIT PRICE", "TOTAL SOLD", "UNIT PRICE", "SOLD AMOUNT", "CURRENT STOCK", "PROFIT/LOSS"]
    ]
    
    col_widths = [1.5*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.2*inch, 1.2*inch, 1.2*inch]
    
    table_styles = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor("#4472C4")), 
        ('TEXTCOLOR', (0, 0), (0, 1), colors.white),
        ('BACKGROUND', (1, 0), (3, 0), colors.HexColor("#FFC000")), 
        ('BACKGROUND', (4, 0), (6, 0), colors.HexColor("#E2EFDA")), 
        ('BACKGROUND', (7, 0), (8, 0), colors.HexColor("#DDEBF7")), 
        
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor("#F2F2F2")),
        ('FONTNAME', (0, 0), (-1, 1), 'Helvetica-Bold'),
        
        ('SPAN', (0, 0), (0, 1)), 
        ('SPAN', (1, 0), (3, 0)), 
        ('SPAN', (4, 0), (6, 0)), 
        ('SPAN', (7, 0), (8, 0)), 
    ]
    
    row_num = 2 
    for index, row in df.iterrows():
        col1 = str(row.iloc[0]).strip()
        
        if col1.upper() in ['', 'NAN', 'DETAILS', 'KUGURISHA', 'IMBOGA SECTION']: continue

        # ✅ HINDURA DATA HANO: Gufata inkingi zihwanye neza na Sheet ya "Copy of ibyaguzwe"
        total_stock = str(row.iloc[7]).strip() if len(row) > 7 else ""    # TOTAL QUANTITY [H]
        unit_price = str(row.iloc[5]).strip() if len(row) > 5 else ""     # UNITY PRICE [F]
        today_qty = str(row.iloc[1]).strip() if len(row) > 1 else ""      # TODAY QUANTITY [B]
        total_sold = str(row.iloc[1]).strip() if len(row) > 1 else ""     # TODAY QUANTITY [B]
        unit_price_2 = str(row.iloc[2]).strip() if len(row) > 2 else ""   # AVG UNIT PRICE [C]
        sold_amount = str(row.iloc[3]).strip() if len(row) > 3 else ""    # TODAY AMOUNT [D]
        current_stock = str(row.iloc[4]).strip() if len(row) > 4 else ""  # LAST QUANTITY [E]
        profit_loss = str(row.iloc[9]).strip() if len(row) > 9 else ""    # TOTAL AMOUNT [J]

        table_data.append([col1, total_stock, unit_price, today_qty, total_sold, unit_price_2, sold_amount, current_stock, profit_loss])

        if col1.upper() == "TOTAL" or col1.upper() == "IMBOGA TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif "IMBOGA SECTION" in col1.upper():
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif col1.upper() == "GENERAL TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
            table_styles.append(('BACKGROUND', (6, row_num), (6, row_num), colors.HexColor("#4472C4")))
            table_styles.append(('TEXTCOLOR', (6, row_num), (6, row_num), colors.white))
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
            
        row_num += 1

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle(table_styles))
    elements.append(table)
    
    # =========================================================
    # INCAMAKE (SUMMARY)
    # =========================================================
    elements.append(Spacer(1, 15))
    summary_title_style = ParagraphStyle('SumTitle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)
    elements.append(Paragraph("<b>INCAMAKE Y'UMUNSI (DAILY SUMMARY)</b>", summary_title_style))
    elements.append(Spacer(1, 5))

    total_final_amount = 0
    for _, row in df.iterrows():
        if str(row.iloc[0]).strip().upper() == 'GENERAL TOTAL':
            # ✅ HINDURA DATA HANO: Gufata Total Amount [J] muri index ya 9
            amt = str(row.iloc[9]).replace(',', '').replace('RWF', '').strip() 
            try: total_final_amount = float(amt)
            except: pass
            break

    summary_data = [
        ["IKIGERERANYO (METRIC)", "AGACIRO (VALUE)"],
        ["Amafaranga Yose Yinjiye (Total Amount)", f"{total_final_amount:,.0f} RWF"]
    ]
    
    summary_table = Table(summary_data, colWidths=[4*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#f9f9f9")), 
    ]))
    elements.append(summary_table)

    elements.append(Spacer(1, 10)) 
    elements.append(Paragraph(f"<b>BIKOREWE MU Ruhango</b>", footer_text_style))
    
    ubu_gihe = datetime.now()
    elements.append(Paragraph(f"<i>(Raporo yakozwe kuwa {ubu_gihe.strftime('%d/%m/%Y')} saa {ubu_gihe.strftime('%H:%M')})</i>", igihe_style))
    
    elements.append(Spacer(1, 20)) 
    elements.append(get_signatures())
    
    doc.build(elements)
    print(f"✅ PDF Y'UMUNSI YAKOZWE: {output_pdf}")

    return output_pdf

if __name__ == "__main__":
    create_daily_report()
