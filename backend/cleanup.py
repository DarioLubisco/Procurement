import database
conn = database.get_db_connection()
cursor = conn.cursor()

# Get retenciones
cursor.execute("SELECT Id, NumeroD FROM EnterpriseAdmin_AMC.Procurement.Retenciones_IVA WHERE NumeroComprobante = '20260400000429' ORDER BY Id ASC")
rows = cursor.fetchall()
# keep the first two
ids_to_del = [r[0] for r in rows[2:]]
print('Retenciones duplicate IDs to delete:', ids_to_del)

if len(ids_to_del) > 0:
    q1 = f"DELETE FROM EnterpriseAdmin_AMC.Procurement.Retenciones_IVA WHERE Id IN ({','.join(['?' for _ in ids_to_del])})"
    cursor.execute(q1, ids_to_del)
    print('Deleted Retenciones')

# Get abonos
cursor.execute("SELECT AbonoID FROM EnterpriseAdmin_AMC.dbo.CxP_Abonos WHERE Referencia LIKE '%20260400000429%' AND TipoAbono = 'RETENCION_IVA' ORDER BY AbonoID ASC")
abonos = cursor.fetchall()
# keep the first two
abonos_to_del = [a[0] for a in abonos[2:]]
print('Abonos duplicate IDs to delete:', abonos_to_del)

if len(abonos_to_del) > 0:
    q2 = f"DELETE FROM EnterpriseAdmin_AMC.dbo.CxP_Abonos WHERE AbonoID IN ({','.join(['?' for _ in abonos_to_del])})"
    cursor.execute(q2, abonos_to_del)
    print('Deleted Abonos')

conn.commit()
print('Committed cleanup.')
