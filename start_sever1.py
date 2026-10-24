import subprocess
import sys
import time
import os

# ==========================================
APP_FILE = "app.py"
PORT = 5000
# ==========================================

def kill_port(port):
    """Ifunga server ya kera kuri iyi port"""
    try:
        command = f"netstat -ano | findstr :{port}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.stdout:
            lines = result.stdout.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}"):
                    pid = parts[-1]
                    if pid != "0":
                        subprocess.run(f"taskkill /PID {pid} /F", shell=True, capture_output=True)
                        print(f"🔴 Yafunze server ya kera kuri Port {port}.")
    except Exception:
        pass

def main():
    print("🔄 Turasuzuma sisitemu...")
    
    # 1. Kuraho server ya kera kuri port 5000
    kill_port(PORT)
    time.sleep(1)

    # 2. Reba niba app.py ihari
    if not os.path.exists(APP_FILE):
        print(f"❌ Ntabwo nabonye fayilo {APP_FILE} muri iyi folder!")
        return

    print(f"🚀 Turatangiza {APP_FILE}...")
    
    # 3. Fungura cmd nshya itangiza app.py
    try:
        # Iyi command ifungura cmd nshya, ihindura umutwe wayo, hanyuma ikatanga app.py
        cmd_command = f'start "SMART REPORTING SERVER" cmd /k ""{sys.executable}" -u "{APP_FILE}""'
        
        subprocess.Popen(cmd_command, shell=True)
        print("✅ Command Prompt nshya yafungutse kandi irimo gutangiza app.py...")
        print("ℹ️ Ntacyo kindi iyi script izakora. Fungura browser yawe ukandike: http://127.0.0.1:5000")
        
    except Exception as e:
        print(f"❌ Habaye ikibazo mu gutangiza app.py: {e}")

if __name__ == "__main__":
    main()