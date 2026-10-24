# helpers.py
from datetime import datetime
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import sheets_invetory_reader as sheets_reader

styles = getSampleStyleSheet()

# Imiterere y'inyandiko isanzwe
title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=TA_CENTER, fontSize=12, spaceAfter=2)
subtitle_style = ParagraphStyle('SubtitleStyle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, spaceAfter=1)
report_title_style = ParagraphStyle('ReportTitle', parent=styles['Heading2'], alignment=TA_CENTER, fontSize=9, spaceAfter=5)
footer_text_style = ParagraphStyle('FooterText', parent=styles['Normal'], alignment=TA_CENTER, fontSize=8, spaceAfter=10)
igihe_style = ParagraphStyle('IgiheStyle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=7, textColor=colors.grey)
sig_style = ParagraphStyle('Sig', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')

def get_company_header():
    """Iyi function izana Umutwe w'Ikigo na Logo"""
    try:
        logo = Image("logo.png", width=0.8*inch, height=0.8*inch)
    except:
        logo = Paragraph("<b>T&J</b>", title_style) 

    company_details = [
        Paragraph("<b>T&J THINK BIG MINING COMPANY LTD</b>", title_style),
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
    return header_table

def get_signatures():
    """Iyi function izana imikono ivuye muri Google Sheets"""
    df_abakozi = sheets_reader.read_as_table("Abakozi")
    
    if df_abakozi.empty:
        abakozi_list = [
            {"Amazina": "KWIZERA Leonard", "Umwanya": "Teller", "Icyiciro": "LEFT"},
            {"Amazina": "UWIMANA Jacqueline", "Umwanya": "Managing Director", "Icyiciro": "RIGHT"}
        ]
    else:
        abakozi_list = df_abakozi.to_dict('records')

    mukozi_ibumoso = next((m for m in abakozi_list if "LEFT" in str(m.get('Icyiciro', '')).upper()), None)
    mukozi_iburyo = next((m for m in abakozi_list if "RIGHT" in str(m.get('Icyiciro', '')).upper()), None)

    sig_1_text = f"{mukozi_ibumoso.get('Amazina', '')}<br/><br/>{mukozi_ibumoso.get('Umwanya', '')}" if mukozi_ibumoso else ""
    sig_2_text = f"{mukozi_iburyo.get('Amazina', '')}<br/><br/>{mukozi_iburyo.get('Umwanya', '')}" if mukozi_iburyo else ""

    style_ibumoso = ParagraphStyle('SigLeft', parent=sig_style, alignment=TA_LEFT)
    style_iburyo = ParagraphStyle('SigRight', parent=sig_style, alignment=TA_RIGHT)

    sig_data = [[Paragraph(sig_1_text, style_ibumoso), Paragraph(sig_2_text, style_iburyo)]]
    sig_table = Table(sig_data, colWidths=[3.5*inch, 3.5*inch])
    sig_table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP')]))
    return sig_table

def get_base_table_style():
    """Iyi ni style isanzwe y'imbonerahamwe"""
    return [
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