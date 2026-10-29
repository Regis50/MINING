# generate_all_reports.py
import time
import os

def run_all_reports():
    print("==================================================")
    print("🚀 TURATANGIRA GUKORA RAPORO ZOSE ICYARIMWE")
    print("==================================================")
    
    start_time = time.time()

    # 1. DAILY REPORT
    print("\n▶️ [1/4] Turi gukora DAILY REPORT...")
    try:
        from daily_report import create_daily_report
        create_daily_report()
        print("✅ Daily Report yarangiye.")
    except Exception as e:
        print(f"❌ Habaye ikibazo muri Daily Report: {e}")

    # 2. WEEKLY REPORT
    print("\n▶️ [2/4] Turi gukora WEEKLY REPORT...")
    try:
        from weekly_report import create_weekly_report
        create_weekly_report()
        print("✅ Weekly Report yarangiye.")
    except Exception as e:
        print(f"❌ Habaye ikibazo muri Weekly Report: {e}")

    # 3. MONTHLY REPORT
    print("\n▶️ [3/4] Turi gukora MONTHLY REPORT...")
    try:
        from monthly_report import create_monthly_report
        create_monthly_report()
        print("✅ Monthly Report yarangiye.")
    except Exception as e:
        print(f"❌ Habaye ikibazo muri Monthly Report: {e}")

    # 4. YEARLY REPORT
    print("\n▶️ [4/4] Turi gukora YEARLY REPORT...")
    try:
        from yearly_report import create_yearly_report
        create_yearly_report()
        print("✅ Yearly Report yarangiye.")
    except Exception as e:
        print(f"❌ Habaye ikibazo muri Yearly Report: {e}")

    # ==========================================
    # IGIHE BYATWAYE
    # ==========================================
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n==================================================")
    print(f"🎉 RAPORO ZOSE ZARANGIYE NEZA! Byatwaye {duration:.2f} seconds.")
    print(f"📂 Reba muri folder '{os.path.abspath('reports')}' ushake ama PDF yose.")
    print("==================================================")

if __name__ == "__main__":
    run_all_reports()
