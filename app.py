"""
app.py
===========================================================
T&J THINK BIG MINING ENTERPRISE OS — Flask server (Version 3)
All API routes, background auto-update thread (every 5 min),
pre-warm cache on startup, owner vs employee RBAC.

Routes:
  - GET  /                   → templates_v4_final.html
  - GET  /legacy             → jandt.html
  - Auth: /api/auth/*
  - Products: /api/products, /api/products/<pid>, /api/products/bulk
  - Employees: /api/employees, /api/employees/<eid>, /api/employees/<eid>/assignments
  - Services: /api/services, /api/services/<sid>
  - Transactions: /api/transactions
  - Service Transactions: /api/service-transactions
  - Dashboard: /api/dashboard, /api/service-dashboard
  - Reports: /generate_daily|weekly|monthly|yearly
  - Service Reports: /generate_service_daily|weekly|monthly|yearly
===========================================================
"""

import os
import json
import glob
import time
import threading
import traceback
from datetime import datetime, timedelta

from flask import (
    Flask, send_file, jsonify, render_template,
    request, make_response,
)
from flask_cors import CORS

import system_db
import auth
from auth import require_auth, require_owner, current_user, set_server_session_cookie, clear_server_session_cookie

app = Flask(__name__, template_folder=".", static_folder="static")
CORS(app, supports_credentials=True)

REPORTS_DIR = "reports"
if not os.path.exists(REPORTS_DIR):
    os.makedirs(REPORTS_DIR)


# =========================================================
# HTML pages
# =========================================================
@app.route("/")
def index():
    try:
        return render_template("templates_v4_final.html")
    except Exception:
        # fallback if template not yet present
        return render_template("jandt.html")


@app.route("/legacy")
def legacy():
    return render_template("jandt.html")


# =========================================================
# Auth
# =========================================================
@app.route("/api/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    user, token = auth.login(username, password)
    if not user or not token:
        return jsonify({"error": "Invalid credentials or inactive account"}), 401
    resp = make_response(jsonify({"ok": True, "user": _safe_user(user)}))
    set_server_session_cookie(resp, token)
    return resp


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    token = request.cookies.get(auth.SESSION_COOKIE)
    if token:
        auth.logout(token)
    resp = make_response(jsonify({"ok": True}))
    clear_server_session_cookie(resp)
    return resp


@app.route("/api/auth/session", methods=["GET"])
def api_session():
    user = current_user(request)
    if not user:
        return jsonify({"authenticated": False}), 200
    return jsonify({"authenticated": True, "user": _safe_user(user)}), 200


@app.route("/api/auth/forgot-password", methods=["POST"])
def api_forgot_password():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("username") or data.get("email") or "").strip()
    if not identifier:
        return jsonify({"error": "Username or email required"}), 400
    # Demo only: we don't actually send mail; we look up the user and return a hint
    users = system_db.list_users()
    match = next((u for u in users if u["username"].lower() == identifier.lower()
                  or u["email"].lower() == identifier.lower()), None)
    if not match:
        return jsonify({"ok": False, "message": "Ntibyabonetse konti ifite iryo zina."}), 404
    # In real life, send reset email. Here we just confirm.
    return jsonify({
        "ok": True,
        "message": f"Ijambobanga risimburwa rifungurwa. Reba email: {match['email']}",
    })


def _safe_user(u):
    if not u:
        return None
    return {k: v for k, v in u.items() if k not in ("password", "_row_num")}


def _make_fake_request(token):
    """Tiny stand-in to reuse current_user() right after login."""
    class _R:
        cookies = {auth.SESSION_COOKIE: token}
    return _R()


# =========================================================
# Products
# =========================================================
@app.route("/api/products", methods=["GET"])
@require_auth
def api_products_list():
    user = request._user
    include_hidden = (user.get("role") or "").upper() == auth.OWNER
    all_products = system_db.list_products(include_hidden=include_hidden)

    # Employees see only assigned products
    if (user.get("role") or "").upper() != auth.OWNER:
        assigned_ids = {a["product_id"] for a in system_db.list_employee_products(user["id"])}
        all_products = [p for p in all_products if p["id"] in assigned_ids]

    # Strip _row_num from output
    out = [{k: v for k, v in p.items() if k != "_row_num"} for p in all_products]
    return jsonify(out)


@app.route("/api/products", methods=["POST"])
@require_owner
def api_products_create():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "Product name required"}), 400
    prod = system_db.insert_product(data)
    if not prod:
        return jsonify({"error": "Failed to create product"}), 500
    return jsonify(prod), 201


@app.route("/api/products/<pid>", methods=["PUT"])
@require_owner
def api_products_update(pid):
    data = request.get_json(silent=True) or {}
    ok = system_db.update_product(pid, data)
    if not ok:
        return jsonify({"error": "Product not found or update failed"}), 404
    return jsonify({"ok": True})


@app.route("/api/products/<pid>", methods=["DELETE"])
@require_owner
def api_products_delete(pid):
    ok = system_db.delete_product(pid)
    if not ok:
        return jsonify({"error": "Product not found or delete failed"}), 404
    return jsonify({"ok": True})


@app.route("/api/products/bulk", methods=["POST"])
@require_owner
def api_products_bulk():
    data = request.get_json(silent=True) or {}
    items = data.get("products") or []
    if not items:
        return jsonify({"error": "No products provided"}), 400
    created = []
    for it in items:
        if not it.get("name"):
            continue
        p = system_db.insert_product(it)
        if p:
            created.append(p)
    return jsonify({"created": len(created), "products": created}), 201


# =========================================================
# Employees
# =========================================================
@app.route("/api/employees", methods=["GET"])
@require_owner
def api_employees_list():
    users = system_db.list_users()
    out = [
        {k: v for k, v in u.items() if k not in ("password", "_row_num")}
        for u in users if (u.get("role") or "").upper() == auth.EMPLOYEE
    ]
    return jsonify(out)


@app.route("/api/employees", methods=["POST"])
@require_owner
def api_employees_create():
    data = request.get_json(silent=True) or {}
    if not data.get("username") or not data.get("name"):
        return jsonify({"error": "username and name required"}), 400
    data["role"] = auth.EMPLOYEE
    if "active" not in data:
        data["active"] = True
    u = system_db.insert_user(data)
    if not u:
        return jsonify({"error": "Failed to create employee"}), 500
    return jsonify(_safe_user(u)), 201


@app.route("/api/employees/<eid>", methods=["PUT"])
@require_owner
def api_employees_update(eid):
    data = request.get_json(silent=True) or {}
    if "active" in data:
        data["active"] = str(data["active"]).upper()
    ok = system_db.update_user(eid, data)
    if not ok:
        return jsonify({"error": "Employee not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/employees/<eid>", methods=["DELETE"])
@require_owner
def api_employees_delete(eid):
    # Disable (set active=False) — keep record for history
    ok = system_db.update_user(eid, {"active": False})
    if not ok:
        return jsonify({"error": "Employee not found"}), 404
    return jsonify({"ok": True, "disabled": True})


@app.route("/api/employees/<eid>/assignments", methods=["GET"])
@require_owner
def api_employee_assignments_get(eid):
    result = system_db.get_employee_assignments(eid)
    # Also return approver_id
    import json, os
    try:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "employee_approvers.json")
        with open(path, 'r') as f:
            emp_approvers = json.load(f)
        result["approver_id"] = emp_approvers.get(eid, "")
    except:
        result["approver_id"] = ""
    return jsonify(result)


@app.route("/api/employees/<eid>/assignments", methods=["PUT"])
@require_owner
def api_employee_assignments_set(eid):
    data = request.get_json(silent=True) or {}
    product_ids = data.get("product_ids") or []
    service_ids = data.get("service_ids") or []
    approver_id = data.get("approver_id") or ""
    system_db.assign_employee_products(eid, product_ids)
    system_db.assign_employee_services(eid, service_ids)
    # Save approver_id for this employee
    import json, os
    emp_approvers_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "employee_approvers.json")
    try:
        with open(emp_approvers_path, 'r') as f:
            emp_approvers = json.load(f)
    except:
        emp_approvers = {}
    emp_approvers[eid] = approver_id
    with open(emp_approvers_path, 'w') as f:
        json.dump(emp_approvers, f, indent=2)
    return jsonify({"ok": True})

@app.route('/api/employees/<eid>/hard-delete', methods=['POST'])
@require_owner
def api_employees_hard_delete(eid):
    """HARD delete: permanently remove employee from Google Sheets."""
    ok = system_db.delete_user_hard(eid)
    if not ok:
        return jsonify({"error": "Ntibyakunze gusiba umukozi."}), 400
    return jsonify({"ok": True, "mode": "hard"})



# =========================================================
# Services
# =========================================================
@app.route("/api/services", methods=["GET"])
@require_auth
def api_services_list():
    user = request._user
    services = system_db.list_services(active_only=(user.get("role") or "").upper() != auth.OWNER)
    if (user.get("role") or "").upper() != auth.OWNER:
        assigned = {a["service_id"] for a in system_db.list_employee_services(user["id"])}
        services = [s for s in services if s["id"] in assigned]
    out = [{k: v for k, v in s.items() if k != "_row_num"} for s in services]
    return jsonify(out)


@app.route("/api/services", methods=["POST"])
@require_owner
def api_services_create():
    data = request.get_json(silent=True) or {}
    if not data.get("name"):
        return jsonify({"error": "Service name required"}), 400
    s = system_db.insert_service(data)
    if not s:
        return jsonify({"error": "Failed"}), 500
    return jsonify(s), 201


@app.route("/api/services/<sid>", methods=["PUT"])
@require_owner
def api_services_update(sid):
    data = request.get_json(silent=True) or {}
    ok = system_db.update_service(sid, data)
    if not ok:
        return jsonify({"error": "Service not found"}), 404
    return jsonify({"ok": True})


@app.route("/api/services/<sid>", methods=["DELETE"])
@require_owner
def api_services_delete(sid):
    ok = system_db.delete_service(sid)
    if not ok:
        return jsonify({"error": "Service not found"}), 404
    return jsonify({"ok": True})


# =========================================================
# Transactions
# =========================================================
@app.route("/api/transactions", methods=["GET"])
@require_auth
def api_transactions_list():
    user = request._user
    limit = request.args.get("limit", type=int) or 100
    txs = system_db.list_transactions(limit=limit)
    if (user.get("role") or "").upper() != auth.OWNER:
        # Employees only see their own, and hide profit
        txs = [
            {k: v for k, v in t.items() if k not in ("profit", "total_cost", "_row_num")}
            for t in txs if t.get("employee_id") == user["id"]
        ]
    else:
        txs = [{k: v for k, v in t.items() if k != "_row_num"} for t in txs]
    return jsonify(txs)


@app.route("/api/transactions", methods=["POST"])
@require_auth
def api_transactions_create():
    user = request._user
    data = request.get_json(silent=True) or {}
    items = data.get("items") or []
    if not items:
        return jsonify({"error": "No items"}), 400
    payload = {
        "type": (data.get("type") or "SALE").upper(),
        "employee_id": user["id"],
        "employee_name": user.get("name", ""),
        "items": items,
        "notes": data.get("notes", ""),
    }
    tx = system_db.insert_transaction(payload)
    if not tx:
        return jsonify({"error": "Failed to record transaction"}), 500
    return jsonify(tx), 201


# =========================================================
# Service Transactions
# =========================================================
@app.route("/api/service-transactions", methods=["GET"])
@require_auth
def api_service_tx_list():
    user = request._user
    limit = request.args.get("limit", type=int) or 100
    txs = system_db.list_service_transactions(limit=limit)
    if (user.get("role") or "").upper() != auth.OWNER:
        txs = [t for t in txs if t.get("employee_id") == user["id"]]
    out = [{k: v for k, v in t.items() if k != "_row_num"} for t in txs]
    return jsonify(out)


@app.route("/api/service-transactions", methods=["POST"])
@require_auth
def api_service_tx_create():
    user = request._user
    data = request.get_json(silent=True) or {}
    if not data.get("service_id"):
        return jsonify({"error": "service_id required"}), 400
    payload = {
        "service_id": data["service_id"],
        "employee_id": user["id"],
        "employee_name": user.get("name", ""),
        "num_clients": data.get("num_clients", 1),
        "price_per_client": data.get("price_per_client"),
        "notes": data.get("notes", ""),
    }
    tx = system_db.insert_service_transaction(payload)
    if not tx:
        return jsonify({"error": "Failed"}), 500
    return jsonify(tx), 201


# =========================================================
# Dashboards
# =========================================================
@app.route("/api/dashboard", methods=["GET"])
@require_owner
def api_dashboard():
    kpis = system_db.dashboard_kpis()
    charts = system_db.dashboard_charts()
    return jsonify({"kpis": kpis, "charts": charts})


@app.route("/api/service-dashboard", methods=["GET"])
@require_owner
def api_service_dashboard():
    return jsonify(system_db.service_dashboard_stats())


# =========================================================
# Reports — Product PDFs
# =========================================================
def _latest_pdf(pattern):
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)


@app.route("/generate_daily")
@require_owner
def route_daily():
    try:
        from reports_classic import create_daily_report
        path = create_daily_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/generate_weekly")
@require_owner
def route_weekly():
    try:
        from reports_classic import create_weekly_report
        path = create_weekly_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/generate_monthly")
@require_owner
def route_monthly():
    try:
        from reports_classic import create_monthly_report
        path = create_monthly_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/generate_yearly")
@require_owner
def route_yearly():
    try:
        from reports_classic import create_yearly_report
        path = create_yearly_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


# =========================================================
# Reports — Service PDFs
# =========================================================
@app.route("/generate_service_daily")
@require_owner
def route_svc_daily():
    try:
        from service_reports import create_service_daily_report
        path = create_service_daily_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/generate_service_weekly")
@require_owner
def route_svc_weekly():
    try:
        from service_reports import create_service_weekly_report
        path = create_service_weekly_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/generate_service_monthly")
@require_owner
def route_svc_monthly():
    try:
        from service_reports import create_service_monthly_report
        path = create_service_monthly_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


@app.route("/generate_service_yearly")
@require_owner
def route_svc_yearly():
    try:
        from service_reports import create_service_yearly_report
        path = create_service_yearly_report(output_folder=REPORTS_DIR)
        return send_file(path, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500


# =========================================================
# OWNER PROFILE + APPROVERS + SIGNATURE + TRANSLATIONS
# =========================================================
OWNER_PROFILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "owner_profile.json")
SIGNATURE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "owner_signature.json")
TRANSLATIONS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "translations.json")
EMPLOYEE_SIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "employee_signatures.json")
APPROVER_SIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "approver_signatures.json")


def _load_owner_profile():
    """Owner-edited company info + personal details. Falls back to defaults."""
    defaults = {
        "company_name": "T&J THINK BIG MINING",
        "company_full": "T&J THINK BIG MINING COMPANY LTD",
        "tin": "121715003",
        "phone": "0782992433",
        "alt_phone": "0788977442",
        "email": "uwijacky15@gmail.com",
        "address": "Rwanda",
        "drive_link": "",  # Google Drive folder where reports are stored (for QR code)
        "owner_name": "T&J Owner",
        "owner_title": "Managing Director",
        "owner_phone": "0782992433",
        "owner_email": "owner@tjmining.rw",
    }
    try:
        if os.path.exists(OWNER_PROFILE_PATH):
            with open(OWNER_PROFILE_PATH, "r") as f:
                saved = json.load(f)
            defaults.update(saved)
    except Exception as e:
        print(f"[owner_profile] load error: {e}")
    return defaults


def _save_owner_profile(data):
    try:
        with open(OWNER_PROFILE_PATH, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[owner_profile] save error: {e}")
        return False


def _load_signature():
    """Returns {png_base64: '...'} or {} if no signature saved."""
    try:
        if os.path.exists(SIGNATURE_PATH):
            with open(SIGNATURE_PATH, "r") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_signature(b64):
    try:
        with open(SIGNATURE_PATH, "w") as f:
            json.dump({"png_base64": b64}, f)
        return True
    except Exception as e:
        print(f"[signature] save error: {e}")
        return False


@app.route("/api/owner/profile", methods=["GET"])
@require_auth
def api_owner_profile_get():
    return jsonify(_load_owner_profile())


@app.route("/api/owner/profile", methods=["PUT"])
@require_owner
def api_owner_profile_update():
    """Owner edits own + company details. Also updates the Owner's row in
    System_Users (name, phone, email) so the rest of the app sees the change."""
    data = request.get_json(silent=True) or {}
    profile = _load_owner_profile()
    # Update only known keys
    for k in (
        "company_name", "company_full", "tin", "phone", "alt_phone",
        "email", "address", "drive_link",
        "owner_name", "owner_title", "owner_phone", "owner_email",
    ):
        if k in data:
            profile[k] = data[k]
    ok = _save_owner_profile(profile)

    # Also sync owner_name/phone/email into System_Users sheet
    try:
        user = request._user
        if user and user.get("role") == "OWNER":
            updates = {}
            if "owner_name" in data:
                updates["name"] = data["owner_name"]
            if "owner_phone" in data:
                updates["phone"] = data["owner_phone"]
            if "owner_email" in data:
                updates["email"] = data["owner_email"]
            if updates:
                system_db.update_user(user["id"], updates)
    except Exception as e:
        print(f"[owner_profile] sync to sheet failed: {e}")

    return jsonify({"ok": ok, "profile": profile})


@app.route("/api/owner/signature", methods=["GET"])
@require_auth
def api_owner_signature_get():
    sig = _load_signature()
    return jsonify({"has_signature": bool(sig.get("png_base64")), "png_base64": sig.get("png_base64", "")})


@app.route("/api/owner/signature", methods=["PUT"])
@require_owner
def api_owner_signature_update():
    """Save a PNG signature as base64. Body: {png_base64: 'data:image/png;base64,...'}"""
    data = request.get_json(silent=True) or {}
    b64 = data.get("png_base64", "")
    if not b64:
        return jsonify({"error": "png_base64 required"}), 400
    ok = _save_signature(b64)
    return jsonify({"ok": ok})


@app.route("/api/approvers", methods=["GET"])
@require_owner
def api_approvers_list():
    """List all approvers + which employees are assigned to each."""
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "approvers.json")) as f:
            approvers = json.load(f).get("approvers", [])
    except Exception:
        approvers = []
    try:
        with open(os.path.join(base, "employee_approvers.json")) as f:
            emp_approvers = json.load(f)
    except Exception:
        emp_approvers = {}
    # Build a map: approver_id → [employee ids]
    approver_to_emps = {}
    for emp_id, ap_id in emp_approvers.items():
        approver_to_emps.setdefault(ap_id, []).append(emp_id)
    # Attach employee names
    users = system_db.list_users()
    users_by_id = {u["id"]: u for u in users}
    for a in approvers:
        emp_ids = approver_to_emps.get(a["id"], [])
        a["employees"] = [
            {"id": eid, "name": users_by_id.get(eid, {}).get("name", "")}
            for eid in emp_ids
        ]
    return jsonify(approvers)


def _load_approvers_json():
    """Returns the raw approvers.json content as a list."""
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "approvers.json")) as f:
            return json.load(f).get("approvers", [])
    except Exception:
        return []


def _save_approvers_json(approvers):
    """Persist approvers list back to approvers.json."""
    base = os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "approvers.json"), "w") as f:
            json.dump({"approvers": approvers}, f, indent=2)
        return True
    except Exception as e:
        print(f"[approvers] save error: {e}")
        return False


@app.route("/api/approvers", methods=["POST"])
@require_owner
def api_approvers_create():
    """Add a new approver to approvers.json."""
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "Name is required"}), 400
    approvers = _load_approvers_json()
    # Generate a unique id
    existing_ids = {a.get("id", "") for a in approvers}
    n = len(approvers) + 1
    new_id = f"approver_{n:03d}"
    while new_id in existing_ids:
        n += 1
        new_id = f"approver_{n:03d}"
    new_approver = {
        "id": new_id,
        "name": name,
        "title": (data.get("title") or "").strip(),
        "phone": (data.get("phone") or "").strip(),
        "email": (data.get("email") or "").strip(),
        "is_default": bool(data.get("is_default", False)),
    }
    # If is_default is set, clear other defaults
    if new_approver["is_default"]:
        for a in approvers:
            a["is_default"] = False
    approvers.append(new_approver)
    ok = _save_approvers_json(approvers)
    if not ok:
        return jsonify({"error": "Failed to save"}), 500
    return jsonify({"ok": True, "approver": new_approver}), 201


@app.route("/api/approvers/<aid>", methods=["PUT"])
@require_owner
def api_approvers_update(aid):
    """Update an existing approver."""
    data = request.get_json(silent=True) or {}
    approvers = _load_approvers_json()
    target = next((a for a in approvers if a.get("id") == aid), None)
    if not target:
        return jsonify({"error": "Approver not found"}), 404
    # Update fields
    if "name" in data:
        target["name"] = (data["name"] or "").strip() or target["name"]
    if "title" in data:
        target["title"] = (data["title"] or "").strip()
    if "phone" in data:
        target["phone"] = (data["phone"] or "").strip()
    if "email" in data:
        target["email"] = (data["email"] or "").strip()
    if "is_default" in data:
        new_default = bool(data["is_default"])
        if new_default:
            for a in approvers:
                a["is_default"] = (a.get("id") == aid)
        else:
            target["is_default"] = False
    ok = _save_approvers_json(approvers)
    if not ok:
        return jsonify({"error": "Failed to save"}), 500
    return jsonify({"ok": True, "approver": target})


@app.route("/api/approvers/<aid>", methods=["DELETE"])
@require_owner
def api_approvers_delete(aid):
    """Delete an approver. Also removes any employee → approver mappings that point to it."""
    approvers = _load_approvers_json()
    target = next((a for a in approvers if a.get("id") == aid), None)
    if not target:
        return jsonify({"error": "Approver not found"}), 404
    if target.get("is_default"):
        return jsonify({"error": "Cannot delete the default approver. Set another as default first."}), 400
    approvers = [a for a in approvers if a.get("id") != aid]
    ok = _save_approvers_json(approvers)
    if not ok:
        return jsonify({"error": "Failed to save"}), 500
    # Clean up employee_approvers.json — remove any mapping pointing to this approver
    base = os.path.dirname(os.path.abspath(__file__))
    emp_appr_path = os.path.join(base, "employee_approvers.json")
    try:
        with open(emp_appr_path, "r") as f:
            emp_appr = json.load(f)
        cleaned = {eid: ap_id for eid, ap_id in emp_appr.items() if ap_id != aid}
        with open(emp_appr_path, "w") as f:
            json.dump(cleaned, f, indent=2)
    except Exception as e:
        print(f"[approvers] cleanup emp_approvers error: {e}")
    # Also remove any signature stored for this approver
    appr_sig_path = os.path.join(base, "approver_signatures.json")
    try:
        with open(appr_sig_path, "r") as f:
            appr_sigs = json.load(f)
        if aid in appr_sigs:
            del appr_sigs[aid]
            with open(appr_sig_path, "w") as f:
                json.dump(appr_sigs, f, indent=2)
    except Exception:
        pass
    return jsonify({"ok": True, "deleted_id": aid})


@app.route("/api/owner/password", methods=["PUT"])
@require_owner
def api_owner_password_update():
    """Owner changes own password."""
    data = request.get_json(silent=True) or {}
    new_pw = data.get("new_password", "").strip()
    if not new_pw or len(new_pw) < 4:
        return jsonify({"error": "Password must be at least 4 characters"}), 400
    user = request._user
    ok = system_db.update_user(user["id"], {"password": new_pw})
    if not ok:
        return jsonify({"error": "Failed to update password"}), 500
    return jsonify({"ok": True})


# =========================================================
# EMPLOYEE + APPROVER SIGNATURES
# =========================================================
def _load_emp_signatures():
    """Returns {employee_id: {png_base64, name, signed_at}}."""
    try:
        if os.path.exists(EMPLOYEE_SIG_PATH):
            with open(EMPLOYEE_SIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_emp_signatures(data):
    try:
        with open(EMPLOYEE_SIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[emp_sigs] save error: {e}")
        return False


def _load_appr_signatures():
    """Returns {approver_id: {png_base64, name, signed_at}}."""
    try:
        if os.path.exists(APPROVER_SIG_PATH):
            with open(APPROVER_SIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_appr_signatures(data):
    try:
        with open(APPROVER_SIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[appr_sigs] save error: {e}")
        return False


# --- Employee signature endpoints ---
@app.route("/api/employees/my-signature", methods=["GET"])
@require_auth
def api_my_signature_get():
    """Employee reads their own signature."""
    user = request._user
    sigs = _load_emp_signatures()
    sig = sigs.get(user["id"], {})
    return jsonify({
        "has_signature": bool(sig.get("png_base64")),
        "png_base64": sig.get("png_base64", ""),
        "name": sig.get("name", user.get("name", "")),
        "signed_at": sig.get("signed_at", ""),
    })


@app.route("/api/employees/my-signature", methods=["PUT"])
@require_auth
def api_my_signature_update():
    """Employee saves their own signature."""
    data = request.get_json(silent=True) or {}
    b64 = data.get("png_base64", "")
    if not b64:
        return jsonify({"error": "png_base64 required"}), 400
    user = request._user
    sigs = _load_emp_signatures()
    sigs[user["id"]] = {
        "png_base64": b64,
        "name": user.get("name", ""),
        "signed_at": datetime.now().isoformat(timespec="seconds"),
    }
    ok = _save_emp_signatures(sigs)
    return jsonify({"ok": ok})


@app.route("/api/employees/<eid>/signature", methods=["GET"])
@require_owner
def api_employee_signature_get(eid):
    """Owner reads any employee's signature."""
    sigs = _load_emp_signatures()
    sig = sigs.get(eid, {})
    return jsonify({
        "has_signature": bool(sig.get("png_base64")),
        "png_base64": sig.get("png_base64", ""),
        "name": sig.get("name", ""),
        "signed_at": sig.get("signed_at", ""),
    })


@app.route("/api/employees/<eid>/signature", methods=["PUT"])
@require_owner
def api_employee_signature_update(eid):
    """Owner updates any employee's signature (e.g. on their behalf)."""
    data = request.get_json(silent=True) or {}
    b64 = data.get("png_base64", "")
    if not b64:
        return jsonify({"error": "png_base64 required"}), 400
    sigs = _load_emp_signatures()
    # Look up employee name
    name = ""
    try:
        for u in system_db.list_users():
            if u["id"] == eid:
                name = u.get("name", "")
                break
    except Exception:
        pass
    sigs[eid] = {
        "png_base64": b64,
        "name": name,
        "signed_at": datetime.now().isoformat(timespec="seconds"),
    }
    ok = _save_emp_signatures(sigs)
    return jsonify({"ok": ok})


# --- Approver signature endpoints ---
@app.route("/api/approvers/<aid>/signature", methods=["GET"])
@require_auth
def api_approver_signature_get(aid):
    """Read an approver's signature."""
    sigs = _load_appr_signatures()
    sig = sigs.get(aid, {})
    return jsonify({
        "has_signature": bool(sig.get("png_base64")),
        "png_base64": sig.get("png_base64", ""),
        "name": sig.get("name", ""),
        "signed_at": sig.get("signed_at", ""),
    })


@app.route("/api/approvers/<aid>/signature", methods=["PUT"])
@require_owner
def api_approver_signature_update(aid):
    """Owner updates an approver's signature."""
    data = request.get_json(silent=True) or {}
    b64 = data.get("png_base64", "")
    if not b64:
        return jsonify({"error": "png_base64 required"}), 400
    sigs = _load_appr_signatures()
    # Look up approver name
    name = ""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "approvers.json")) as f:
            approvers = json.load(f).get("approvers", [])
        for a in approvers:
            if a["id"] == aid:
                name = a.get("name", "")
                break
    except Exception:
        pass
    sigs[aid] = {
        "png_base64": b64,
        "name": name,
        "signed_at": datetime.now().isoformat(timespec="seconds"),
    }
    ok = _save_appr_signatures(sigs)
    return jsonify({"ok": ok})


@app.route("/api/signatures/all", methods=["GET"])
@require_owner
def api_all_signatures():
    """Owner gets all signatures (employees + approvers) for management view."""
    return jsonify({
        "employees": _load_emp_signatures(),
        "approvers": _load_appr_signatures(),
        "owner": _load_signature() if os.path.exists(SIGNATURE_PATH) else {},
    })


# =========================================================
# UI TRANSLATIONS — JSON dictionary of all UI strings
# =========================================================
def _load_translations():
    """Load the translations JSON. Returns dict. Falls back to empty dict on error."""
    try:
        if os.path.exists(TRANSLATIONS_PATH):
            with open(TRANSLATIONS_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[translations] load error: {e}")
    return {}


def _save_translations(data):
    try:
        with open(TRANSLATIONS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[translations] save error: {e}")
        return False


@app.route("/api/translations", methods=["GET"])
def api_translations_get():
    """Return the full translations dictionary. Available to anyone authenticated."""
    return jsonify(_load_translations())


@app.route("/api/translations", methods=["PUT"])
@require_owner
def api_translations_update():
    """Owner edits any UI string. Body: {key: new_value, ...} — merges into existing."""
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict) or not data:
        return jsonify({"error": "Body must be a non-empty JSON object {key: value}"}), 400
    current = _load_translations()
    updated_count = 0
    new_keys = []
    for k, v in data.items():
        if k.startswith("_"):
            continue  # don't allow editing comment keys
        if k in current:
            current[k] = v
            updated_count += 1
        else:
            current[k] = v
            new_keys.append(k)
    ok = _save_translations(current)
    return jsonify({
        "ok": ok,
        "updated": updated_count,
        "added_new": len(new_keys),
        "new_keys": new_keys,
        "total_keys": len(current),
    })


# =========================================================
# SYSTEM RESET — wipe all business data, keep Owner account
# =========================================================
@app.route("/api/system/reset", methods=["POST"])
@require_owner
def api_system_reset():
    """
    Wipe selected parts of the system so the Owner can start over.

    Body:
      {
        "confirm": "RESET",                  # mandatory safety latch
        "targets": [                         # optional — default is ["all"]
          "products",                        # wipe System_Products
          "transactions",                    # wipe System_Transactions + TransactionItems
          "services",                        # wipe System_Services
          "service_transactions",            # wipe System_ServiceTransactions
          "employee_assignments",            # wipe EmployeeProducts + EmployeeServices
          "employees",                       # wipe System_Users EXCEPT Owner
          "reports",                         # delete PDF files in /reports
          "sessions",                        # clear sessions.json (keep Owner's)
          "approvers_mapping"                # reset employee_approvers.json to {}
          "all"                              # OR wipe everything (default)
        ]
      }

    If `targets` is omitted or contains "all", wipes everything.
    """
    data = request.get_json(silent=True) or {}
    if (data.get("confirm") or "").strip().upper() != "RESET":
        return jsonify({
            "error": "Confirmation missing. Send {\"confirm\":\"RESET\"} to proceed."
        }), 400

    # Validate targets
    valid_targets = {
        "products", "transactions", "services", "service_transactions",
        "employee_assignments", "employees", "reports", "sessions",
        "approvers_mapping", "all",
    }
    targets = data.get("targets") or ["all"]
    if isinstance(targets, str):
        targets = [targets]
    bad = [t for t in targets if t not in valid_targets]
    if bad:
        return jsonify({
            "error": f"Unknown targets: {bad}. Valid: {sorted(valid_targets)}"
        }), 400

    user = request._user
    owner_id = user.get("id")

    # Separate sheet-level targets from file-level targets
    sheet_targets = [t for t in targets if t not in ("reports", "sessions", "approvers_mapping", "all")]
    if "all" in targets or not targets:
        sheet_targets = ["all"]  # reset_all_system will expand

    # 1. Reset sheets via system_db
    try:
        summary = system_db.reset_all_system(
            keep_owner_id=owner_id,
            targets=sheet_targets,
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Reset failed on Google Sheets: " + str(e)}), 500

    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Delete PDF reports (only if "reports" or "all" requested)
    if "reports" in targets or "all" in targets:
        try:
            reports_dir = os.path.join(base_dir, REPORTS_DIR)
            deleted_pdfs = 0
            if os.path.isdir(reports_dir):
                for fn in os.listdir(reports_dir):
                    if fn.lower().endswith(".pdf"):
                        try:
                            os.remove(os.path.join(reports_dir, fn))
                            deleted_pdfs += 1
                        except Exception:
                            pass
            summary["reports_deleted"] = deleted_pdfs
        except Exception as e:
            summary["reports_deleted"] = f"error: {e}"

    # 3. Reset employee_approvers.json (only if "approvers_mapping" or "all" or "employees" requested)
    if "approvers_mapping" in targets or "all" in targets or "employees" in targets:
        emp_approvers_path = os.path.join(base_dir, "employee_approvers.json")
        try:
            with open(emp_approvers_path, "w") as f:
                json.dump({}, f)
            summary["employee_approvers"] = "reset"
        except Exception as e:
            summary["employee_approvers"] = f"error: {e}"

    # 4. Clear sessions.json (only if "sessions" or "all" requested)
    if "sessions" in targets or "all" in targets:
        sessions_path = os.path.join(base_dir, "sessions.json")
        try:
            owner_token = request.cookies.get(auth.SESSION_COOKIE)
            with open(sessions_path, "w") as f:
                json.dump({}, f)
            # Re-issue Owner's session so they stay logged in
            if owner_token:
                from datetime import datetime as _dt, timedelta as _td
                new_sessions = {
                    owner_token: {
                        "user_id": owner_id,
                        "expires_at": (_dt.now() + _td(days=7)).isoformat(),
                    }
                }
                with open(sessions_path, "w") as f:
                    json.dump(new_sessions, f)
            summary["sessions_cleared"] = True
        except Exception as e:
            summary["sessions_cleared"] = f"error: {e}"

    print(f"\n🧹 SYSTEM RESET by Owner {user.get('username')} ({owner_id})")
    print(f"   Targets: {targets}")
    print(f"   Summary: {summary}\n")

    return jsonify({
        "ok": True,
        "message": "Reset complete for: " + ", ".join(targets),
        "targets": targets,
        "summary": summary,
    })


# =========================================================
# Background auto-update (every 5 min — all 8 reports)
# =========================================================
def background_auto_update():
    print("⏳ Auto-Update thread started. Generating all 8 reports every 5 min.")
    # Initial small delay to let server bind
    time.sleep(20)
    while True:
        try:
            now = datetime.now()
            print(f"\n⏰ [{now.strftime('%H:%M:%S')}] Generating all 8 reports...")
            from reports_classic import (
                create_daily_report, create_weekly_report,
                create_monthly_report, create_yearly_report,
            )
            from service_reports import (
                create_service_daily_report, create_service_weekly_report,
                create_service_monthly_report, create_service_yearly_report,
            )
            try: create_daily_report()
            except Exception as e: print(f"  daily err: {e}")
            try: create_weekly_report()
            except Exception as e: print(f"  weekly err: {e}")
            try: create_monthly_report()
            except Exception as e: print(f"  monthly err: {e}")
            try: create_yearly_report()
            except Exception as e: print(f"  yearly err: {e}")
            try: create_service_daily_report()
            except Exception as e: print(f"  svc daily err: {e}")
            try: create_service_weekly_report()
            except Exception as e: print(f"  svc weekly err: {e}")
            try: create_service_monthly_report()
            except Exception as e: print(f"  svc monthly err: {e}")
            try: create_service_yearly_report()
            except Exception as e: print(f"  svc yearly err: {e}")
            print("🎉 All reports generated.")
        except Exception as e:
            print(f"❌ Auto-Update error: {e}")
            traceback.print_exc()
        time.sleep(300)


# =========================================================
# Main
# =========================================================
if __name__ == "__main__":
    # Pre-warm cache
    try:
        system_db._prewarm_cache()
    except Exception as e:
        print(f"⚠️ Pre-warm failed: {e}")

    # Start background thread
    loop_thread = threading.Thread(target=background_auto_update, daemon=True)
    loop_thread.start()

    print("🚀 T&J THINK BIG MINING ENTERPRISE OS — http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
