import pyodbc
from dotenv import load_dotenv
import os

load_dotenv('c:/source/Synapse/backend/.env')

available = pyodbc.drivers()
driver_name = "ODBC Driver 18 for SQL Server"
if driver_name not in available:
    driver_name = "SQL Server"

conn_str = (
    f"DRIVER={{{driver_name}}};"
    f"SERVER={os.getenv('DB_SERVER', 'amc.sql\\\\efficacis3')};"
    f"DATABASE={os.getenv('DB_DATABASE', 'EnterpriseAdmin_AMC')};"
    f"UID={os.getenv('DB_USERNAME', 'sa')};"
    f"PWD={os.getenv('DB_PASSWORD', 'Twinc3pt.')};"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

query = """
SELECT f.NumeroD, f.CodProv, f.FechaE, f.Monto, f.Saldo
FROM dbo.SAACXP f
WHERE f.TipoCxP = '10' 
  AND f.Saldo <= 0.5 
  AND f.Monto > 0
  AND f.FechaE >= DATEADD(month, -2, GETDATE())
  AND NOT EXISTS (
      SELECT 1 
      FROM EnterpriseAdmin_AMC.dbo.CxP_Abonos a 
      WHERE a.CodProv = f.CodProv AND a.NumeroD = f.NumeroD
  )
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.SAPAGCXP p
      WHERE p.NroUnico = f.NroUnico
  )
ORDER BY f.FechaE DESC
"""
cursor.execute(query)
rows = cursor.fetchall()
print(f'Total en últimos 2 meses: {len(rows)}')
for r in rows:
    print(f'{r.NumeroD} | {r.CodProv} | {r.FechaE.strftime("%Y-%m-%d")} | Monto: {r.Monto} | Saldo: {r.Saldo}')

query2 = """
SELECT TOP 10 f.NumeroD, f.CodProv, f.FechaE, f.Monto, f.Saldo
FROM dbo.SAACXP f
WHERE f.TipoCxP = '10' 
  AND f.Saldo <= 0.5 
  AND f.Monto > 0
  AND NOT EXISTS (
      SELECT 1 
      FROM EnterpriseAdmin_AMC.dbo.CxP_Abonos a 
      WHERE a.CodProv = f.CodProv AND a.NumeroD = f.NumeroD
  )
  AND NOT EXISTS (
      SELECT 1
      FROM dbo.SAPAGCXP p
      WHERE p.NroUnico = f.NroUnico
  )
"""
cursor.execute(query2)
for r in cursor.fetchall():
    print(r)
