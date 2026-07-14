import os
import sys
from dotenv import load_dotenv

load_dotenv("/home/synapse/source/Pedidos/.env", override=True)
sys.path.append("/home/synapse/source/Pedidos")

from analytics_engine.core.db import db_cursor

def populate_prices():
    try:
        with db_cursor() as cursor:
            # Check if Prices table is empty
            cursor.execute("SELECT COUNT(*) FROM Procurement.Prices")
            count = cursor.fetchone()[0]
            
            if count > 0:
                print(f"La tabla Procurement.Prices ya tiene {count} registros. Limpiando para recargar...")
                cursor.execute("TRUNCATE TABLE Procurement.Prices")
            
            # Poblar desde SAITEMCOM y SACOMP calculando el precio en USD (Costo / Factor)
            # Solo desde 2024 en adelante para evitar distorsiones por devaluación / reconversión
            print("Poblando historicos de costos en USD desde SAITEMCOM/SACOMP (solo >= 2024)...")
            
            sql_insert = """
            INSERT INTO Procurement.Prices (proveedor, codbarras, precio_usd, fecha, fuente)
            SELECT 
                c.CodProv, 
                i.CodItem, 
                i.Costo / NULLIF(c.Factor, 0), 
                c.FechaT, 
                'SACOMP'
            FROM SAITEMCOM i
            JOIN SACOMP c ON i.NumeroD = c.NumeroD AND i.TipoCom = c.TipoCom
            WHERE c.Factor > 0 AND i.Costo > 0 AND c.FechaT >= '2024-01-01'
            """
            cursor.execute(sql_insert)
            
            cursor.execute("SELECT COUNT(*) FROM Procurement.Prices")
            new_count = cursor.fetchone()[0]
            print(f"Se han cargado {new_count} historicos de precios (>= 2024) en Procurement.Prices")
            
    except Exception as e:
        print(f"Error poblando Procurement.Prices: {e}")

if __name__ == "__main__":
    populate_prices()
