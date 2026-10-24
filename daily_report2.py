# daily_report.py
import pandas as pd
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
import sheets_invetory_reader as sheets_reader 
from helpers import *

def create_daily_report(output_folder="reports"):
    print("🔄 Turafata amakuru muri Google Sheets (Daily Report)...")
    
    # 1. Soma 'Daily Report'
    df = sheets_reader.read_as_table("Daily Report")
    
    if df.empty:
        print("❌ Nta makuru yabonetse.")
        return

    # =========================================================
    # 2. GUSHAKA ITARIKI MURI SHEET
    # =========================================================
    itariki_iri_muri_sheet = ""
    
    for i in range(min(10, len(df))):
        try:
            possible_date_d = str(df.iloc[i, 3]).strip()
            possible_date_c = str(df.iloc[i, 2]).strip()
            
            if "/" in possible_date_d and len(possible_date_d) >= 8:
                datetime.strptime(possible_date_d.split(" ")[0], "%m/%d/%Y")
                itariki_iri_muri_sheet = possible_date_d.split(" ")[0]
                break
            elif "/" in possible_date_c and len(possible_date_c) >= 8:
                datetime.strptime(possible_date_c.split(" ")[0], "%m/%d/%Y")
                itariki_iri_muri_sheet = possible_date_c.split(" ")[0]
                break
        except:
            continue

    if not itariki_iri_muri_sheet:
        print("⚠️ Ntibyakunze kubona itariki muri Sheet. Turakoresha iy'uyu munsi.")
        itariki_iri_muri_sheet = datetime.now().strftime("%m/%d/%Y")

    print(f"📅 Itariki yabonetse: {itariki_iri_muri_sheet}")

    # =========================================================
    # 3. GUKORA SEARCH Y'UMUNSI
    # =========================================================
    try:
        itariki_obj = datetime.strptime(itariki_iri_muri_sheet, "%m/%d/%Y")
        umunsi_num = itariki_obj.weekday()
        amazina_yiminsi = ["kuwambere", "kuwakabiri", "kuwagatatu", "kuwakane", "kuwagatanu", "kuwagatandatu", "kucyumweru"]
        izina_ry_umunsi = amazina_yiminsi[umunsi_num]
    except Exception as e:
        print(f"⚠️ Ntibyakunye gukora search y'umunsi: {e}")
        izina_ry_umunsi = "umunsi"

    # =========================================================
    # 4. GUTEGURA IZINA RYA FILE
    # =========================================================
    try:
        itariki_fmt = datetime.strptime(itariki_iri_muri_sheet, "%m/%d/%Y").strftime("%Y-%m-%d")
    except:
        itariki_fmt = datetime.now().strftime("%Y-%m-%d")

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    output_pdf = f"{output_folder}/Daily_Report_{izina_ry_umunsi}_{itariki_fmt}.pdf"
    csv_filename = f"{output_folder}/daily_{izina_ry_umunsi}_{itariki_fmt}.csv"

    print(f"✅ Umunsi wabonetse: {izina_ry_umunsi}")
    print(f"💾 Izina rya PDF: Daily_Report_{izina_ry_umunsi}_{itariki_fmt}.pdf")
    print(f"💾 Izina rya CSV: daily_{izina_ry_umunsi}_{itariki_fmt}.csv")

    # --- KUBIKA AMAKURU MURI CSV ---
    # HANO: Nongeyeho 'DAILY REPORT', 'RAPPORT', 'DATE', 'T&J', etc.
    mask = ~df.iloc[:, 0].astype(str).str.upper().str.contains(
        'TOTAL|IMBOGA|DETAILS|KWIZERA|UWIMANA|BIKOREWE|T&J|TIN|DAILY REPORT|RAPPORT|DATE|IBYUMWERU', 
        na=False
    )
    df_to_save = df[mask]
    df_to_save.to_csv(csv_filename, index=False)
    print(f"✅ CSV YABITSWE MURI: {csv_filename}")

    # =========================================================
    # 5. GUKORA PDF
    # =========================================================
    doc = SimpleDocTemplate(output_pdf, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20)
    elements = [get_company_header(), Paragraph("<hr/>", styles['Normal']), Spacer(1, 2)]
    
    elements.append(Paragraph(f"<b>DAILY REPORT - RAPPORT UMUNSI KUWA {itariki_iri_muri_sheet} ({izina_ry_umunsi.capitalize()})</b>", report_title_style))

    table_data = [["DETAILS", "QUANTITY", "UNITY PRICE", "TOTAL/RWF"]]
    table_styles = get_base_table_style()
    
    row_num = 1 
    for index, row in df.iterrows():
        col1 = str(row.iloc[0]).strip()
        col2 = str(row.iloc[1]).strip() if len(row) > 1 else ""
        
        # =========================================================
        # HANO: GUKURAHO IMIRONGO YOSE ITARI IY'IBICURUZWA
        # =========================================================
        # Kurengera umutwe w'ikigo n'amakuru yayo
        if "T&J" in col1.upper() or "TIN" in col1.upper() or "TEL" in col1.upper() or "EMAIL" in col1.upper():
            continue
            
        # Kurengera umutwe w'imbonerahamwe (Daily Report, Rapport, etc.)
        if "DAILY REPORT" in col1.upper() or "RAPPORT" in col1.upper() or "IBYUMWERU" in col1.upper():
            continue
            
        # Kurengera itariki (Date) niba iri muri col1 cyangwa col2
        if "DATE" in col1.upper() or "DATE" in col2.upper():
            continue
            
        # Kurengera imikono (KWIZERA, UWIMANA, Teller, Managing Director)
        if "BIKOREWE" in col1.upper() or "KWIZERA" in col1.upper() or "UWIMANA" in col1.upper() or "TELLER" in col2.upper() or "MANAGING" in col2.upper():
            continue
            
        if col1.upper() == "DETAILS" or col1 == "" or "TIMESTAMP" in col1.upper():
            continue

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

    return output_pdf

if __name__ == "__main__":
    create_daily_report()