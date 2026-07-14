import pyodbc
import os
from dotenv import load_dotenv

load_dotenv()

available = pyodbc.drivers()
driver_name = 'ODBC Driver 18 for SQL Server'
if driver_name not in available:
    driver_name = 'SQL Server'

default_server = "amc.sql\\efficacis3"
conn_str = (
    f'DRIVER={{{driver_name}}};'
    f'SERVER={os.getenv("DB_SERVER", default_server)};'
    f'DATABASE={os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")};'
    f'UID={os.getenv("DB_USERNAME", "sa")};'
    f'PWD={os.getenv("DB_PASSWORD", "Twinc3pt.")};'
    f'Encrypt=yes;TrustServerCertificate=yes;'
)

try:
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()

    query = """
    UPDATE f
    SET f.Saldo = f.Monto
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
    """
    
    cursor.execute(query)
    affected_rows = cursor.rowcount
    conn.commit()
    
    print(f'EXITO: Se restableció el Saldo = Monto para {affected_rows} facturas.')

except Exception as e:
    print(f"ERROR al ejecutar la corrección: {e}")
finally:
    if 'conn' in locals():
        conn.close()
