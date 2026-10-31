"""
setup_sheets.py
===========================================================
T&J THINK BIG MINING ENTERPRISE OS — Google Sheets seeder.
Creates the System_* tabs (idempotent) and seeds:
  - Owner (owner / owner123)
  - 2 Employees (alice / alice123, eric / eric123)
  - 12 mining products
  - 5 services
Run once before starting app.py:
    python3 setup_sheets.py
===========================================================
"""

import sys
from datetime import datetime

import gspread
from oauth2client.service_account import ServiceAccountCredentials

import sheets_invetory_reader as sr

SHEET_ID = sr.SHEET_ID
CREDENTIALS_FILE = "credentials.json"

_SCOPE = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]


def _client():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, _SCOPE)
    return gspread.authorize(creds)


# ---------------------------------------------------------
# Tab schemas (header rows)
# ---------------------------------------------------------
TAB_SCHEMAS = {
    "System_Users": [
        "id", "username", "password", "name", "role",
        "phone", "email", "active", "created_at",
    ],
    "System_Products": [
        "id", "name", "sku", "category", "quantity",
        "unit_price", "cost_price", "hidden",
        "created_at", "updated_at",
    ],
    "System_Transactions": [
        "id", "type", "employee_id", "employee_name",
        "total_amount", "total_cost", "profit",
        "items_count", "notes", "created_at",
    ],
    "System_TransactionItems": [
        "id", "transaction_id", "product_id", "product_name",
        "quantity", "unit_price", "cost_price", "subtotal",
        "created_at",
    ],
    "System_Services": [
        "id", "name", "description", "default_price",
        "active", "created_at",
    ],
    "System_ServiceTransactions": [
        "id", "service_id", "service_name",
        "employee_id", "employee_name",
        "num_clients", "price_per_client", "total_amount",
        "notes", "created_at",
    ],
    "System_EmployeeProducts": [
        "id", "employee_id", "product_id", "product_name", "assigned_at",
    ],
    "System_EmployeeServices": [
        "id", "employee_id", "service_id", "service_name", "assigned_at",
    ],
}


# ---------------------------------------------------------
# Seed data
# ---------------------------------------------------------
def _now():
    return datetime.now().isoformat(timespec="seconds")


SEED_USERS = [
    # id, username, password, name, role, phone, email, active, created_at
    ["U_OWNER01", "owner", "owner123", "T&J Owner", "OWNER",
     "0782992433", "owner@tjmining.rw", "TRUE", _now()],
    ["U_EMP_ALICE", "alice", "alice123", "Alice Mukamana", "EMPLOYEE",
     "0788123456", "alice@tjmining.rw", "TRUE", _now()],
    ["U_EMP_ERIC", "eric", "eric123", "Eric Twizeyimana", "EMPLOYEE",
     "0788654321", "eric@tjmining.rw", "TRUE", _now()],
]

# 12 mining products (id, name, sku, category, qty, unit_price, cost_price, hidden, created_at, updated_at)
SEED_PRODUCTS = [
    ["P_CASSITE",   "Cassiterite (Tin Ore)",   "MIN-001", "Minerals", 500,  18000, 12000, "FALSE", _now(), _now()],
    ["P_WOLFRAM",   "Wolframite (Tungsten)",   "MIN-002", "Minerals", 320,  22000, 15000, "FALSE", _now(), _now()],
    ["P_COLTAN",    "Coltan (Tantalum)",       "MIN-003", "Minerals", 280,  35000, 24000, "FALSE", _now(), _now()],
    ["P_BERYL",     "Beryl (Beryllium)",       "MIN-004", "Minerals", 150,  15000,  9000, "FALSE", _now(), _now()],
    ["P_GOLD_NUG",  "Gold Nugget (Small)",     "MIN-005", "Minerals",  50, 850000,600000, "FALSE", _now(), _now()],
    ["P_LITHIUM",   "Lithium Ore",             "MIN-006", "Minerals", 420,  12500,  8000, "FALSE", _now(), _now()],
    ["P_GEM_RUBY",  "Ruby Gemstone",           "MIN-007", "Gemstones", 75, 120000, 80000, "FALSE", _now(), _now()],
    ["P_GEM_SAPP",  "Sapphire Gemstone",       "MIN-008", "Gemstones", 60,  95000, 60000, "FALSE", _now(), _now()],
    ["P_QUARTZ",    "Quartz Crystal",          "MIN-009", "Minerals", 900,   2500,  1500, "FALSE", _now(), _now()],
    ["P_FELDSPAR",  "Feldspar",                "MIN-010", "Minerals", 600,   3500,  2000, "FALSE", _now(), _now()],
    ["P_MICA",      "Mica Sheets",             "MIN-011", "Minerals", 250,   4200,  2800, "FALSE", _now(), _now()],
    ["P_TALC",      "Talc (Steatite)",         "MIN-012", "Minerals", 380,   3000,  1800, "FALSE", _now(), _now()],
]

# 5 services (id, name, description, default_price, active, created_at)
SEED_SERVICES = [
    ["S_MINING_CONS", "Mining Consultation",   "Expert advisory on mineral exploration & extraction.",   25000, "TRUE", _now()],
    ["S_GEM_CERT",    "Gemstone Certification","Lab-grade certification of gemstone authenticity & grade.",45000, "TRUE", _now()],
    ["S_ORE_TEST",    "Ore Quality Testing",   "Laboratory assay of ore samples for mineral content.",   18000, "TRUE", _now()],
    ["S_LOGISTICS",   "Mining Logistics",      "Transport & handling of mineral consignments.",          35000, "TRUE", _now()],
    ["S_LEGAL_PERM",  "Legal & Permit Advisory","Help with mining licenses, permits & compliance.",      50000, "TRUE", _now()],
]


def ensure_tabs(ss):
    """Create all System_* tabs with headers if missing. Clear existing data."""
    existing = {w.title for w in ss.worksheets()}
    for tab_name, header in TAB_SCHEMAS.items():
        if tab_name in existing:
            ws = ss.worksheet(tab_name)
            # Only clear rows below header
            try:
                ws.clear()
            except Exception as e:
                print(f"  (clear failed for {tab_name}: {e})")
            ws.update([header], value_input_option="USER_ENTERED")
        else:
            ws = ss.add_worksheet(title=tab_name, rows="1000", cols="20")
            ws.update([header], value_input_option="USER_ENTERED")
        print(f"  ✔ {tab_name} ready")


def seed_rows(ss, tab_name, rows):
    ws = ss.worksheet(tab_name)
    if rows:
        ws.append_rows(rows, value_input_option="USER_ENTERED")
    print(f"  ✔ Seeded {len(rows)} rows into {tab_name}")


def main():
    print("Connecting to Google Sheets...")
    gc = _client()
    ss = gc.open_by_key(SHEET_ID)
    print(f"Spreadsheet: {ss.title}")

    print("\n[1/4] Ensuring System_* tabs...")
    ensure_tabs(ss)

    print("\n[2/4] Seeding users...")
    seed_rows(ss, "System_Users", SEED_USERS)

    print("\n[3/4] Seeding products...")
    seed_rows(ss, "System_Products", SEED_PRODUCTS)

    print("\n[4/4] Seeding services...")
    seed_rows(ss, "System_Services", SEED_SERVICES)

    print("\n✅ Setup complete. You can now run: python3 app.py")
    print("Login as Owner:   owner / owner123")
    print("Login as Alice:   alice / alice123")
    print("Login as Eric:    eric  / eric123")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
