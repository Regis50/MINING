# app.py
from flask import Flask, send_file, jsonify, render_template
import os
import glob
import traceback
import time
import threading
import json
from datetime import datetime, timedelta

app = Flask(__name__, template_folder='.', static_folder='static')

# ==========================================
# 1. DASHBOARD & LOGIN (HTML)
# ==========================================
@app.route('/')
def index():
    return render_template('jandt.html')

# ==========================================
# 2. API YO GUTANGA ABAKORESHA (KUVA MURI JSON)
# ==========================================
@app.route('/api/users', methods=['GET'])
def get_users():
    try:
        with open('users.json', 'r') as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": "Ntibyakunze gusoma users.json"}), 500

# ==========================================
# 3. API YO GUTANGA DATA (JSON) → Dashboard
# ==========================================
@app.route('/api/data')
def api_data():
    try:
        data = [
            {"details": "Ibishimbo", "quantity": 100, "unit_price": "440",  "date": ""},
            {"details": "Amavuta",   "quantity": 459, "unit_price": "6868", "date": ""},
            {"details": "Kawunga",   "quantity": 692, "unit_price": "1000", "date": ""},
            {"details": "Amata",     "quantity": 560, "unit_price": "850",  "date": ""},
        ]
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": traceback.format_exc()}), 500

# ==========================================
# 4. GUKORA RAPORO (PDF)
# ==========================================
def _latest_pdf(pattern):
    files = glob.glob(pattern)
    if not files:
        return None
    return max(files, key=os.path.getctime)

@app.route('/generate_daily')
def generate_daily():
    try:
        from daily_report2 import create_daily_report # Koresha daily_report2
        create_daily_report()
        latest = _latest_pdf('reports/Daily_Report_*.pdf')
        if not latest:
            return jsonify({"error": "Nta PDF yabonetse."}), 500
        return send_file(latest, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500

@app.route('/generate_weekly')
def generate_weekly():
    try:
        from weekly_report import create_weekly_report
        create_weekly_report()
        latest = _latest_pdf('reports/Weekly_Report_*.pdf')
        if not latest:
            return jsonify({"error": "Nta PDF yabonetse."}), 500
        return send_file(latest, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500

@app.route('/generate_monthly')
def generate_monthly():
    try:
        from monthly_report import create_monthly_report
        create_monthly_report()
        latest = _latest_pdf('reports/Monthly_Report_*.pdf')
        if not latest:
            return jsonify({"error": "Nta PDF yabonetse."}), 500
        return send_file(latest, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500

@app.route('/generate_yearly')
def generate_yearly():
    try:
        from yearly_report import create_yearly_report
        create_yearly_report()
        latest = _latest_pdf('reports/Yearly_Report_*.pdf')
        if not latest:
            return jsonify({"error": "Nta PDF yabonetse."}), 500
        return send_file(latest, as_attachment=True)
    except Exception:
        return jsonify({"error": traceback.format_exc()}), 500

# ==========================================
# 5. BACKGROUND LOOP (AUTO-UPDATE BURI MINETI 5)
# ==========================================
def background_auto_update():
    print("⏳ Auto-Update yatangiye. Raporo zose zizakorwa buri mineti 5.")
    
    while True:
        try:
            now = datetime.now()
            print(f"\n⏰ [{now.strftime('%H:%M:%S')}] Turahamagara Raporo Zose...")
            
            from daily_report2 import create_daily_report
            create_daily_report()
            print("✅ Daily Report yabitswe.")
            
            from weekly_report import create_weekly_report
            create_weekly_report()
            print("✅ Weekly Report yabitswe.")
            
            from monthly_report import create_monthly_report
            create_monthly_report()
            print("✅ Monthly Report yabitswe.")
            
            from yearly_report import create_yearly_report
            create_yearly_report()
            print("✅ Yearly Report yabitswe.")
            
            print("🎉 Raporo zose zagezweho! Zizongera gukorwa mu minota 5.")
            
        except Exception as e:
            print(f"❌ Habaye ikibazo muri Auto-Update: {e}")
            traceback.print_exc()
        
        time.sleep(300) # 5 minutes


if __name__ == '__main__':
    loop_thread = threading.Thread(target=background_auto_update, daemon=True)
    loop_thread.start()
    
    print("🚀 Flask Server: http://127.0.0.1:5000")
    app.run(port=5000, debug=True, use_reloader=False)