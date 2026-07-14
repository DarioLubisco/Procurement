import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()
DB_SERVER = os.getenv("DB_SERVER", "amc.sql\\efficacis3")
DB_DATABASE = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
DB_USERNAME = os.getenv("DB_USERNAME", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Twinc3pt.")

available = pyodbc.drivers()
driver_name = "ODBC Driver 18 for SQL Server"
if driver_name not in available:
    driver_name = "SQL Server"

conn_str = (
    f"DRIVER={{{driver_name}}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_DATABASE};"
    f"UID={DB_USERNAME};"
    f"PWD={DB_PASSWORD};"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Query summary per seller today
print("=== VENTAS DE HOY POR VENDEDOR ===")
cursor.execute("""
    SELECT CodVend, TipoFac, SUM(CancelT) as cancel_t, SUM(CancelE) as cancel_e, SUM(Monto) as monto 
    FROM SAFACT 
    WHERE CAST(FechaE AS DATE) = CAST(GETDATE() AS DATE) 
    GROUP BY CodVend, TipoFac
""")
for row in cursor.fetchall():
    print(row)

# Get Arianny's info if there's a specific name
print("\n=== DETALLES DE VENDEDOR ARIANNY ===")
cursor.execute("""
    SELECT v.CodVend, v.Descrip, f.TipoFac, COUNT(*), SUM(f.CancelT), SUM(f.CancelE)
    FROM SAVEND v
    LEFT JOIN SAFACT f ON v.CodVend = f.CodVend AND CAST(f.FechaE AS DATE) = CAST(GETDATE() AS DATE)
    WHERE v.Descrip LIKE '%ARIANNY%' OR v.Descrip LIKE '%ARY%'
    GROUP BY v.CodVend, v.Descrip, f.TipoFac
""")
for row in cursor.fetchall():
    print(row)
