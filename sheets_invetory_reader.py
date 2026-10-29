"""
sheets_reader.py
Smart Reporting System — Google Sheets reader.
Iyi version ikoresha requests kugira ngo irinde SSL error, kandi yakira ama tabs atandukanye.
"""

import pandas as pd
import requests
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import Request

CREDENTIALS_FILE = "credentials.json"
# Tukuyemo sheet ID nshya y'iyi sisitemu ubona ku ifoto
SHEET_ID = "1fZLm1HjlfFOb7dbFA5xxXcVb03vCjaA__XgVBaf7xCQ"

# SCOPES zawe zikora neza
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
]

_credentials = None
_session = None

def _initialize_google_client():
    global _credentials, _session

    if _session is not None:
        return

    print("🔄 Connecting to Google Sheets...")
    
    _credentials = Credentials.from_service_account_file(
        CREDENTIALS_FILE, scopes=SCOPES
    )
    
    _session = requests.Session()
    _credentials.refresh(Request(session=_session))
    
    print("✅ Connected to Google Sheets API!")

def read_as_table(tab_name: str, header_row: int = 0, data_start_row: int = 1) -> pd.DataFrame:
    """
    Ubu iyi function isaba guhabwa 'tab_name' bitemewe guhora uhindura code rwagati.
    Urugero: read_as_table("Form Responses 1") cyangwa read_as_table("Daily Report", header_row=4, data_start_row=5)
    """
    _initialize_google_client()

    range_name = f"'{tab_name}'"
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET_ID}/values/{range_name}"
    
    headers = {
        "Authorization": f"Bearer {_credentials.token}",
        "Content-Type": "application/json",
    }
    
    try:
        r = _session.get(url, headers=headers, timeout=30)
        r.raise_for_status()
        values = r.json().get("values", [])
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        return pd.DataFrame()

    if not values:
        print(f"⚠️  Nta data muri tab '{tab_name}'")
        return pd.DataFrame()

    width = max(len(row) for row in values)
    
    # ✅ HANO: Dufata umurongo wa header_row (urugero: umurongo wa 5 = index 4)
    raw_header = list(values[header_row]) if header_row < len(values) else []

    header, seen = [], {}
    for i, name in enumerate(raw_header):
        name = str(name).strip() or f"col_{i}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        header.append(name)
    header += [f"col_{i}" for i in range(len(header), width)]

    # ✅ HANO: Dufata amakuru atangira kuri data_start_row (urugero: umurongo wa 6 = index 5)
    data = [list(row) + [""] * (width - len(row)) for row in values[data_start_row:]]
    df = pd.DataFrame(data, columns=header)

    df = df[df.apply(lambda r: any(str(c).strip() for c in r), axis=1)]
    df = df[df.apply(lambda r: sum(str(c).strip() != "" for c in r) > 1, axis=1)]

    non_empty = df.astype(str).apply(lambda c: c.str.strip().ne("").any())
    df = df.loc[:, non_empty]

    return df.reset_index(drop=True)

if __name__ == "__main__":
    # =========================================================
    # UBU WAHAMAGARA TAB IYARIYO YOSE UKORESHEJE IZINA RYAYO:
    # =========================================================
    
    # 1. Gusoma amakuru ya Form Responses
    print("\n--- READING: FORM RESPONSES ---")
    df_form = read_as_table("Form Responses")
    if not df_form.empty:
        print(f"✅ Rows: {len(df_form)} | Columns: {len(df_form.columns)}")
        print(df_form.head(2))

    # 2. Gusoma amakuru ya Copy of ibyagurishijwe (Nk'uko biri muri code yawe nshya)
    print("\n--- READING: COPY OF IBYAGURISHIJWE ---")
    df_daily = read_as_table("Copy of ibyagurishijwe", header_row=4, data_start_row=5)
    if not df_daily.empty:
        print(f"✅ Rows: {len(df_daily)} | Columns: {len(df_daily.columns)}")
        print(df_daily.head(5))
