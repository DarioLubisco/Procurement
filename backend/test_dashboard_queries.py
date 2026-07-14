import sys
import pyodbc
from database import get_db_connection

def test_queries():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    fecha_desde = "2024-01-01"
    fecha_hasta = "2025-12-31" # Use a wide range just to see if data exists
    
    try:
        print("\n=== Ventas por Categoria ===")
        cursor.execute("""
            SELECT TOP 10
                inst.Descrip as category,
                SUM(CASE WHEN f.TipoFac='C' THEN -i.TotalItem ELSE i.TotalItem END) as amount
            FROM dbo.SAITEMFAC i
            JOIN dbo.SAFACT f ON i.NumeroD = f.NumeroD AND i.TipoFac = f.TipoFac
            JOIN dbo.SAPROD p ON i.CodItem = p.CodProd
            JOIN dbo.SAINSTA inst ON p.CodInst = inst.CodInst
            WHERE CAST(f.FechaE AS DATE) BETWEEN ? AND ?
              AND f.TipoFac IN ('A', 'C')
            GROUP BY inst.Descrip
            ORDER BY amount DESC
        """, (fecha_desde, fecha_hasta))
        for r in cursor.fetchall():
            print(f"Categoria: {r[0].strip() if r[0] else 'N/A'}, Amount: {r[1]}")
            
    except Exception as e:
        print("Error:", e)
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    test_queries()
