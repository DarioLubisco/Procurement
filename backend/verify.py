import database
conn = database.get_db_connection()
cursor = conn.cursor()
cursor.execute("DELETE FROM EnterpriseAdmin_AMC.Procurement.Retenciones_IVA WHERE Id = 61")
cursor.execute("DELETE FROM EnterpriseAdmin_AMC.dbo.CxP_Abonos WHERE Referencia LIKE '%20260400000429%' AND TipoAbono = 'RETENCION_IVA'")
conn.commit()
print('Cleaned up ID 61 entirely')
