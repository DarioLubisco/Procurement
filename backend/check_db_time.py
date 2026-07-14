import database
try:
    conn = database.get_db_connection()
    c = conn.cursor()
    c.execute("SELECT TOP 5 id, fecha FROM Custom.CajaTransaccionesDolares ORDER BY id DESC")
    print("Latest transactions:")
    for row in c.fetchall():
        print(f"ID: {row[0]}, Fecha: {row[1]}, iso: {row[1].isoformat() if hasattr(row[1], 'isoformat') else ''}")
except Exception as e:
    print("Error:", e)
