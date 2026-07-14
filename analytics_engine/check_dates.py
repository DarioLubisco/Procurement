import pyodbc
import json

try:
    conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=10.147.18.192,49751;DATABASE=EnterpriseAdmin_AMC;UID=sa;PWD=synapse_ADMIN1.;TrustServerCertificate=yes', timeout=5)
    cursor = conn.cursor()
    
    # Check if there is a timestamp column in Mercado_Vivo_PDR or if we need to check sys tables
    cursor.execute("SELECT proveedor, MAX(GETDATE()) as last_date FROM Analitica.Mercado_Vivo_PDR GROUP BY proveedor")
    # Actually wait, Mercado_Vivo_PDR might have an insertion date column.
    # Let's get columns for Mercado_Vivo_PDR
    cursor.execute("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA='Analitica' AND TABLE_NAME='Mercado_Vivo_PDR'")
    columns = [row[0] for row in cursor.fetchall()]
    
    date_col = next((c for c in columns if 'date' in c.lower() or 'fecha' in c.lower() or 'actualizacion' in c.lower()), None)
    
    res = {}
    if date_col:
        cursor.execute(f"SELECT proveedor, MAX({date_col}) FROM Analitica.Mercado_Vivo_PDR GROUP BY proveedor")
        rows = cursor.fetchall()
        for r in rows:
            res[r[0]] = str(r[1])
            
    # Also let's check sys.dm_db_index_usage_stats for the Inv tables
    cursor.execute("""
    SELECT t.name AS TableName, MAX(s.last_user_update) AS LastUpdate
    FROM sys.dm_db_index_usage_stats s 
    JOIN sys.tables t ON s.object_id = t.object_id 
    WHERE t.name LIKE '%_Inv' 
    GROUP BY t.name
    """)
    rows = cursor.fetchall()
    for r in rows:
        res[r[0]] = str(r[1])

    print(json.dumps(res))
except Exception as e:
    print(json.dumps({"error": str(e)}))
