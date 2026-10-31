# helpers.py
from datetime import datetime
import os, json, base64
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph, Image, Spacer
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


def _load_owner_profile():
    """Load owner-edited profile (company info + owner details). Falls back to defaults."""
    defaults = {
        "company_name": "T&J THINK BIG MINING",
        "company_full": "T&J THINK BIG MINING COMPANY LTD",
        "tin": "121715003",
        "phone": "0782992433",
        "alt_phone": "0788977442",
        "email": "uwijacky15@gmail.com",
        "address": "Rwanda",
        "drive_link": "",
        "owner_name": "T&J Owner",
        "owner_title": "Managing Director",
        "owner_phone": "0782992433",
        "owner_email": "owner@tjmining.rw",
    }
    try:
        path = os.path.join(os.path.dirname(__file__), "owner_profile.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                defaults.update(json.load(f))
    except Exception:
        pass
    return defaults


def get_owner_profile():
    """Public accessor so report builders can read owner profile."""
    return _load_owner_profile()


def _load_signature_png():
    """Returns the saved OWNER signature as a ReportLab Image, or None if missing."""
    try:
        path = os.path.join(os.path.dirname(__file__), "owner_signature.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            data = json.load(f)
        b64 = data.get("png_base64", "")
        if not b64:
            return None
        # Strip data URL prefix if present
        if "," in b64 and b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        png_bytes = base64.b64decode(b64)
        # Write to temp file so ReportLab Image can load it
        tmp = os.path.join(os.path.dirname(__file__), "_sig_owner_tmp.png")
        with open(tmp, "wb") as f:
            f.write(png_bytes)
        return Image(tmp, width=1.6*inch, height=0.5*inch)
    except Exception as e:
        print(f"[helpers] owner signature load error: {e}")
        return None


def _load_employee_signature_png(employee_id):
    """Returns the employee's signature as a ReportLab Image, or None."""
    if not employee_id:
        return None
    try:
        path = os.path.join(os.path.dirname(__file__), "employee_signatures.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            sigs = json.load(f)
        sig = sigs.get(employee_id, {})
        b64 = sig.get("png_base64", "")
        if not b64:
            return None
        if "," in b64 and b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        png_bytes = base64.b64decode(b64)
        tmp = os.path.join(os.path.dirname(__file__), "_sig_emp_tmp.png")
        with open(tmp, "wb") as f:
            f.write(png_bytes)
        return Image(tmp, width=1.5*inch, height=0.45*inch)
    except Exception as e:
        print(f"[helpers] employee signature load error: {e}")
        return None


def _load_approver_signature_png(approver_id):
    """Returns the approver's signature as a ReportLab Image, or None."""
    if not approver_id:
        return None
    try:
        path = os.path.join(os.path.dirname(__file__), "approver_signatures.json")
        if not os.path.exists(path):
            return None
        with open(path, "r") as f:
            sigs = json.load(f)
        sig = sigs.get(approver_id, {})
        b64 = sig.get("png_base64", "")
        if not b64:
            return None
        if "," in b64 and b64.startswith("data:"):
            b64 = b64.split(",", 1)[1]
        png_bytes = base64.b64decode(b64)
        tmp = os.path.join(os.path.dirname(__file__), "_sig_appr_tmp.png")
        with open(tmp, "wb") as f:
            f.write(png_bytes)
        return Image(tmp, width=1.6*inch, height=0.5*inch)
    except Exception as e:
        print(f"[helpers] approver signature load error: {e}")
        return None


def _find_employee_id_by_name(name):
    """Look up an employee's id by their name."""
    try:
        import system_db
        for u in system_db.list_users():
            if str(u.get("name", "")).lower() == str(name).lower():
                return u.get("id")
    except Exception:
        pass
    return None


def _find_approver_id_by_name(name):
    """Look up an approver's id by their name."""
    try:
        approvers = _load_approvers()
        for a in approvers:
            if str(a.get("name", "")).lower() == str(name).lower():
                return a.get("id")
    except Exception:
        pass
    return None


def _load_approvers():
    try:
        path = os.path.join(os.path.dirname(__file__), "approvers.json")
        with open(path, "r") as f:
            return json.load(f).get("approvers", [])
    except Exception:
        return []


def _load_emp_approvers():
    try:
        path = os.path.join(os.path.dirname(__file__), "employee_approvers.json")
        with open(path, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def get_approver_for_employees(employee_names):
    """Look up the approver assigned to employees who made transactions.
    Returns (approver_name, approver_phone, approver_title)."""
    try:
        emp_approvers = _load_emp_approvers()
        approvers = _load_approvers()
        import system_db
        users = system_db.list_users()
        for name in employee_names or []:
            for u in users:
                if str(u.get("name", "")).lower() == str(name).lower():
                    emp_id = u.get("id")
                    ap_id = emp_approvers.get(emp_id)
                    if ap_id:
                        for a in approvers:
                            if a.get("id") == ap_id:
                                return a.get("name", ""), a.get("phone", ""), a.get("title", "")
        # Fallback: default approver
        for a in approvers:
            if a.get("is_default"):
                return a.get("name", ""), a.get("phone", ""), a.get("title", "")
        if approvers:
            return approvers[0].get("name", ""), approvers[0].get("phone", ""), approvers[0].get("title", "")
    except Exception:
        pass
    return None, None, None


def get_employee_info(employee_names):
    """For the first employee in the list, return (name, phone, title).
    title is 'Employee' unless we can match an approver title."""
    try:
        import system_db
        users = system_db.list_users()
        for name in employee_names or []:
            for u in users:
                if str(u.get("name", "")).lower() == str(name).lower():
                    return u.get("name", ""), u.get("phone", ""), u.get("role", "Employee").title()
        # If no exact match, return first name with defaults
        if employee_names:
            return employee_names[0], "", "Employee"
    except Exception:
        pass
    return None, None, None


def _make_qr_code(url):
    """Generate a QR code Image for a URL. Returns ReportLab Image.
    Requires the `qrcode` and `Pillow` libraries (in requirements.txt).
    If they're missing, returns an error Paragraph explaining the issue.
    """
    if not url:
        return None
    try:
        import qrcode
        # Build the QR with high error correction so it scans even if printed small
        qr = qrcode.QRCode(
            version=None,  # auto-fit
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        # Save to a temp file so ReportLab can load it as Image
        tmp = os.path.join(os.path.dirname(__file__), "_qr_tmp.png")
        img.save(tmp, format="PNG")
        # Verify the file was actually written
        if not os.path.exists(tmp) or os.path.getsize(tmp) < 100:
            print("[helpers] QR file write failed or too small")
            return Paragraph(
                f"<font size='7' color='#990000'>QR generation failed — check qrcode/Pillow install</font>",
                subtitle_style,
            )
        # Return a smaller, professional QR image (1 inch square default —
        # the footer overrides drawWidth/drawHeight to 0.95" for compact display)
        return Image(tmp, width=1.0*inch, height=1.0*inch)
    except ImportError as e:
        missing = 'qrcode'
        try:
            import qrcode  # noqa
        except ImportError:
            missing = 'qrcode'
        try:
            from PIL import Image as _PILImage  # noqa
        except ImportError:
            missing = missing + ' + Pillow'
        print(f"[helpers] QR ImportError: {e} — missing: {missing}")
        return Paragraph(
            f"<font size='7' color='#990000'>QR ntiyaremewe: install {missing} (pip install {missing.replace(' + ', ' ')})</font>",
            subtitle_style,
        )
    except Exception as e:
        print(f"[helpers] QR error: {e}")
        import traceback
        traceback.print_exc()
        return Paragraph(
            f"<font size='7' color='#990000'>QR error: {e}</font>",
            subtitle_style,
        )


def get_company_header():
    """Iyi function izana Umutwe w'Ikigo na Logo — uses owner-edited profile."""
    profile = _load_owner_profile()
    try:
        logo = Image("logo.png", width=0.8*inch, height=0.8*inch)
    except:
        logo = Paragraph("<b>T&J</b>", title_style)

    company_details = [
        Paragraph(f"<b>{profile.get('company_full', 'T&J THINK BIG MINING COMPANY LTD')}</b>", title_style),
        Paragraph(f"TIN: {profile.get('tin', '121715003')}", subtitle_style),
        Paragraph(f"TEL: {profile.get('phone', '0782992433')} / {profile.get('alt_phone', '0788977442')}", subtitle_style),
        Paragraph(f"Email: {profile.get('email', 'uwijacky15@gmail.com')}", subtitle_style),
        Paragraph(f"Address: {profile.get('address', 'Rwanda')}", subtitle_style),
    ]

    header_table = Table([[logo, company_details]], colWidths=[1*inch, 6*inch])
    header_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'CENTER'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    return header_table


def get_signatures():
    """Deprecated stub — kept for backward compat. Use get_report_footer() instead."""
    return Spacer(1, 10)


def get_report_footer(employee_names=None, title_text=None):
    """Build the new footer with:
      - Title + generated-on date (centered)
      - 2-column signature layout:
          LEFT  = employee signature image + "Prepared by" info
          RIGHT = approver signature image + "Approved by" info
      - Verification QR code (bottom-right) — encodes a JSON payload with:
          company, report_type, date, signed_by (emp), approved_by (approver),
          signed_at timestamp, and a content hash for tamper detection.
        When scanned, any QR reader displays the verification info.
    """
    from reportlab.platypus import KeepTogether
    import hashlib

    profile = _load_owner_profile()
    ap_name, ap_phone, ap_title = get_approver_for_employees(employee_names)
    emp_name, emp_phone, emp_title = get_employee_info(employee_names)

    # Fallbacks
    if not ap_name:
        ap_name = profile.get("owner_name", "T&J Owner")
        ap_phone = profile.get("owner_phone", "0782992433")
        ap_title = profile.get("owner_title", "Managing Director")
    if not emp_name and employee_names:
        emp_name = employee_names[0]
    if not emp_name:
        emp_name = "—"
    if not emp_title:
        emp_title = "Employee"
    if not emp_phone:
        emp_phone = "—"

    # Look up signature images
    emp_id = _find_employee_id_by_name(emp_name) if emp_name != "—" else None
    ap_id = _find_approver_id_by_name(ap_name)
    emp_sig_img = _load_employee_signature_png(emp_id) if emp_id else None
    ap_sig_img = _load_approver_signature_png(ap_id) if ap_id else None
    # If approver has no signature but is the Owner, fall back to owner signature
    if not ap_sig_img:
        owner_sig = _load_signature_png()
        if owner_sig and ap_name == profile.get("owner_name", "T&J Owner"):
            ap_sig_img = owner_sig

    def _esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Title + date
    out = []
    out.append(Spacer(1, 10))
    if title_text:
        out.append(Paragraph(f"<b>{_esc(title_text)}</b>", footer_text_style))
    ubu_gihe = datetime.now()
    iso_ts = ubu_gihe.isoformat(timespec="seconds")
    out.append(Paragraph(
        f"<i>(Raporo yakozwe kuwa {ubu_gihe.strftime('%d/%m/%Y')} "
        f"saa {ubu_gihe.strftime('%H:%M')})</i>",
        igihe_style,
    ))
    out.append(Spacer(1, 20))

    # Build signature lines (2 columns: employee | approver)
    emp_label_style = ParagraphStyle('EmpLabel', parent=styles['Normal'], fontSize=8, alignment=TA_LEFT, textColor=colors.HexColor("#333333"), fontName="Helvetica-Bold")
    emp_detail_style = ParagraphStyle('EmpDetail', parent=styles['Normal'], fontSize=7, alignment=TA_LEFT, textColor=colors.HexColor("#555555"))
    appr_label_style = ParagraphStyle('ApprLabel', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT, textColor=colors.HexColor("#333333"), fontName="Helvetica-Bold")
    appr_detail_style = ParagraphStyle('ApprDetail', parent=styles['Normal'], fontSize=7, alignment=TA_RIGHT, textColor=colors.HexColor("#555555"))

    # LEFT cell: employee signature + info
    left_cell = [Paragraph("Prepared by (Umukozi):", emp_label_style)]
    if emp_sig_img:
        left_cell.append(emp_sig_img)
        left_cell.append(Spacer(1, 2))
    else:
        left_cell.append(Spacer(1, 30))  # blank space for handwritten sig
    left_cell.append(Paragraph(f"<b>{_esc(emp_name)}</b>", emp_label_style))
    left_cell.append(Paragraph(f"Tel: {_esc(emp_phone)}", emp_detail_style))
    left_cell.append(Paragraph(f"Position: {_esc(emp_title)}", emp_detail_style))

    # RIGHT cell: approver signature + info
    right_cell = [Paragraph("Approved by (Mwemeza):", appr_label_style)]
    if ap_sig_img:
        right_cell.append(ap_sig_img)
        right_cell.append(Spacer(1, 2))
    else:
        right_cell.append(Spacer(1, 30))
    right_cell.append(Paragraph(f"<b>{_esc(ap_name)}</b>", appr_label_style))
    right_cell.append(Paragraph(f"Tel: {_esc(ap_phone)}", appr_detail_style))
    right_cell.append(Paragraph(f"Title: {_esc(ap_title)}", appr_detail_style))

    # 2-column signature table
    sig_table = Table([[left_cell, right_cell]], colWidths=[3.25*inch, 3.25*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LINEABOVE', (0, 0), (-1, 0), 0.3, colors.HexColor("#CCCCCC")),
    ]))
    out.append(sig_table)

    # ===== VERIFICATION QR CODE =====
    # Build a self-contained verification payload
    verification_payload = {
        "company": profile.get("company_name", "T&J THINK BIG MINING"),
        "tin": profile.get("tin", "121715003"),
        "report_type": title_text or "Report",
        "date": ubu_gihe.strftime('%Y-%m-%d'),
        "time": ubu_gihe.strftime('%H:%M'),
        "signed_by": emp_name if emp_name != "—" else "",
        "approved_by": ap_name,
        "signed_at": iso_ts,
    }
    # Compute a verification hash from the payload (tamper detection)
    payload_str = json.dumps(verification_payload, sort_keys=True, ensure_ascii=False)
    hash_str = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()[:16]
    verification_payload["hash"] = hash_str
    # Encode as compact JSON string for the QR
    qr_data = json.dumps(verification_payload, ensure_ascii=False, separators=(",", ":"))
    # If a drive_link is set, prepend it (so QR includes both verification + Drive URL)
    drive_link = profile.get("drive_link", "")
    if drive_link:
        qr_data = drive_link + "\n---VERIFY---\n" + qr_data

    qr_img = _make_qr_code(qr_data)
    if qr_img:
        # ===== PROFESSIONAL CENTERED QR CODE =====
        # Compact: just the QR + a small caption below it (no side text).
        # Centered horizontally. Small footprint (~1 inch square).
        out.append(Spacer(1, 6))
        # Force the QR image to a smaller, professional size (0.95 inch)
        try:
            qr_img.drawWidth = 0.95 * inch
            qr_img.drawHeight = 0.95 * inch
        except Exception:
            pass
        # Tiny caption — single line, gray, italic
        qr_caption_style = ParagraphStyle(
            'QRCaption',
            parent=styles['Normal'],
            fontSize=6,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#888888"),
            fontName="Helvetica-Oblique",
            spaceBefore=2,
            spaceAfter=0,
            leading=7,
        )
        qr_cell = [
            qr_img,
            Paragraph(f"Scan to verify · {hash_str[:8]}", qr_caption_style),
        ]
        # Wrap QR + caption in a single-cell table so we can center the content
        qr_table = Table([[qr_cell]], colWidths=[6.5*inch])
        qr_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        out.append(qr_table)
    else:
        # Fallback: just show the hash as tiny centered text
        out.append(Spacer(1, 4))
        out.append(Paragraph(
            f"<font size='6' color='#888888'><i>Verify · {hash_str[:8]}</i></font>",
            subtitle_style
        ))

    return KeepTogether(out)


def get_report_submitter(employee_names=None, approver_name=None, approver_phone=None):
    """Backward-compat wrapper. New code should use get_report_footer()."""
    from reportlab.platypus import KeepTogether
    if not approver_name or not approver_phone:
        ap_name, ap_phone, _ = get_approver_for_employees(employee_names)
        approver_name = approver_name or ap_name
        approver_phone = approver_phone or ap_phone
    if not approver_name:
        approver_name = "T&J Owner"
    if not approver_phone:
        approver_phone = "0782992433"

    def _esc(s):
        return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    submitter_style = ParagraphStyle('SubmitterFooter', parent=styles['Normal'], fontSize=8, alignment=TA_CENTER, textColor=colors.grey, spaceBefore=5, spaceAfter=2)
    approver_style = ParagraphStyle('ApproverFooter', parent=styles['Normal'], fontSize=9, alignment=TA_CENTER, textColor=colors.HexColor("#333333"), spaceBefore=2, spaceAfter=10, fontName="Helvetica-Bold")

    elements = []
    if employee_names:
        seen = set()
        unique_names = []
        for n in employee_names:
            if n and n.lower() not in seen:
                seen.add(n.lower())
                unique_names.append(n)
        if unique_names:
            names_text = ", ".join(_esc(n) for n in unique_names)
            elements.append(Paragraph(f"Transactions by: {names_text}", submitter_style))
    elements.append(Paragraph(f"Approved by: {_esc(approver_name)} &mdash; Tel: {_esc(approver_phone)}", approver_style))
    return KeepTogether(elements)


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