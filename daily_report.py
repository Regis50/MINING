# daily_report.py
import pandas as pd
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
import sheets_invetory_reader as sheets_reader 
from helpers import *

def create_daily_report(output_pdf="T&J_Daily_Report.pdf"):
    print("🔄 Turafata amakuru muri Google Sheets (Daily Report)...")
    df = sheets_reader.read_as_table("Daily Report")
    
    if df.empty:
        print("❌ Nta makuru yabonetse.")
        return

    # --- KUBIKA AMAKURU MURI CSV ---
    if not os.path.exists("daily_reports"):
        os.makedirs("daily_reports")
        
    uyu_munsi = datetime.now().strftime("%Y-%m-%d")
    csv_filename = f"daily_reports/daily_{uyu_munsi}.csv"
    
    # Kubika gusa imirongo y'ibicuruzwa (turengera TOTAL n'Imboga)
    df_to_save = df[~df.iloc[:, 0].astype(str).str.upper().str.contains('TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE', na=False)]
    df_to_save.to_csv(csv_filename, index=False)
    print(f"💾 Amakuru yabitswe muri: {csv_filename}")

    # --- GUKORA PDF ---
    doc = SimpleDocTemplate(output_pdf, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = [get_company_header(), Paragraph("<hr/>", styles['Normal']), Spacer(1, 2)]
    
    uyu_munsi_fmt = datetime.now().strftime("%d/%m/%Y")
    elements.append(Paragraph(f"<b>DAILY REPORT - RAPPORT UMUNSI WA {uyu_munsi_fmt}</b>", report_title_style))

    table_data = [["DETAILS", "QUANTITY", "UNITY PRICE", "TOTAL/RWF"]]
    table_styles = get_base_table_style()
    
    row_num = 1 
    for index, row in df.iterrows():
        col1 = str(row.iloc[0]).strip()
        if col1.upper() == "DETAILS" or col1 == "": continue
        if "BIKOREWE" in col1.upper() or "KWIZERA" in col1.upper() or "UWIMANA" in col1.upper(): continue

        col2 = str(row.iloc[1]).strip() if len(row) > 1 else ""
        col3 = str(row.iloc[2]).strip() if len(row) > 2 else ""
        col4 = str(row.iloc[3]).strip() if len(row) > 3 else ""

        table_data.append([col1, col2, col3, col4])

        if col1.upper() == "TOTAL" or col1.upper() == "IMBOGA TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif "IMBOGA SECTION" in col1.upper():
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif col1.upper() == "GENERAL TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
            table_styles.append(('BACKGROUND', (3, row_num), (3, row_num), colors.HexColor("#4472C4")))
            table_styles.append(('TEXTCOLOR', (3, row_num), (3, row_num), colors.white))
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        row_num += 1

    table = Table(table_data, colWidths=[3.5*inch, 1*inch, 1*inch, 1.2*inch])
    table.setStyle(TableStyle(table_styles))
    elements.append(table)
    
    elements.append(Spacer(1, 5)) 
    elements.append(Paragraph(f"<b>BIKOREWE MU Ruhango</b>", footer_text_style))
    elements.append(Paragraph(f"<i>(Raporo yakozwe kuwa {datetime.now().strftime('%d/%m/%Y saa %H:%M')})</i>", igihe_style))
    elements.append(Spacer(1, 30)) 
    elements.append(get_signatures())
    
    doc.build(elements)
    print(f"✅ PDF Y'UMUNSI YAKOZWE: {output_pdf}")

if __name__ == "__main__":
    create_daily_report()