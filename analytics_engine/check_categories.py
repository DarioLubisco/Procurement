import os
import sys
import pandas as pd
from dotenv import load_dotenv

load_dotenv("/home/synapse/source/Pedidos/.env", override=True)
sys.path.insert(0, '/home/synapse/source/Pedidos')

try:
    from analytics_engine.core.db import query_dataframe
except ImportError as e:
    print(f"Error importando query_dataframe: {e}")
    sys.exit(1)

def main():
    try:
        # Check available categories
        df = query_dataframe("SELECT DISTINCT clasificacion_insumo_Des FROM Procurement.por_aprobacion_equivalencias")
        print("Categorías disponibles:")
        print(df)
        
        # Count total rows
        df2 = query_dataframe("SELECT COUNT(*) as total FROM Procurement.por_aprobacion_equivalencias")
        print(f"\nTotal rows in por_aprobacion_equivalencias: {df2.iloc[0]['total']}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
