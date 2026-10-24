import pandas as pd
import glob
from datetime import datetime
import json
import os

def generate_html_dashboard():
    print("🔄 Turakusanya amakuru ya Dashboard...")
    
    # 1. Reba niba folder ya daily_reports ihari
    if not os.path.exists('daily_reports'):
        print("❌ Nta folder 'daily_reports' ibonetse. Banza ukore Daily Report.")
        return

    list_of_files = glob.glob('daily_reports/daily_*.csv')
    if not list_of_files:
        print("❌ Nta makuru abonetse muri 'daily_reports'. Banza ukore Daily Report.")
        return

    # 2. Soma amadosiye yose
    df_list = []
    for file in list_of_files:
        try:
            df = pd.read_csv(file)
            date_str = file.split('_')[-1].replace('.csv', '')
            df['Date'] = pd.to_datetime(date_str)
            df_list.append(df)
        except Exception as e:
            print(f"⚠️ Habaye ikibazo kuri file {file}: {e}")

    if not df_list:
        print("❌ Nta makuru yasomwe neza.")
        return

    df_all = pd.concat(df_list, ignore_index=True)
    
    # 3. Gutunganya imibare (Kureka ibintu bitari imibare)
    try:
        df_all['TOTAL_NUM'] = df_all.iloc[:, 3].astype(str).str.replace(',', '').str.replace('RWF', '').str.strip().astype(float)
        df_all['QTY_NUM'] = pd.to_numeric(df_all.iloc[:, 1].astype(str).str.replace(r'[^\d.]', '', regex=True), errors='coerce').fillna(0)
    except Exception as e:
        print(f"⚠️ Ikibazo mu guhindura imibare: {e}")
        return
    
    # 4. Gukuraho imirongo itari ibicuruzwa (nka TOTAL, DETAILS, IMBOGA)
    mask = ~df_all.iloc[:, 0].astype(str).str.upper().str.contains('TOTAL|IMBOGA|DETAILS', na=False)
    df_all = df_all[mask].copy()

    # 5. Guhindura itariki mu buryo bwa string (YYYY-MM-DD)
    df_all['DateString'] = df_all['Date'].dt.strftime('%Y-%m-%d')

    # 6. Gutegura amakuru ya JavaScript (JSON)
    records = []
    for index, row in df_all.iterrows():
        records.append({
            "details": str(row.iloc[0]),
            "quantity": float(row['QTY_NUM']),
            "unit_price": str(row.iloc[2]),
            "total": float(row['TOTAL_NUM']),
            "total_str": str(row.iloc[3]),
            "date": row['DateString']
        })

    # Kunanura JSON (ensure_ascii=False kugira ngo inyuguti nka é zidakorwe nabi)
    json_data = json.dumps(records, ensure_ascii=False)

    # 7. Gutegura HTML
    ubu_gihe = datetime.now().strftime('%d/%m/%Y %H:%M')

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>T&J Think Big Mining - Dashboard</title>
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f7f6; margin: 0; padding: 20px; }}
            .header {{ text-align: center; margin-bottom: 20px; }}
            .header h1 {{ color: #333; margin-bottom: 5px; }}
            .filters {{ display: flex; justify-content: center; gap: 10px; margin-bottom: 30px; flex-wrap: wrap; }}
            .filter-btn {{ padding: 10px 20px; border: none; border-radius: 5px; background-color: #e0e0e0; cursor: pointer; font-weight: bold; transition: 0.3s; }}
            .filter-btn:hover {{ background-color: #ccc; }}
            .filter-btn.active {{ background-color: #4F81BD; color: white; }}
            .metrics {{ display: flex; justify-content: space-around; margin-bottom: 30px; flex-wrap: wrap; gap: 15px; }}
            .card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); text-align: center; flex: 1; min-width: 250px; }}
            .card h3 {{ margin: 0; color: #555; font-size: 16px; }}
            .card p {{ font-size: 24px; font-weight: bold; color: #FFC000; margin: 10px 0 0 0; }}
            .charts-container {{ display: flex; flex-wrap: wrap; gap: 20px; }}
            .chart-box {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); flex: 1 1 45%; min-width: 300px; }}
            .chart-box-full {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.1); width: 100%; margin-top: 20px; box-sizing: border-box;}}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: center; }}
            th {{ background-color: #FFC000; color: #333; position: sticky; top: 0; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
        </style>
    </head>
    <body>

        <div class="header">
            <h1>📊 T&J THINK BIG MINING COMPANY LTD</h1>
            <p>Business Performance Dashboard (Yakozwe: {ubu_gihe})</p>
        </div>

        <div class="filters">
            <button class="filter-btn active" onclick="filterData('all', event)">Byose (All Time)</button>
            <button class="filter-btn" onclick="filterData('daily', event)">Uyu Munsi (Daily)</button>
            <button class="filter-btn" onclick="filterData('weekly', event)">Iki Cyumweru (Weekly)</button>
            <button class="filter-btn" onclick="filterData('monthly', event)">Uku Kwezi (Monthly)</button>
            <button class="filter-btn" onclick="filterData('yearly', event)">Uyu Mwaka (Yearly)</button>
        </div>

        <div class="metrics">
            <div class="card">
                <h3>Amafaranga Yinjiye Yose</h3>
                <p id="metric-revenue">0 RWF</p>
            </div>
            <div class="card">
                <h3>Ibicuruzwa Byose Byacurujwe</h3>
                <p id="metric-items">0</p>
            </div>
            <div class="card">
                <h3>Umubare w'Ibicuruzwa Byanditswe</h3>
                <p id="metric-trans">0</p>
            </div>
        </div>

        <div class="charts-container">
            <div class="chart-box">
                <h3>🔥 Top 5 Ibicuruzwa Byinjije Menshi</h3>
                <canvas id="barChart"></canvas>
            </div>
            <div class="chart-box">
                <h3>🥧 Uko Amafaranga Agabanyijemo</h3>
                <canvas id="pieChart"></canvas>
            </div>
            <div class="chart-box-full">
                <h3>📈 Uko Amafaranga Yinjiye Agenda (Trend)</h3>
                <canvas id="lineChart"></canvas>
            </div>
        </div>

        <div class="chart-box-full" style="margin-top: 20px;">
            <h3>📋 Urutonde rw'Ibicuruzwa</h3>
            <div style="max-height: 400px; overflow-y: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>DETAILS</th>
                            <th>QUANTITY</th>
                            <th>UNITY PRICE</th>
                            <th>TOTAL/RWF</th>
                            <th>ITARIKI</th>
                        </tr>
                    </thead>
                    <tbody id="table-body">
                    </tbody>
                </table>
            </div>
        </div>

        <script>
            // Amakuru ava muri Python
            const allData = {json_data};
            
            let barChartInstance = null;
            let pieChartInstance = null;
            let lineChartInstance = null;

            const today = new Date();
            const todayStr = today.toISOString().split('T')[0];

            // Kubara intangiriro y'icyumweru (Kuwa mbere)
            const dayOfWeek = today.getDay();
            const diffToMonday = today.getDate() - dayOfWeek + (dayOfWeek === 0 ? -6 : 1);
            const startOfWeek = new Date(today.setDate(diffToMonday));
            const startOfWeekStr = startOfWeek.toISOString().split('T')[0];

            const startOfMonthStr = todayStr.substring(0, 7) + "-01";
            const startOfYearStr = todayStr.substring(0, 4) + "-01-01";

            function filterData(type, event) {{
                // 1. Guhindura amabara ya Buto
                document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
                if (event) event.target.classList.add('active');

                // 2. Shaka amakuru ajyanye n'igihe cyatoranyijwe
                let filteredData = [];
                if (type === 'all') {{
                    filteredData = allData;
                }} else if (type === 'daily') {{
                    filteredData = allData.filter(d => d.date === todayStr);
                }} else if (type === 'weekly') {{
                    filteredData = allData.filter(d => d.date >= startOfWeekStr && d.date <= todayStr);
                }} else if (type === 'monthly') {{
                    filteredData = allData.filter(d => d.date >= startOfMonthStr && d.date <= todayStr);
                }} else if (type === 'yearly') {{
                    filteredData = allData.filter(d => d.date >= startOfYearStr && d.date <= todayStr);
                }}

                // 3. Kubara imibare
                let totalRevenue = 0;
                let totalQty = 0;
                let totalTrans = filteredData.length;
                
                let groupedByItem = {{}};
                let dailyTrend = {{}};

                filteredData.forEach(item => {{
                    totalRevenue += item.total;
                    totalQty += item.quantity;
                    
                    if (!groupedByItem[item.details]) groupedByItem[item.details] = 0;
                    groupedByItem[item.details] += item.total;

                    if (!dailyTrend[item.date]) dailyTrend[item.date] = 0;
                    dailyTrend[item.date] += item.total;
                }});

                // Kuvugurura imibare
                document.getElementById('metric-revenue').innerText = totalRevenue.toLocaleString() + " RWF";
                document.getElementById('metric-items').innerText = totalQty.toLocaleString();
                document.getElementById('metric-trans').innerText = totalTrans;

                // 4. Gutegura Charts
                let itemsArray = Object.keys(groupedByItem).map(key => {{
                    return {{ name: key, total: groupedByItem[key] }};
                }});
                itemsArray.sort((a, b) => b.total - a.total);

                let top5 = itemsArray.slice(0, 5);
                let top5Labels = top5.map(i => i.name);
                let top5Data = top5.map(i => i.total);

                let pieTop6 = itemsArray.slice(0, 6);
                let pieLabels = pieTop6.map(i => i.name);
                let pieData = pieTop6.map(i => i.total);

                let sortedDates = Object.keys(dailyTrend).sort();
                let lineLabels = sortedDates;
                let lineData = sortedDates.map(d => dailyTrend[d]);

                // 5. Kuvugurura Charts (Kureka izashaje zikavanwaho)
                if (barChartInstance) barChartInstance.destroy();
                if (pieChartInstance) pieChartInstance.destroy();
                if (lineChartInstance) lineChartInstance.destroy();

                barChartInstance = new Chart(document.getElementById('barChart'), {{
                    type: 'bar',
                    data: {{
                        labels: top5Labels,
                        datasets: [{{ label: 'Amafaranga (RWF)', data: top5Data, backgroundColor: '#4F81BD' }}]
                    }}
                }});

                pieChartInstance = new Chart(document.getElementById('pieChart'), {{
                    type: 'doughnut',
                    data: {{
                        labels: pieLabels,
                        datasets: [{{ data: pieData, backgroundColor: ['#FFC000', '#4F81BD', '#A5C63B', '#FF6F61', '#8E44AD', '#34495E'] }}]
                    }}
                }});

                lineChartInstance = new Chart(document.getElementById('lineChart'), {{
                    type: 'line',
                    data: {{
                        labels: lineLabels,
                        datasets: [{{ label: 'Amafaranga yinjiye', data: lineData, borderColor: '#FFC000', backgroundColor: 'rgba(255, 192, 0, 0.2)', fill: true }}]
                    }}
                }});

                // 6. Kuvugurura Table
                let tableHTML = "";
                filteredData.forEach(item => {{
                    tableHTML += `
                        <tr>
                            <td>${{item.details}}</td>
                            <td>${{item.quantity}}</td>
                            <td>${{item.unit_price}}</td>
                            <td>${{item.total_str}}</td>
                            <td>${{item.date}}</td>
                        </tr>
                    `;
                }});
                document.getElementById('table-body').innerHTML = tableHTML;
            }}

            // Gutangiza Dashboard kuri "Byose" (All Data)
            window.onload = function() {{
                filterData('all', null);
            }};
        </script>
    </body>
    </html>
    """

    try:
        with open("dashboard.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        print("✅ Dashboard yakozwe neza muri file 'dashboard.html'!")
        print("💡 Fungura iyi file ukoresheje browser yawe.")
    except Exception as e:
        print(f"❌ Habaye ikibazo mu kubika file: {e}")

if __name__ == "__main__":
    generate_html_dashboard()