import database

try:
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    print("=== DATABASES ===")
    cursor.execute("SELECT name FROM sys.databases")
    for row in cursor.fetchall():
        print(row[0])
        
    print("\n=== SCHEMAS ===")
    cursor.execute("SELECT schema_name FROM information_schema.schemata")
    for row in cursor.fetchall():
        print(row[0])

    print("\n=== TABLES WITH DROGUERIA OR CREDENTIALS IN NAME ===")
    cursor.execute("""
        SELECT table_schema, table_name 
        FROM information_schema.tables 
        WHERE table_name LIKE '%drogueria%' OR table_name LIKE '%cred%' OR table_schema LIKE '%drogueria%'
    """)
    for row in cursor.fetchall():
        print(f"{row[0]}.{row[1]}")
        
    conn.close()
except Exception as e:
    print("Error:", e)
