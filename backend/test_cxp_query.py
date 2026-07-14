import database
import logging

try:
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT SettingValue FROM EnterpriseAdmin_AMC.Procurement.Settings WITH (NOLOCK) WHERE SettingKey = 'LimiteCarga'")
    row = cursor.fetchone()
    print("LimiteCarga:", row)
    
    date_filter = " AND SAACXP.FechaE >= DATEADD(month, -4, GETDATE())"
    top_clause = "TOP 500"
    tolerance = 0.50

    cleanup_query = """
        DELETE PP
        FROM EnterpriseAdmin_AMC.Procurement.PagosPlanificados PP
        INNER JOIN EnterpriseAdmin_AMC.dbo.SAACXP ON PP.NroUnico = SAACXP.NroUnico
        WHERE SAACXP.Saldo <= ? AND SAACXP.TipoCxP = '10'
    """
    cursor.execute(cleanup_query, (tolerance,))
    conn.commit()
    print("Cleanup done")

    query = f"""
        SELECT {top_clause}
            SACOMP.FechaI
        FROM dbo.SAACXP
        OUTER APPLY (
            SELECT SUM(MontoBsAbonado) AS TotalBs
            FROM EnterpriseAdmin_AMC.dbo.CxP_Abonos A 
            WHERE A.CodProv = SAACXP.CodProv AND A.NumeroD = SAACXP.NumeroD AND ISNULL(A.AfectaSaldo, 1) = 1
        ) abonos
        OUTER APPLY (
            SELECT TOP 1 Id, MontoRetenido
            FROM EnterpriseAdmin_AMC.Procurement.Retenciones_IVA WITH (NOLOCK)
            WHERE CodProv = SAACXP.CodProv AND NumeroD = SAACXP.NumeroD AND Estado != 'ANULADO'
        ) portal_ret
        OUTER APPLY (
            SELECT TOP 1 NumeroD
            FROM dbo.SAPAGCXP
            WHERE SAPAGCXP.NroUnico = SAACXP.NroUnico
        ) SAPAGCXP
        LEFT OUTER JOIN dbo.SAPROV ON SAACXP.CodProv = SAPROV.CodProv
        LEFT OUTER JOIN dbo.SAIPACXP ON SAACXP.NroUnico = SAIPACXP.NroUnico
        LEFT OUTER JOIN dbo.SACOMP ON SAACXP.NumeroD = SACOMP.NumeroD AND SAACXP.CodProv = SACOMP.CodProv
        LEFT OUTER JOIN EnterpriseAdmin_AMC.Procurement.InvoiceSettings inv_set ON SAACXP.CodProv = inv_set.CodProv AND SAACXP.NumeroD = inv_set.NumeroD
        OUTER APPLY (
            SELECT TOP 1 dolarbcv 
            FROM EnterpriseAdmin_AMC.dbo.dolartoday 
            WHERE CAST(fecha AS DATE) <= CAST(SAACXP.FechaE AS DATE)
            ORDER BY fecha DESC
        ) dt_emision
        OUTER APPLY (
            SELECT TOP 1 dolarbcv 
            FROM EnterpriseAdmin_AMC.dbo.dolartoday 
            WHERE dolarbcv IS NOT NULL
            ORDER BY id DESC
        ) dt_actual
        LEFT OUTER JOIN EnterpriseAdmin_AMC.Procurement.PagosPlanificados PP
            ON SAACXP.NroUnico = PP.NroUnico
        WHERE SAACXP.TipoCxP = '10' 
            AND (SAACXP.NumeroD LIKE ?
            OR SACOMP.NumeroD LIKE ?
            OR SAPAGCXP.NumeroD LIKE ?
            OR SAPROV.Descrip LIKE ?)
            {date_filter}
        ORDER BY SAACXP.FechaE DESC
    """
    params = ['%%', '%%', '%%', '%%']
    cursor.execute(query, tuple(params))
    rows = cursor.fetchall()
    print("Fetched rows:", len(rows))
    
except Exception as e:
    print("Error:", e)
finally:
    if 'conn' in locals():
        conn.close()
