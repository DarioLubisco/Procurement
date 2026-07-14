import sys
sys.path.append(r'c:\source\Synapse\backend')
import database

def main():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    delete_query = """
    WITH CTE AS (
        SELECT id,
               ROW_NUMBER() OVER (
                   PARTITION BY cierre_id, tipo, referencia, monto, punto_de_venta 
                   ORDER BY id
               ) as fila_num
        FROM Custom.CajaCierreTarjeta
        WHERE cierre_id IN (
            SELECT id FROM Custom.CajaCierre WHERE fecha_ini IN ('2026-04-23', '2026-04-24')
        )
    )
    DELETE FROM CTE WHERE fila_num > 1;
    """
    
    try:
        cursor.execute(delete_query)
        deleted_count = cursor.rowcount
        conn.commit()
        print(f"Éxito: Se eliminaron {deleted_count} registros duplicados de CajaCierreTarjeta.")
    except Exception as e:
        print(f"Error al eliminar: {e}")
        conn.rollback()

if __name__ == '__main__':
    main()
