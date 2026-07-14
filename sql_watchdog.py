import os
import time
import requests
import subprocess
import json
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "backend/.env"))

DB_SERVER = os.getenv("DB_SERVER", "100.94.5.108\\efficacis3")
DB_DATABASE = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
DB_USERNAME = os.getenv("DB_USERNAME", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Twinc3pt.")

# Bot credentials from synapse_credentials.md
BOT_TOKEN = "8795593743:AAEebBKpsAlITvv72Fb8BaQNbfwPdVjP-3s"
CHAT_ID = "-1003531406167"
QUEUE_FILE = os.path.join(os.path.dirname(__file__), "watchdog_queue.json")

def load_queue():
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading queue: {e}")
    return []

def save_queue(q):
    try:
        with open(QUEUE_FILE, "w") as f:
            json.dump(q, f)
    except Exception as e:
        print(f"Error saving queue: {e}")

def queue_alert(msg):
    q = load_queue()
    q.append({"msg": msg, "timestamp": time.time(), "retries": 0})
    save_queue(q)

def flush_queue():
    q = load_queue()
    if not q:
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    new_q = []
    
    for item in q:
        msg = item["msg"]
        retries = item.get("retries", 0)
        
        # Exponential backoff base (2^retries seconds) max 300s
        backoff = min(300, 2 ** retries)
        if time.time() - item["timestamp"] < backoff and retries > 0:
            new_q.append(item)
            continue
            
        payload = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        
        sent = False
        try:
            requests.post(url, json=payload, timeout=10)
            sent = True
        except requests.exceptions.SSLError as e:
            print(f"SSLError sending to Telegram. Retrying with verify=False. WARNING: MITM risk.")
            try:
                requests.post(url, json=payload, timeout=10, verify=False)
                sent = True
            except Exception as inner_e:
                print(f"Fallback failed: {inner_e}")
        except Exception as e:
            print(f"Failed to send telegram (attempt {retries}): {e}")
            
        if not sent:
            item["retries"] = retries + 1
            item["timestamp"] = time.time()
            new_q.append(item)
            
    save_queue(new_q)

def check_db_connection():
    cmd = [
        "docker",
        "exec",
        "synapse-api",
        "python3",
        "-c",
        "import pyodbc, os; from dotenv import load_dotenv; load_dotenv('/app/.env'); "
        "conn=pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=' + os.getenv('DB_SERVER') + ';DATABASE=' + os.getenv('DB_DATABASE') + ';UID=' + os.getenv('DB_USERNAME') + ';PWD=' + os.getenv('DB_PASSWORD') + ';Encrypt=yes;TrustServerCertificate=yes;LoginTimeout=5;', timeout=5); "
        "cursor=conn.cursor(); cursor.execute('SELECT 1'); cursor.fetchone(); cursor.close(); conn.close()"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return res.returncode == 0
    except Exception as e:
        print(f"Error running check inside container: {e}")
        return False

def main():
    print("Iniciando SQL Watchdog (con soporte de cola local y timeout estricto)...")
    
    was_down = False
    
    while True:
        flush_queue()
        
        success = False
        for attempt in range(3):
            if check_db_connection():
                success = True
                break
            time.sleep(2)
        
        if not success and not was_down:
            msg = f"⚠️ *ALERTA CRÍTICA: Base de Datos* ⚠️\n\nLa conexión a SQL Server (`{DB_SERVER}`) ha fallado tras 3 intentos. El servidor podría estar bloqueado o hay problemas en ZeroTier."
            print(msg)
            queue_alert(msg)
            flush_queue()
            was_down = True
            
        elif success and was_down:
            msg = "✅ *RECUPERACIÓN: Base de Datos* ✅\n\nLa conexión a SQL Server se ha restablecido exitosamente."
            print(msg)
            queue_alert(msg)
            flush_queue()
            was_down = False
            
        time.sleep(60)

if __name__ == "__main__":
    main()
