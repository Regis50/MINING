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
    
    df = sheets_reader.read_as_table("Copy of ibyagurishijwe", header_row=4, data_start_row=5)
    
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
                    datetime.strptime(val.split(" "), "%m/%d/%Y")
                    itariki_iri_muri_sheet = val.split(" ")
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
    
    styles = getSampleStyleSheet()
    
    header_text_style_white = ParagraphStyle(
        'TableHeaderWhite',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.white,
        alignment=TA_CENTER
    )
    
    header_text_style_dark = ParagraphStyle(
        'TableHeaderDark',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.black,
        alignment=TA_CENTER
    )

    elements = [get_company_header(), Paragraph("<hr/>", styles['Normal']), Spacer(1, 5)]
    elements.append(Paragraph(f"<b>DAILY REPORT - {itariki_iri_muri_sheet} ({izina_ry_umunsi.capitalize()})</b>", report_title_style))

    # =========================================================
    # IMBOONERAHAMWE (Zose hamwe ni inkingi 8 zuzuye neza)
    # =========================================================
    table_data = [
        [
            Paragraph("DETAILS", header_text_style_white), 
            Paragraph("STOCK YOSE", header_text_style_dark), "", 
            Paragraph("IBYAGURISHIJWE", header_text_style_dark), "", "", 
            Paragraph("IBYASIGAYE MURI STOCK", header_text_style_dark), ""
        ],
        [
            "", 
            Paragraph("TOTAL STOCK", header_text_style_dark), 
            Paragraph("UNIT PRICE", header_text_style_dark), 
            Paragraph("TOTAL SOLD", header_text_style_dark), 
            Paragraph("UNIT PRICE", header_text_style_dark), 
            Paragraph("SOLD AMOUNT", header_text_style_dark), 
            Paragraph("CURRENT STOCK", header_text_style_dark), 
            Paragraph("PROFIT/LOSS", header_text_style_dark)
        ]
    ]
    
    col_widths = [1.6*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.1*inch, 1.2*inch, 1.3*inch, 1.3*inch]
    
    # ✅ KOSORA HANO: Gutunganya ama BACKGROUND na SPAN zikaza ku nkingi zazo neza neza
    table_styles = [
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        ('BACKGROUND', (0, 0), (0, 1), colors.HexColor("#4472C4")), # DETAILS (Blue)
        ('BACKGROUND', (1, 0), (2, 0), colors.HexColor("#FFC000")), # STOCK YOSE (Orange/Yellow - Col 1 kugeza 2)
        ('BACKGROUND', (3, 0), (5, 0), colors.HexColor("#E2EFDA")), # IBYAGURISHIJWE (Light Green - Col 3 kugeza 5)
        ('BACKGROUND', (6, 0), (7, 0), colors.HexColor("#DDEBF7")), # IBYASIGAYE MURI STOCK (Light Blue - Col 6 kugeza 7)
        
        ('BACKGROUND', (1, 1), (-1, 1), colors.HexColor("#F2F2F2")),
        
        ('SPAN', (0, 0), (0, 1)),   # DETAILS
        ('SPAN', (1, 0), (2, 0)),   # STOCK YOSE ihubura ku nkingi 2 (Total Stock na Unit Price)
        ('SPAN', (3, 0), (5, 0)),   # IBYAGURISHIJWE ihubura ku nkingi 3 (Total Sold, Unit Price, na Sold Amount)
        ('SPAN', (6, 0), (7, 0)),   # IBYASIGAYE MURI STOCK ihubura ku nkingi 2 (Current Stock na Profit/Loss)
    ]
    
    max_qty_sold = -1
    most_sold_product = "Nta gicuruzwa"
    total_profit_loss = 0.0
    total_final_amount = 0.0

    row_num = 2 
    for index, row in df.iterrows():
        col1 = str(row.iloc[0]).strip()
        
        if col1.upper() in ['', 'NAN', 'DETAILS', 'KUGURISHA', 'IMBOGA SECTION']: continue

        total_stock = str(row.iloc[1]).strip() if len(row) > 1 else ""
        unit_price = str(row.iloc[2]).strip() if len(row) > 2 else ""
        total_sold = str(row.iloc[3]).strip() if len(row) > 3 else ""
        unit_price_2 = str(row.iloc[4]).strip() if len(row) > 4 else ""
        sold_amount = str(row.iloc[5]).strip() if len(row) > 5 else ""
        current_stock = str(row.iloc[6]).strip() if len(row) > 6 else ""
        profit_loss = str(row.iloc[7]).strip() if len(row) > 7 else ""

        table_data.append([col1, total_stock, unit_price, total_sold, unit_price_2, sold_amount, current_stock, profit_loss])

        if col1.upper() not in ["TOTAL", "IMBOGA TOTAL", "GENERAL TOTAL"]:
            try:
                qty = float(total_sold.replace(',', '').strip())
                if qty > max_qty_sold:
                    max_qty_sold = qty
                    most_sold_product = col1
            except ValueError:
                pass

        if col1.upper() == 'GENERAL TOTAL':
            try:
                total_final_amount = float(sold_amount.replace(',', '').replace('RWF', '').strip())
            except:
                pass
            try:
                total_profit_loss = float(profit_loss.replace(',', '').replace('RWF', '').strip())
            except:
                pass

        if col1.upper() == "TOTAL" or col1.upper() == "IMBOGA TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif "IMBOGA SECTION" in col1.upper():
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif col1.upper() == "GENERAL TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
            table_styles.append(('BACKGROUND', (5, row_num), (5, row_num), colors.HexColor("#4472C4")))
            table_styles.append(('TEXTCOLOR', (5, row_num), (5, row_num), colors.white))
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
            
        row_num += 1

    table = Table(table_data, colWidths=col_widths)
    table.setStyle(TableStyle(table_styles))
    elements.append(table)
    
    # =========================================================
    # INCAMAKE (SUMMARY TABLE)
    # =========================================================
    elements.append(Spacer(1, 15))
    summary_title_style = ParagraphStyle('SumTitle', parent=styles['Normal'], fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)
    elements.append(Paragraph("<b>INCAMAKE Y'UMUNSI (DAILY SUMMARY)</b>", summary_title_style))
    elements.append(Spacer(1, 5))

    profit_text = f"{total_profit_loss:,.0f} RWF" if total_profit_loss >= 0 else f"{total_profit_loss:,.0f} RWF (Igihombo)"

    summary_data = [
        ["IKIGERERANYO (METRIC)", "AGACIRO (VALUE)"],
        ["Amafaranga Yose Yinjiye (Total Sales Amount)", f"{total_final_amount:,.0f} RWF"],
        ["Inyungu Yose Hamwe (Total Profit/Loss)", profit_text],
        ["Igicuruzwa Cyaguzwe Cyane (Most Sold Item)", f"{most_sold_product} ({max_qty_sold:,.0f})"]
    ]
    
    summary_table = Table(summary_data, colWidths=[4.5*inch, 3*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4472C4")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (1, 1), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#F9F9F9")), 
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

    # =========================================================
    # GUKORA CSV NA EXCEL (Nk'uko byakozwe muri Version 1)
    # =========================================================
    csv_filename = f"{output_folder}/daily_{izina_ry_umunsi}_{itariki_fmt}.csv"
    excel_filename = f"{output_folder}/Daily_Report_{izina_ry_umunsi}_{itariki_fmt}.xlsx"

    # Kurengera imirongo itari iy'ibicuruzwa (uko byakozwe muri V1)
    mask = ~df.iloc[:, 0].astype(str).str.upper().str.contains(
        'TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE|T&J|TIN|DAILY REPORT|RAPPORT|DATE|IBYUMWERU|KUGURISHA',
        na=False
    )
    # =========================================================
    # GUKORA CSV NA EXCEL (inkingi zose zikomeze - nk'uko byakozwe muri Version 1)
    # Twongerereye amazina meza kugira ngo weekly_report.py abone
    # inkingi zisanzwe: DETAILS, TODAY QUANTITY, AVG UNIT PRICE
    # =========================================================
    RENAME = {0: 'DETAILS', 1: 'TOTAL STOCK', 2: 'UNIT PRICE', 3: 'TODAY QUANTITY', 4: 'AVG UNIT PRICE', 5: 'SOLD AMOUNT', 6: 'CURRENT STOCK', 7: 'PROFIT/LOSS'}
    df_to_save = df[mask].copy()
    new_cols = list(df_to_save.columns)
    for i, name in RENAME.items():
        if i < len(new_cols):
            new_cols[i] = name
    df_to_save.columns = new_cols

    # Kubika CSV (ifungura muri Excel)
    try:
        df_to_save.to_csv(csv_filename, index=False)
        print(f"✅ CSV YABITSWE MURI: {csv_filename}")
    except Exception as e:
        print(f"⚠️ Ikindi kibazo cyabaye kuri CSV: {e}")

    # Kubika Excel (.xlsx)
    try:
        df_to_save.to_excel(excel_filename, index=False, engine='openpyxl')
        print(f"✅ EXCEL YABITSWE MURI: {excel_filename}")
    except ImportError:
        print("\n❌ IKOSA: Excel ntabwo yakozwe kuko mudasobwa yawe idafite 'openpyxl'.")
        print("💡 Gukosora: Run-inga iri tegeko kuri terminal yawe: pip install openpyxl\n")
    except Exception as e:
        print(f"⚠️ Ikindi kibazo cyabaye kuri Excel: {e}")

    return output_pdf

if __name__ == "__main__":
    create_daily_report()
