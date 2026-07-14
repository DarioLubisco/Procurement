import sys
import pyodbc
from database import get_db_connection

def describe_table(table_name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT TOP 1 * FROM {table_name}")
    columns = [column[0] for column in cursor.description]
    print(f"Columns in {table_name}:")
    for col in columns:
        print(f" - {col}")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    describe_table("dbo.SAITEMFAC")
