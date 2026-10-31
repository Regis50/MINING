"""
system_db.py
===========================================================
T&J THINK BIG MINING ENTERPRISE OS
Google Sheets CRUD layer (Version 3) with:
  - In-memory cache (60s TTL)
  - Batch reads via _batch_read_tabs
  - Pre-warm cache via _prewarm_cache
  - User / Product / Transaction / Service / Employee CRUD
  - Dashboard analytics
Reads use _read_tab (returns list of dicts with _row_num)
Writes use _append_row / _update_cell (invalidate cache)
===========================================================
"""

import os
import time
import uuid
import threading
from datetime import datetime, timedelta, date

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Reuse the SHEET_ID from the existing reader module
import sheets_invetory_reader as sr
SHEET_ID = sr.SHEET_ID
CREDENTIALS_FILE = "credentials.json"

# ---------------------------------------------------------
# Scope & client init (gspread based, read+write)
# ---------------------------------------------------------
_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
_gc = None
_gc_lock = threading.Lock()


def _client():
    """Return a cached gspread client (thread-safe)."""
    global _gc
    if _gc is None:
        with _gc_lock:
            if _gc is None:
                creds = ServiceAccountCredentials.from_json_keyfile_name(
                    CREDENTIALS_FILE, _SCOPE
                )
                _gc = gspread.authorize(creds)
    return _gc


def _spreadsheet():
    return _client().open_by_key(SHEET_ID)


# ---------------------------------------------------------
# Cache layer (60s TTL)
# ---------------------------------------------------------
_CACHE_TTL = 60  # seconds
_cache = {}  # tab_name -> (timestamp, rows)
_cache_lock = threading.Lock()


def _invalidate(tab_name=None):
    """Invalidate one tab or entire cache (mark stale by setting timestamp to 0,
    but keep the data so a subsequent rate-limited read can still fall back to it)."""
    with _cache_lock:
        if tab_name is None:
            for k, v in list(_cache.items()):
                # keep data, mark stale
                _cache[k] = (0.0, v[1])
        else:
            entry = _cache.get(tab_name)
            if entry:
                _cache[tab_name] = (0.0, entry[1])
            # if no entry, nothing to invalidate


def _cache_set_row(tab_name, row_num, row_dict):
    """In-memory update: replace a row by _row_num in the cached list."""
    with _cache_lock:
        entry = _cache.get(tab_name)
        if not entry:
            return
        rows = entry[1]
        for i, r in enumerate(rows):
            if r.get("_row_num") == row_num:
                rows[i] = {**row_dict, "_row_num": row_num}
                _cache[tab_name] = (time.time(), rows)
                return


def _cache_append_row(tab_name, row_dict):
    """In-memory update: append a row to the cached list (best-effort _row_num)."""
    with _cache_lock:
        entry = _cache.get(tab_name)
        if not entry:
            return
        rows = entry[1]
        max_rn = max((r.get("_row_num", 1) for r in rows), default=1)
        row_dict = {**row_dict, "_row_num": max_rn + 1}
        rows.append(row_dict)
        _cache[tab_name] = (time.time(), rows)


def _cache_remove_row(tab_name, row_num):
    """In-memory update: remove a row by _row_num from the cached list."""
    with _cache_lock:
        entry = _cache.get(tab_name)
        if not entry:
            return
        rows = [r for r in entry[1] if r.get("_row_num") != row_num]
        _cache[tab_name] = (time.time(), rows)


def _read_tab(tab_name, use_cache=True):
    """
    Read a tab as list of dicts.
    Each dict also carries _row_num (1-based, including header -> data starts at 2).
    `use_cache` controls only whether a cached entry may short-circuit the read;
    a fresh read ALWAYS refreshes the cache so callers benefit on the next hit.
    """
    now = time.time()
    if use_cache:
        with _cache_lock:
            entry = _cache.get(tab_name)
            if entry and (now - entry[0]) < _CACHE_TTL:
                return [dict(r) for r in entry[1]]

    try:
        ws = _spreadsheet().worksheet(tab_name)
        all_values = ws.get_all_values()
    except Exception as e:
        print(f"[system_db] _read_tab('{tab_name}') error: {e}")
        # If we have a stale cache entry, fall back to it rather than failing hard
        with _cache_lock:
            entry = _cache.get(tab_name)
            if entry:
                return [dict(r) for r in entry[1]]
        return []

    if not all_values or len(all_values) < 2:
        rows = []
    else:
        header = [str(h).strip() for h in all_values[0]]
        rows = []
        for idx, raw in enumerate(all_values[1:], start=2):  # row 1 = header
            row = {}
            for ci, col_name in enumerate(header):
                row[col_name] = raw[ci] if ci < len(raw) else ""
            row["_row_num"] = idx
            # Skip empty rows
            if any(str(v).strip() for k, v in row.items() if k != "_row_num"):
                rows.append(row)

    # Always refresh the cache after a successful fresh read
    with _cache_lock:
        _cache[tab_name] = (now, [dict(r) for r in rows])

    return rows


def _batch_read_tabs(tab_names, use_cache=True):
    """Read multiple tabs in one logical batch (parallel-ish)."""
    out = {}
    threads = []
    results = {}

    def worker(name):
        results[name] = _read_tab(name, use_cache=use_cache)

    for n in tab_names:
        t = threading.Thread(target=worker, args=(n,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=20)
    for n in tab_names:
        out[n] = results.get(n, [])
    return out


def _prewarm_cache():
    """Pre-warm cache for all System_* tabs."""
    tabs = [
        "System_Users",
        "System_Products",
        "System_Transactions",
        "System_TransactionItems",
        "System_Services",
        "System_ServiceTransactions",
        "System_EmployeeProducts",
        "System_EmployeeServices",
    ]
    print("[system_db] Pre-warming cache for", len(tabs), "tabs...")
    _batch_read_tabs(tabs, use_cache=False)
    print("[system_db] Cache warmed ✅")


# ---------------------------------------------------------
# Low-level write helpers
# ---------------------------------------------------------
def _append_row(tab_name, row_values):
    """Append a row to a tab and update the in-memory cache (rather than just
    invalidating it) so that an immediate subsequent read sees the new row
    even if a fresh Google Sheets read is rate-limited."""
    try:
        ws = _spreadsheet().worksheet(tab_name)
        ws.append_row(row_values, value_input_option="USER_ENTERED")
        # Re-read header so we can attach proper keys in cache
        try:
            header = ws.row_values(1)
        except Exception:
            header = []
        row_dict = {}
        for i, val in enumerate(row_values):
            key = header[i] if i < len(header) and header[i] else f"col_{i}"
            row_dict[key] = val
        _cache_append_row(tab_name, row_dict)
        _invalidate(tab_name)  # mark stale but keep data; next read will refresh
        return True
    except Exception as e:
        print(f"[system_db] _append_row('{tab_name}') error: {e}")
        return False


def _update_cell(tab_name, row, col, value):
    """Update a single cell (1-based row, 1-based col)."""
    try:
        ws = _spreadsheet().worksheet(tab_name)
        ws.update_cell(row, col, value)
        _invalidate(tab_name)
        return True
    except Exception as e:
        print(f"[system_db] _update_cell('{tab_name}',{row},{col}) error: {e}")
        return False


def _update_row(tab_name, row_num, values):
    """Update a whole row (1-based) starting at column A and refresh cache."""
    try:
        ws = _spreadsheet().worksheet(tab_name)
        # values is a list aligned with header order
        ws.update(f"A{row_num}", [values], value_input_option="USER_ENTERED")
        # Refresh in-memory cache for this row
        try:
            header = ws.row_values(1)
        except Exception:
            header = []
        row_dict = {}
        for i, val in enumerate(values):
            key = header[i] if i < len(header) and header[i] else f"col_{i}"
            row_dict[key] = val
        _cache_set_row(tab_name, row_num, row_dict)
        _invalidate(tab_name)
        return True
    except Exception as e:
        print(f"[system_db] _update_row('{tab_name}',{row_num}) error: {e}")
        return False


def _delete_row(tab_name, row_num):
    """Delete a row by its 1-based index and update the cache."""
    try:
        ws = _spreadsheet().worksheet(tab_name)
        ws.delete_rows(row_num)
        _cache_remove_row(tab_name, row_num)
        _invalidate(tab_name)
        return True
    except Exception as e:
        print(f"[system_db] _delete_row('{tab_name}',{row_num}) error: {e}")
        return False


# ---------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------
def _new_id(prefix=""):
    return f"{prefix}{uuid.uuid4().hex[:10]}"


def _now_iso():
    return datetime.now().isoformat(timespec="seconds")


def _to_float(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        s = str(v).replace(",", "").replace("RWF", "").strip()
        return float(s)
    except Exception:
        return default


def _to_int(v, default=0):
    try:
        if v is None or v == "":
            return default
        s = str(v).replace(",", "").strip()
        return int(float(s))
    except Exception:
        return default


# =========================================================
# USER CRUD
# =========================================================
USERS_TAB = "System_Users"


def list_users(active_only=False):
    rows = _read_tab(USERS_TAB)
    out = []
    for r in rows:
        u = {
            "id": r.get("id", ""),
            "username": r.get("username", ""),
            "password": r.get("password", ""),  # plain-text demo (matches setup seeds)
            "name": r.get("name", ""),
            "role": (r.get("role", "") or "EMPLOYEE").upper(),
            "phone": r.get("phone", ""),
            "email": r.get("email", ""),
            "active": str(r.get("active", "TRUE")).upper() in ("TRUE", "1", "YES"),
            "created_at": r.get("created_at", ""),
            "_row_num": r.get("_row_num"),
        }
        if active_only and not u["active"]:
            continue
        out.append(u)
    return out


def find_user_by_credentials(username, password):
    for u in list_users(active_only=True):
        if u["username"].lower() == username.lower() and u["password"] == password:
            return u
    return None


def find_user_by_id(user_id):
    for u in list_users():
        if u["id"] == user_id:
            return u
    return None


def insert_user(data):
    uid = data.get("id") or _new_id("U")
    row = [
        uid,
        data.get("username", ""),
        data.get("password", ""),
        data.get("name", ""),
        (data.get("role", "EMPLOYEE") or "EMPLOYEE").upper(),
        data.get("phone", ""),
        data.get("email", ""),
        str(data.get("active", True)).upper(),
        _now_iso(),
    ]
    if _append_row(USERS_TAB, row):
        return {"id": uid, **data}
    return None


def update_user(user_id, updates):
    """
    Update user fields. Uses _row_num fallback if id lookup doesn't match.
    """
    users = list_users()
    target = None
    for u in users:
        if u["id"] == user_id:
            target = u
            break
    if not target:
        # fallback: match by username
        for u in users:
            if u["username"] == updates.get("username"):
                target = u
                break
    if not target:
        return False

    # Build merged row aligned with header
    header = ["id", "username", "password", "name", "role", "phone", "email", "active", "created_at"]
    merged = {**target, **{k: v for k, v in updates.items() if k in header}}
    row_values = [
        merged.get("id", ""),
        merged.get("username", ""),
        merged.get("password", ""),
        merged.get("name", ""),
        (merged.get("role") or "EMPLOYEE").upper(),
        merged.get("phone", ""),
        merged.get("email", ""),
        str(merged.get("active", True)).upper() if isinstance(merged.get("active"), bool) else str(merged.get("active", "TRUE")).upper(),
        merged.get("created_at", _now_iso()),
    ]
    return _update_row(USERS_TAB, target["_row_num"], row_values)


# =========================================================
# PRODUCT CRUD
# =========================================================
PRODUCTS_TAB = "System_Products"



def delete_user_hard(user_id):
    """HARD delete: permanently remove user row from Google Sheets."""
    # Find the user and their row number
    rows = _read_tab("System_Users", use_cache=False)
    row_num = None
    for r in rows:
        if r.get("id") == user_id:
            row_num = r.get("_row_num")
            break
    if not row_num:
        return False
    # Delete the row using gspread (same as delete_product)
    ok = _delete_row("System_Users", row_num)
    # Also remove their assignments
    try:
        _delete_employee_assignments(user_id, "products")
    except: pass
    try:
        _delete_employee_assignments(user_id, "services")
    except: pass
    return ok

def list_products(include_hidden=False):
    rows = _read_tab(PRODUCTS_TAB)
    out = []
    for r in rows:
        p = {
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "sku": r.get("sku", ""),
            "category": r.get("category", ""),
            "quantity": _to_int(r.get("quantity", 0)),
            "unit_price": _to_float(r.get("unit_price", 0)),
            "cost_price": _to_float(r.get("cost_price", 0)),
            "hidden": str(r.get("hidden", "FALSE")).upper() in ("TRUE", "1", "YES"),
            "created_at": r.get("created_at", ""),
            "updated_at": r.get("updated_at", ""),
            "_row_num": r.get("_row_num"),
        }
        if p["hidden"] and not include_hidden:
            continue
        out.append(p)
    return out


def find_product(product_id):
    for p in list_products(include_hidden=True):
        if p["id"] == product_id:
            return p
    return None


def insert_product(data):
    pid = data.get("id") or _new_id("P")
    row = [
        pid,
        data.get("name", ""),
        data.get("sku", ""),
        data.get("category", ""),
        str(_to_int(data.get("quantity", 0))),
        str(_to_float(data.get("unit_price", 0))),
        str(_to_float(data.get("cost_price", 0))),
        str(data.get("hidden", False)).upper(),
        _now_iso(),
        _now_iso(),
    ]
    if _append_row(PRODUCTS_TAB, row):
        return {"id": pid, **data}
    return None


def update_product(product_id, updates):
    products = list_products(include_hidden=True)
    target = next((p for p in products if p["id"] == product_id), None)
    if not target:
        # fallback by _row_num passed in updates
        rn = updates.get("_row_num")
        if rn:
            target = {"_row_num": int(rn)}
        else:
            return False
    header = ["id", "name", "sku", "category", "quantity", "unit_price", "cost_price", "hidden", "created_at", "updated_at"]
    merged = {**target, **{k: v for k, v in updates.items() if k in header}}
    rn = target.get("_row_num") or updates.get("_row_num")
    row_values = [
        merged.get("id", product_id),
        merged.get("name", ""),
        merged.get("sku", ""),
        merged.get("category", ""),
        str(_to_int(merged.get("quantity", 0))),
        str(_to_float(merged.get("unit_price", 0))),
        str(_to_float(merged.get("cost_price", 0))),
        str(merged.get("hidden", False)).upper() if isinstance(merged.get("hidden"), bool) else str(merged.get("hidden", "FALSE")).upper(),
        merged.get("created_at", _now_iso()),
        _now_iso(),
    ]
    return _update_row(PRODUCTS_TAB, rn, row_values)


def delete_product(product_id):
    products = list_products(include_hidden=True)
    target = next((p for p in products if p["id"] == product_id), None)
    if not target:
        return False
    ok = _delete_row(PRODUCTS_TAB, target["_row_num"])
    if ok:
        _invalidate(PRODUCTS_TAB)
    return ok


# =========================================================
# TRANSACTION CRUD
# =========================================================
TX_TAB = "System_Transactions"
TX_ITEMS_TAB = "System_TransactionItems"


def list_transactions(limit=500):
    rows = _read_tab(TX_TAB)
    out = []
    for r in rows[-limit:] if limit else rows:
        out.append({
            "id": r.get("id", ""),
            "type": r.get("type", "SALE"),
            "employee_id": r.get("employee_id", ""),
            "employee_name": r.get("employee_name", ""),
            "total_amount": _to_float(r.get("total_amount", 0)),
            "total_cost": _to_float(r.get("total_cost", 0)),
            "profit": _to_float(r.get("profit", 0)),
            "items_count": _to_int(r.get("items_count", 0)),
            "notes": r.get("notes", ""),
            "created_at": r.get("created_at", ""),
            "_row_num": r.get("_row_num"),
        })
    return out


def list_transactions_in_range(start_iso, end_iso):
    out = []
    for t in list_transactions(limit=0):
        ca = t.get("created_at", "")
        try:
            dt = datetime.fromisoformat(ca)
        except Exception:
            continue
        if start_iso <= dt.isoformat() <= end_iso:
            out.append(t)
    return out


def list_transaction_items(transaction_id=None):
    rows = _read_tab(TX_ITEMS_TAB)
    out = []
    for r in rows:
        if transaction_id and r.get("transaction_id") != transaction_id:
            continue
        out.append({
            "id": r.get("id", ""),
            "transaction_id": r.get("transaction_id", ""),
            "product_id": r.get("product_id", ""),
            "product_name": r.get("product_name", ""),
            "quantity": _to_int(r.get("quantity", 0)),
            "unit_price": _to_float(r.get("unit_price", 0)),
            "cost_price": _to_float(r.get("cost_price", 0)),
            "subtotal": _to_float(r.get("subtotal", 0)),
            "created_at": r.get("created_at", ""),
            "_row_num": r.get("_row_num"),
        })
    return out


def insert_transaction(payload):
    """
    payload = {
      type: SALE | PURCHASE,
      employee_id, employee_name,
      items: [{ product_id, product_name, quantity, unit_price, cost_price }],
      notes
    }

    Stock + price propagation rules:
      SALE:
        - Decreases product.quantity by qty
        - If product.unit_price was 0, set it to the sold unit_price
          (the employee has effectively established the selling price)
        - product.cost_price is NEVER changed on a sale
      PURCHASE:
        - Increases product.quantity by qty
        - Updates product.cost_price to the WEIGHTED AVERAGE cost:
            new_cost = ((old_qty * old_cost) + (qty * purchase_price)) / new_qty
            If old_cost was 0 or old_qty was 0 → just use purchase_price
        - If product.unit_price was 0, set it to purchase_price * 1.5
          (default 50% markup so the Owner dashboard shows a sensible stock value)

    These changes flow through to the Owner dashboard via dashboard_kpis()
    which reads product.unit_price and product.cost_price directly.

    Returns created transaction record.
    """
    items = payload.get("items", []) or []
    if not items:
        return None

    tx_id = payload.get("id") or _new_id("T")
    now = _now_iso()
    ttype = (payload.get("type") or "SALE").upper()

    DEFAULT_MARKUP = 1.5  # 50% markup when unit_price is unknown on PURCHASE

    total_amount = 0.0
    total_cost = 0.0
    products_touched = set()

    for it in items:
        qty = _to_int(it.get("quantity", 0))
        up = _to_float(it.get("unit_price", 0))      # selling price (SALE) OR purchase price (PURCHASE)
        cp = _to_float(it.get("cost_price", 0))      # existing cost from product record
        sub = qty * up
        total_amount += sub
        total_cost += qty * cp
        # write item row
        item_id = _new_id("I")
        _append_row(TX_ITEMS_TAB, [
            item_id, tx_id,
            it.get("product_id", ""), it.get("product_name", ""),
            str(qty), str(up), str(cp), str(sub), now,
        ])
        # update stock + propagate prices to the product record
        prod = find_product(it.get("product_id", ""))
        if prod:
            old_qty = _to_int(prod.get("quantity", 0))
            old_cost = _to_float(prod.get("cost_price", 0))
            old_unit = _to_float(prod.get("unit_price", 0))

            if ttype == "SALE":
                new_qty = max(0, old_qty - qty)
                updates = {"quantity": new_qty}
                # If the product had no unit_price yet, the employee's sale
                # establishes it (so future sales + the Owner dashboard use it).
                if old_unit == 0 and up > 0:
                    updates["unit_price"] = up
            else:  # PURCHASE
                new_qty = old_qty + qty
                # Weighted average cost
                if new_qty > 0 and (old_qty * old_cost) > 0:
                    new_cost = ((old_qty * old_cost) + (qty * up)) / new_qty
                else:
                    new_cost = up  # use the purchase price as the new cost
                updates = {
                    "quantity": new_qty,
                    "cost_price": round(new_cost, 2),
                }
                # If the product had no unit_price, set one with a default markup
                if old_unit == 0 and up > 0:
                    updates["unit_price"] = round(up * DEFAULT_MARKUP, 2)

            update_product(prod["id"], updates)
            products_touched.add(prod["id"])

    # Invalidate products cache so Owner dashboard sees fresh prices immediately
    if products_touched:
        _invalidate(PRODUCTS_TAB)

    profit = total_amount - total_cost
    _append_row(TX_TAB, [
        tx_id, ttype,
        payload.get("employee_id", ""), payload.get("employee_name", ""),
        str(total_amount), str(total_cost), str(profit),
        str(len(items)), payload.get("notes", ""), now,
    ])
    _invalidate(TX_TAB)
    _invalidate(TX_ITEMS_TAB)
    return {
        "id": tx_id, "type": ttype,
        "employee_id": payload.get("employee_id", ""),
        "employee_name": payload.get("employee_name", ""),
        "total_amount": total_amount, "total_cost": total_cost,
        "profit": profit, "items_count": len(items),
        "notes": payload.get("notes", ""), "created_at": now,
    }


# =========================================================
# SERVICE CRUD
# =========================================================
SERVICES_TAB = "System_Services"


def list_services(active_only=False):
    rows = _read_tab(SERVICES_TAB)
    out = []
    for r in rows:
        s = {
            "id": r.get("id", ""),
            "name": r.get("name", ""),
            "description": r.get("description", ""),
            "default_price": _to_float(r.get("default_price", 0)),
            "active": str(r.get("active", "TRUE")).upper() in ("TRUE", "1", "YES"),
            "created_at": r.get("created_at", ""),
            "_row_num": r.get("_row_num"),
        }
        if active_only and not s["active"]:
            continue
        out.append(s)
    return out


def find_service(service_id):
    for s in list_services():
        if s["id"] == service_id:
            return s
    return None


def insert_service(data):
    sid = data.get("id") or _new_id("S")
    row = [
        sid, data.get("name", ""), data.get("description", ""),
        str(_to_float(data.get("default_price", 0))),
        str(data.get("active", True)).upper(),
        _now_iso(),
    ]
    if _append_row(SERVICES_TAB, row):
        return {"id": sid, **data}
    return None


def update_service(service_id, updates):
    services = list_services()
    target = next((s for s in services if s["id"] == service_id), None)
    if not target:
        rn = updates.get("_row_num")
        if rn:
            target = {"_row_num": int(rn)}
        else:
            return False
    header = ["id", "name", "description", "default_price", "active", "created_at"]
    merged = {**target, **{k: v for k, v in updates.items() if k in header}}
    rn = target.get("_row_num") or updates.get("_row_num")
    row_values = [
        merged.get("id", service_id),
        merged.get("name", ""),
        merged.get("description", ""),
        str(_to_float(merged.get("default_price", 0))),
        str(merged.get("active", True)).upper() if isinstance(merged.get("active"), bool) else str(merged.get("active", "TRUE")).upper(),
        merged.get("created_at", _now_iso()),
    ]
    return _update_row(SERVICES_TAB, rn, row_values)


def delete_service(service_id):
    services = list_services()
    target = next((s for s in services if s["id"] == service_id), None)
    if not target:
        return False
    ok = _delete_row(SERVICES_TAB, target["_row_num"])
    if ok:
        _invalidate(SERVICES_TAB)
    return ok


# =========================================================
# SERVICE TRANSACTION CRUD
# =========================================================
SVC_TX_TAB = "System_ServiceTransactions"


def list_service_transactions(limit=500):
    rows = _read_tab(SVC_TX_TAB)
    out = []
    for r in rows[-limit:] if limit else rows:
        out.append({
            "id": r.get("id", ""),
            "service_id": r.get("service_id", ""),
            "service_name": r.get("service_name", ""),
            "employee_id": r.get("employee_id", ""),
            "employee_name": r.get("employee_name", ""),
            "num_clients": _to_int(r.get("num_clients", 0)),
            "price_per_client": _to_float(r.get("price_per_client", 0)),
            "total_amount": _to_float(r.get("total_amount", 0)),
            "notes": r.get("notes", ""),
            "created_at": r.get("created_at", ""),
            "_row_num": r.get("_row_num"),
        })
    return out


def list_service_transactions_in_range(start_iso, end_iso):
    out = []
    for t in list_service_transactions(limit=0):
        ca = t.get("created_at", "")
        try:
            dt = datetime.fromisoformat(ca)
        except Exception:
            continue
        if start_iso <= dt.isoformat() <= end_iso:
            out.append(t)
    return out


def insert_service_transaction(payload):
    service = find_service(payload.get("service_id", ""))
    if not service and not payload.get("service_name"):
        return None
    sid = payload.get("service_id") or (service["id"] if service else "")
    sname = payload.get("service_name") or (service["name"] if service else "")
    num_clients = _to_int(payload.get("num_clients", 0))
    price_per_client = _to_float(payload.get("price_per_client", service["default_price"] if service else 0))
    total = num_clients * price_per_client
    tx_id = _new_id("ST")
    now = _now_iso()
    row = [
        tx_id, sid, sname,
        payload.get("employee_id", ""), payload.get("employee_name", ""),
        str(num_clients), str(price_per_client), str(total),
        payload.get("notes", ""), now,
    ]
    if _append_row(SVC_TX_TAB, row):
        _invalidate(SVC_TX_TAB)
        return {
            "id": tx_id, "service_id": sid, "service_name": sname,
            "employee_id": payload.get("employee_id", ""),
            "employee_name": payload.get("employee_name", ""),
            "num_clients": num_clients, "price_per_client": price_per_client,
            "total_amount": total, "notes": payload.get("notes", ""),
            "created_at": now,
        }
    return None


def service_dashboard_stats():
    txs = list_service_transactions(limit=0)
    total_clients = sum(t["num_clients"] for t in txs)
    total_revenue = sum(t["total_amount"] for t in txs)
    by_service = {}
    for t in txs:
        key = t["service_name"] or "Unknown"
        if key not in by_service:
            by_service[key] = {"name": key, "clients": 0, "revenue": 0.0}
        by_service[key]["clients"] += t["num_clients"]
        by_service[key]["revenue"] += t["total_amount"]
    top = max(by_service.values(), key=lambda x: x["revenue"]) if by_service else None
    least = min(by_service.values(), key=lambda x: x["revenue"]) if by_service else None
    return {
        "total_clients": total_clients,
        "total_revenue": total_revenue,
        "total_transactions": len(txs),
        "by_service": list(by_service.values()),
        "top_service": top,
        "least_service": least,
    }


# =========================================================
# EMPLOYEE ASSIGNMENTS
# =========================================================
EMP_PROD_TAB = "System_EmployeeProducts"
EMP_SVC_TAB = "System_EmployeeServices"


def list_employee_products(employee_id=None):
    rows = _read_tab(EMP_PROD_TAB)
    out = []
    for r in rows:
        if employee_id and r.get("employee_id") != employee_id:
            continue
        out.append({
            "id": r.get("id", ""),
            "employee_id": r.get("employee_id", ""),
            "product_id": r.get("product_id", ""),
            "product_name": r.get("product_name", ""),
            "assigned_at": r.get("assigned_at", ""),
            "_row_num": r.get("_row_num"),
        })
    return out


def list_employee_services(employee_id=None):
    rows = _read_tab(EMP_SVC_TAB)
    out = []
    for r in rows:
        if employee_id and r.get("employee_id") != employee_id:
            continue
        out.append({
            "id": r.get("id", ""),
            "employee_id": r.get("employee_id", ""),
            "service_id": r.get("service_id", ""),
            "service_name": r.get("service_name", ""),
            "assigned_at": r.get("assigned_at", ""),
            "_row_num": r.get("_row_num"),
        })
    return out


def get_employee_assignments(employee_id):
    return {
        "products": list_employee_products(employee_id),
        "services": list_employee_services(employee_id),
    }


def assign_employee_products(employee_id, product_ids):
    """Replace product assignments for an employee."""
    _delete_employee_assignments(employee_id, "products")
    for pid in product_ids:
        prod = find_product(pid)
        if not prod:
            continue
        _append_row(EMP_PROD_TAB, [
            _new_id("EP"), employee_id, pid, prod["name"], _now_iso()
        ])
    _invalidate(EMP_PROD_TAB)
    return True


def assign_employee_services(employee_id, service_ids):
    _delete_employee_assignments(employee_id, "services")
    for sid in service_ids:
        svc = find_service(sid)
        if not svc:
            continue
        _append_row(EMP_SVC_TAB, [
            _new_id("ES"), employee_id, sid, svc["name"], _now_iso()
        ])
    _invalidate(EMP_SVC_TAB)
    return True


def _delete_employee_assignments(employee_id, kind="products"):
    """Delete existing assignments for an employee."""
    tab = EMP_PROD_TAB if kind == "products" else EMP_SVC_TAB
    id_field = "product_id" if kind == "products" else "service_id"
    rows = _read_tab(tab)
    to_delete = [r["_row_num"] for r in rows if r.get("employee_id") == employee_id]
    # Delete from bottom up so row numbers don't shift
    for rn in sorted(to_delete, reverse=True):
        _delete_row(tab, rn)
    _invalidate(tab)
    return len(to_delete)


# =========================================================
# DASHBOARD ANALYTICS
# =========================================================
def dashboard_kpis():
    """Batch-read all relevant tabs in one pass."""
    batch = _batch_read_tabs([PRODUCTS_TAB, TX_TAB, SERVICES_TAB, SVC_TX_TAB, USERS_TAB])
    products = batch.get(PRODUCTS_TAB, [])
    txs = batch.get(TX_TAB, [])
    services = batch.get(SERVICES_TAB, [])
    svc_txs = batch.get(SVC_TX_TAB, [])
    users = batch.get(USERS_TAB, [])

    total_products = len([p for p in products if str(p.get("hidden", "FALSE")).upper() not in ("TRUE", "1", "YES")])
    stock_value = sum(_to_float(p.get("quantity", 0)) * _to_float(p.get("unit_price", 0)) for p in products)
    stock_cost = sum(_to_float(p.get("quantity", 0)) * _to_float(p.get("cost_price", 0)) for p in products)

    today_iso = date.today().isoformat()
    todays_txs = [t for t in txs if str(t.get("created_at", "")).startswith(today_iso)]
    todays_sales = sum(_to_float(t.get("total_amount", 0)) for t in todays_txs if str(t.get("type", "")).upper() == "SALE")
    todays_profit = sum(_to_float(t.get("profit", 0)) for t in todays_txs)

    total_sales = sum(_to_float(t.get("total_amount", 0)) for t in txs if str(t.get("type", "")).upper() == "SALE")
    total_profit = sum(_to_float(t.get("profit", 0)) for t in txs)

    total_svc_clients = sum(_to_int(t.get("num_clients", 0)) for t in svc_txs)
    total_svc_revenue = sum(_to_float(t.get("total_amount", 0)) for t in svc_txs)

    active_employees = len([u for u in users if str(u.get("role", "")).upper() == "EMPLOYEE" and str(u.get("active", "TRUE")).upper() in ("TRUE", "1", "YES")])

    return {
        "total_products": total_products,
        "stock_value": stock_value,
        "stock_cost": stock_cost,
        "potential_profit": stock_value - stock_cost,
        "todays_sales": todays_sales,
        "todays_profit": todays_profit,
        "todays_transactions": len(todays_txs),
        "total_sales": total_sales,
        "total_profit": total_profit,
        "total_transactions": len(txs),
        "total_services": len(services),
        "total_svc_clients": total_svc_clients,
        "total_svc_revenue": total_svc_revenue,
        "active_employees": active_employees,
    }


def dashboard_charts():
    """Return data for 4 charts: sales last 7 days, top products, sales by category, profit trend."""
    txs = list_transactions(limit=0)
    items = list_transaction_items()

    # Sales last 7 days
    today = date.today()
    days = [(today - timedelta(days=i)) for i in range(6, -1, -1)]
    sales_by_day = []
    for d in days:
        iso = d.isoformat()
        total = sum(_to_float(t.get("total_amount", 0)) for t in txs if str(t.get("created_at", "")).startswith(iso) and str(t.get("type", "")).upper() == "SALE")
        sales_by_day.append({"date": d.strftime("%a %d"), "value": total})

    # Top products by revenue (from items)
    prod_rev = {}
    for it in items:
        name = it.get("product_name", "Unknown")
        prod_rev[name] = prod_rev.get(name, 0.0) + _to_float(it.get("subtotal", 0))
    top_products = sorted([{"name": k, "value": v} for k, v in prod_rev.items()], key=lambda x: x["value"], reverse=True)[:8]

    # Sales by category
    products = {p["id"]: p for p in list_products()}
    cat_rev = {}
    for it in items:
        prod = products.get(it.get("product_id"))
        cat = prod["category"] if prod else "Uncategorized"
        cat_rev[cat] = cat_rev.get(cat, 0.0) + _to_float(it.get("subtotal", 0))
    by_category = sorted([{"name": k, "value": v} for k, v in cat_rev.items()], key=lambda x: x["value"], reverse=True)

    # Profit trend last 7 days
    profit_by_day = []
    for d in days:
        iso = d.isoformat()
        total = sum(_to_float(t.get("profit", 0)) for t in txs if str(t.get("created_at", "")).startswith(iso))
        profit_by_day.append({"date": d.strftime("%a %d"), "value": total})

    return {
        "sales_last_7_days": sales_by_day,
        "top_products": top_products,
        "sales_by_category": by_category,
        "profit_trend": profit_by_day,
    }


# =========================================================
# SYSTEM RESET — wipe all business data, keep owner account
# =========================================================
RESET_TABS = [
    "System_Users",
    "System_Products",
    "System_Transactions",
    "System_TransactionItems",
    "System_Services",
    "System_ServiceTransactions",
    "System_EmployeeProducts",
    "System_EmployeeServices",
]


def _clear_tab_data(tab_name, keep_predicate=None):
    """
    Delete every data row (row >= 2) in `tab_name`, keeping the header row.
    If `keep_predicate(row_dict)` returns True for a row, that row is preserved.
    Returns the number of rows deleted.
    """
    try:
        ws = _spreadsheet().worksheet(tab_name)
        all_values = ws.get_all_values()
    except Exception as e:
        print(f"[system_db] _clear_tab_data('{tab_name}') read error: {e}")
        return 0

    if not all_values or len(all_values) < 2:
        # No data rows
        _invalidate(tab_name)
        return 0

    header = [str(h).strip() for h in all_values[0]]
    total_data_rows = len(all_values) - 1

    # If no predicate, the fast path: just delete all data rows in one shot
    if keep_predicate is None:
        try:
            ws.delete_rows(2, total_data_rows + 1)  # inclusive end
        except Exception as e:
            print(f"[system_db] _clear_tab_data('{tab_name}') bulk delete error: {e}")
            # Fallback: delete one by one in reverse
            for rn in range(total_data_rows + 1, 1, -1):
                try: ws.delete_rows(rn)
                except: pass
        _invalidate(tab_name)
        return total_data_rows

    # With predicate: build list of rows to keep, then rewrite the sheet
    kept_rows = []
    deleted_count = 0
    for idx, raw in enumerate(all_values[1:], start=2):
        row_dict = {}
        for ci, col_name in enumerate(header):
            row_dict[col_name] = raw[ci] if ci < len(raw) else ""
        row_dict["_row_num"] = idx
        if keep_predicate(row_dict):
            # Strip _row_num and pad to header length
            kept_rows.append([row_dict.get(h, "") for h in header])
        else:
            deleted_count += 1

    try:
        # Clear entire sheet then rewrite header + kept rows
        ws.clear()
        if kept_rows:
            ws.append_rows(
                [header] + kept_rows,
                value_input_option="USER_ENTERED",
            )
        else:
            # Just rewrite header
            ws.update("A1", [header], value_input_option="USER_ENTERED")
    except Exception as e:
        print(f"[system_db] _clear_tab_data('{tab_name}') rewrite error: {e}")
        # Best-effort: at least invalidate cache
    _invalidate(tab_name)
    return deleted_count


# ---------------------------------------------------------
# Granular reset — target keys → tabs they wipe
# ---------------------------------------------------------
RESET_TARGETS = {
    # Each key maps to a list of System_* tabs that should be fully wiped.
    "products":              ["System_Products"],
    "transactions":          ["System_Transactions", "System_TransactionItems"],
    "services":              ["System_Services"],
    "service_transactions":  ["System_ServiceTransactions"],
    "employee_assignments":  ["System_EmployeeProducts", "System_EmployeeServices"],
    # 'employees' is special — handled below with keep_owner_id
}

RESET_OPTIONAL_TARGETS = ("employees", "reports", "sessions", "approvers_mapping")


def reset_all_system(keep_owner_id=None, targets=None):
    """
    Reset the system GRANULARLY. Pass `targets` as a list of strings from:
      - "products"             → wipe System_Products
      - "transactions"         → wipe System_Transactions + System_TransactionItems
      - "services"             → wipe System_Services
      - "service_transactions" → wipe System_ServiceTransactions
      - "employee_assignments" → wipe System_EmployeeProducts + System_EmployeeServices
      - "employees"            → wipe System_Users EXCEPT Owner (uses keep_owner_id)
      - "reports"              → ignored here, handled by app.py (deletes PDFs)
      - "sessions"             → ignored here, handled by app.py (clears sessions.json)
      - "approvers_mapping"    → ignored here, handled by app.py (resets employee_approvers.json)
      - "all"                  → wipe every System_* tab (keep Owner)

    If `targets` is None or ["all"], wipes everything (original behaviour).
    `keep_owner_id` is always honoured for the System_Users tab.

    Returns dict: {tab: rows_deleted, ..., "targets": [...], "keep_owner_id": ...}
    """
    summary = {}

    # Normalize targets
    if not targets or targets == ["all"] or "all" in (targets or []):
        targets = list(RESET_TARGETS.keys()) + ["employees"]
        do_all = True
    else:
        do_all = False

    summary["targets"] = targets

    # 1. Pure-wipe tabs based on target selection
    tabs_to_wipe = set()
    for t in targets:
        for tab in RESET_TARGETS.get(t, []):
            tabs_to_wipe.add(tab)

    # If "employees" is in targets, also wipe their assignments automatically
    if "employees" in targets:
        tabs_to_wipe.update(RESET_TARGETS["employee_assignments"])
        targets = [t for t in targets if t != "employee_assignments"]

    for tab in sorted(tabs_to_wipe):
        n = _clear_tab_data(tab, keep_predicate=None)
        summary[tab] = n

    # 2. System_Users — wipe non-Owner only if "employees" was requested
    if "employees" in targets or do_all:
        def _keep_owner(row_dict):
            uid = (row_dict.get("id") or "").strip()
            role = (row_dict.get("role") or "").upper()
            if keep_owner_id and uid == keep_owner_id:
                return True
            if keep_owner_id and role == "OWNER":
                return True
            return False

        summary["System_Users"] = _clear_tab_data(
            "System_Users",
            keep_predicate=_keep_owner if keep_owner_id else None,
        )

    summary["keep_owner_id"] = keep_owner_id

    # 3. Force a fresh re-read so subsequent reads don't serve stale cache
    try:
        _prewarm_cache()
    except Exception:
        pass

    return summary


# ---------------------------------------------------------
# Module self-test (run directly)
# ---------------------------------------------------------
if __name__ == "__main__":
    _prewarm_cache()
    print("Users:", len(list_users()))
    print("Products:", len(list_products()))
    print("Services:", len(list_services()))
    print("Transactions:", len(list_transactions()))
    print("Service TXs:", len(list_service_transactions()))
    print("KPIs:", dashboard_kpis())
