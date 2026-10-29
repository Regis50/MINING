import pandas as pd
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Dukoresha file yawe nk'uko wabisabye
import sheets_invetory_reader as sheets_reader 

def create_pro_report(output_pdf="T&J_Think_Big_Report_OnePage.pdf"):
    print("🔄 Turafata amakuru muri Google Sheets...")
    
    # 1. Fata amakuru ya Daily Report
    df_daily = sheets_reader.read_as_table("Daily Report")
    if df_daily.empty:
        print("❌ Nta makuru yabonetse muri Daily Report.")
        return

    # 2. Fata amakuru y'Abakozi (Signature)
    print("🔄 Turafata abakozi muri Tab 'Abakozi'...")
    df_abakozi = sheets_reader.read_as_table("Abakozi")
    
    if df_abakozi.empty:
        print("⚠️ Nta bakozi babonetse muri Tab 'Abakozi'. Turakoresha abasanzwe.")
        # Niba nta bakozi muri Sheet, dukoresha aba basanzwe
        abakozi_list = [
            {"Amazina": "KWIZERA Leonard", "Umwanya": "Teller", "Icyiciro": "LEFT"},
            {"Amazina": "UWIMANA Jacqueline", "Umwanya": "Managing Director", "Icyiciro": "RIGHT"}
        ]
    else:
        # Guhindura amakuru ya Pandas mu buryo bwa list ya dictionaries
        abakozi_list = df_abakozi.to_dict('records')

    # 3. Gutegura PDF
    doc = SimpleDocTemplate(
        output_pdf,
        pagesize=A4,
        rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=20
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
    subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, spaceAfter=1)
    report_title_style = ParagraphStyle('ReportTitle', parent=styles['Heading2'], alignment=TA_CENTER, fontSize=9, spaceAfter=5)
    
    footer_text_style = ParagraphStyle('FooterText', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, spaceAfter=10)
    igihe_style = ParagraphStyle('IgiheStyle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7, textColor=colors.grey)
    
    # Imikono izaba inyuguti nini gato
    sig_style = ParagraphStyle('Sig', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')

    elements = []
    
    # ==========================================
    # UMUTWE (HEADER) - Logo n'amakuru y'ikigo
    # ==========================================
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
    
    header_table = Table([[logo, company_details]], colWidths=[1*inch, 6*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    
    elements.append(Paragraph("<hr/>", styles['Normal'])) 
    elements.append(Spacer(1, 2))
    
    # ==========================================
    # UMUTWE W'RAPORO
    # ==========================================
    uyu_munsi = datetime.now().strftime("%d/%m/%Y")
    umutwe_wa_raporo = f"<b>DAILY REPORT - RAPPORT UMUNSI WA {uyu_munsi}</b>"
    elements.append(Paragraph(umutwe_wa_raporo, report_title_style))

    # ==========================================
    # IMBONERAHAMWE Y'IBICURUZWA
    # ==========================================
    table_data = [["DETAILS", "QUANTITY", "UNITY PRICE", "TOTAL/RWF"]]
    table_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#FFC000")), 
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'), 
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 2),
        ('TOPPADDING', (0, 0), (-1, 0), 2),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black), 
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 1),
        ('TOPPADDING', (0, 1), (-1, -1), 1),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]

    row_num = 1 
    itariki_yanditse = "BIKOREWE MU Ruhango" 

    for index, row in df_daily.iterrows():
        col1 = str(row.iloc[0]).strip()
        col2 = str(row.iloc[1]).strip() if len(row) > 1 else ""
        col3 = str(row.iloc[2]).strip() if len(row) > 2 else ""
        col4 = str(row.iloc[3]).strip() if len(row) > 3 else ""

        if col1.upper() == "DETAILS" or (col1 == "" and col2 == "" and col3 == "" and col4 == ""):
            continue
            
        if "BIKOREWE" in col1.upper() or "Ruhango" in col1:
            itariki_yanditse = col1 
            continue 
            
        # Kurengera imikono niba yanditse muri Daily Report
        if "KWIZERA" in col1.upper() or "UWIMANA" in col1.upper():
            continue

        table_data.append([col1, col2, col3, col4])

        if col1.upper() == "TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif "IMBOGA SECTION" in col1.upper():
            table_styles.append(('FONTNAME', (0, row_num), (-1, row_num), 'Helvetica-Bold'))
        elif col1.upper() == "IMBOGA TOTAL":
            table_styles.append(('BACKGROUND', (0, row_num), (-1, row_num), colors.HexColor("#FFC000")))
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
    
    # ==========================================
    # ITARIKI N'IGIHE
    # ==========================================
    elements.append(Spacer(1, 5)) 
    elements.append(Paragraph(f"<b>{itariki_yanditse}</b>", footer_text_style))
    
    igihe_yakorewe = datetime.now().strftime("%d/%m/%Y saa %H:%M")
    elements.append(Paragraph(f"<i>(Raporo yakozwe kuwa {igihe_yakorewe})</i>", igihe_style))
    
    elements.append(Spacer(1, 30)) 
    
    # ==========================================
    # GUKORA IMIKONO IVUYE MURI SHEET
    # ==========================================
    # Dushaka abantu babiri: Umwe uri LEFT, undi uri RIGHT
    mukozi_ibumoso = None
    mukozi_iburyo = None
    
    for mukozi in abakozi_list:
        icyiciro = str(mukozi.get('Icyiciro', '')).upper()
        
        # Gushaka umukozi wo ibumoso
        if "LEFT" in icyiciro and mukozi_ibumoso is None:
            mukozi_ibumoso = mukozi
            
        # Gushaka umukozi wo iburyo
        if "RIGHT" in icyiciro and mukozi_iburyo is None:
            mukozi_iburyo = mukozi

    # Niba hatabonetse umwe muri bo, dushyiraho umwanya ubusa
    sig_1_text = ""
    sig_2_text = ""
    
    if mukozi_ibumoso:
        sig_1_text = f"{mukozi_ibumoso.get('Amazina', '')}<br/><br/>{mukozi_ibumoso.get('Umwanya', '')}"
        
    if mukozi_iburyo:
        sig_2_text = f"{mukozi_iburyo.get('Amazina', '')}<br/><br/>{mukozi_iburyo.get('Umwanya', '')}"

    # Dushyira imikono muri Table
    style_ibumoso = ParagraphStyle('SigLeft', parent=sig_style, alignment=TA_LEFT)
    style_iburyo = ParagraphStyle('SigRight', parent=sig_style, alignment=TA_RIGHT)

    sig_data = [
        [Paragraph(sig_1_text, style_ibumoso), Paragraph(sig_2_text, style_iburyo)]
    ]
    
    sig_table = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    elements.append(sig_table)
    
    doc.build(elements)
    print(f"✅ PDF YAKOZWE NEZA: {output_pdf}")

if __name__ == "__main__":
    create_pro_report()
