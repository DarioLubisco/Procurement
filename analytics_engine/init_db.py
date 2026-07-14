import os
import sys
from dotenv import load_dotenv

# Cargar .env desde /home/synapse/source/Pedidos/.env
load_dotenv("/home/synapse/source/Pedidos/.env", override=True)

# Agregar el directorio raíz al path para que funcione la importación
sys.path.append("/home/synapse/source/Pedidos")

from analytics_engine.core.db import db_cursor, query_dataframe

def main():
    try:
        with db_cursor() as cursor:
            # 1. Crear esquema Procurement si no existe
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'Procurement')
                BEGIN
                    EXEC('CREATE SCHEMA Procurement');
                END
            """)
            print("Esquema Procurement verificado.")

            # 2. Crear tabla ProveedorScorecard
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE s.name = 'Procurement' AND t.name = 'ProveedorScorecard')
                BEGIN
                    CREATE TABLE Procurement.ProveedorScorecard (
                        proveedor VARCHAR(255) PRIMARY KEY,
                        score_total INT,
                        competitividad FLOAT,
                        frescura FLOAT,
                        amplitud FLOAT,
                        anomalias FLOAT,
                        pdr_promedio FLOAT,
                        calidad FLOAT,
                        updated_at DATETIME
                    );
                    PRINT 'Tabla Procurement.ProveedorScorecard creada.';
                END
                ELSE
                BEGIN
                    PRINT 'Tabla Procurement.ProveedorScorecard ya existe.';
                END
            """)
            print("Tabla ProveedorScorecard verificada.")

            # 3. Crear tabla Prices (si no existe) y poblarla
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE s.name = 'Procurement' AND t.name = 'Prices')
                BEGIN
                    CREATE TABLE Procurement.Prices (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        proveedor VARCHAR(255),
                        codbarras VARCHAR(50),
                        precio_usd DECIMAL(18,4),
                        fecha DATETIME,
                        fuente VARCHAR(50) DEFAULT 'SACOMP'
                    );
                    PRINT 'Tabla Procurement.Prices creada.';
                END
            """)
            
            # 4. Crear tabla OptimizerConfig (NUEVO v3.1)
            cursor.execute("""
                IF NOT EXISTS (SELECT * FROM sys.tables t JOIN sys.schemas s ON t.schema_id = s.schema_id WHERE s.name = 'Procurement' AND t.name = 'OptimizerConfig')
                BEGIN
                    CREATE TABLE Procurement.OptimizerConfig (
                        id INT IDENTITY(1,1) PRIMARY KEY,
                        profile_name VARCHAR(100) NOT NULL,
                        is_active BIT DEFAULT 0,
                        
                        -- Amplifier
                        amp_a FLOAT DEFAULT 5.84,
                        amp_b FLOAT DEFAULT 1.29,
                        amp_max_increment_pct FLOAT DEFAULT 500.0,
                        amp_floor_pct FLOAT DEFAULT 0.2,
                        
                        -- S4
                        s4_enabled BIT DEFAULT 0,
                        s4_porcentaje_base FLOAT DEFAULT 0.66,
                        
                        -- Monto Maximo
                        monto_buffer_pct FLOAT DEFAULT 20.0,
                        monto_days_reduction_pct FLOAT DEFAULT 20.0,
                        
                        -- Extension
                        ext_max_dias_extra INT DEFAULT 21,
                        ext_umbral FLOAT DEFAULT -0.10,
                        ext_eta FLOAT DEFAULT 4.0,
                        
                        -- Sustitucion & Oportunidad
                        sust_kappa FLOAT DEFAULT 5.0,
                        opp_lambda FLOAT DEFAULT 1.0,
                        
                        -- Pesos
                        w1_elasticidad FLOAT DEFAULT 0.15,
                        w2_demanda FLOAT DEFAULT 0.25,
                        w3_posicionamiento FLOAT DEFAULT 0.25,
                        w4_oportunidad FLOAT DEFAULT 0.20,
                        w5_extension FLOAT DEFAULT 0.15,
                        
                        -- Meta
                        created_at DATETIME DEFAULT GETDATE(),
                        created_by VARCHAR(50)
                    );
                    PRINT 'Tabla Procurement.OptimizerConfig creada.';
                    
                    -- Insertar default
                    INSERT INTO Procurement.OptimizerConfig (
                        profile_name, is_active,
                        amp_a, amp_b, amp_max_increment_pct, amp_floor_pct,
                        s4_enabled, s4_porcentaje_base,
                        monto_buffer_pct, monto_days_reduction_pct,
                        ext_max_dias_extra, ext_umbral, ext_eta,
                        sust_kappa, opp_lambda,
                        w1_elasticidad, w2_demanda, w3_posicionamiento, w4_oportunidad, w5_extension,
                        created_by
                    ) VALUES (
                        'Default Calibrated v3.1', 1,
                        5.84, 1.29, 500.0, 0.2,
                        0, 0.66,
                        20.0, 20.0,
                        21, -0.10, 4.0,
                        5.0, 1.0,
                        0.15, 0.25, 0.25, 0.20, 0.15,
                        'System'
                    );
                END
                ELSE
                BEGIN
                    PRINT 'Tabla Procurement.OptimizerConfig ya existe.';
                END
            """)
            print("Tabla OptimizerConfig verificada.")

            print("Estructura de BD actualizada con éxito.")
            
    except Exception as e:
        print(f"Error actualizando base de datos: {e}")
        
    try:
        sql_tables = """
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME LIKE 'SACOMP%' OR TABLE_NAME LIKE 'SAITEMFAC%' OR TABLE_NAME = 'SAFACT'
        """
        df_tables = query_dataframe(sql_tables)
        print('Tables in Saint:')
        print(df_tables)
        
        if 'SACOMP' in df_tables['TABLE_NAME'].values:
            df_cols = query_dataframe("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'SACOMP'")
            print("SACOMP Columns:", df_cols['COLUMN_NAME'].tolist()[:15])
            
        if 'SAITEMFAC' in df_tables['TABLE_NAME'].values:
            df_cols = query_dataframe("SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'SAITEMFAC'")
            print("SAITEMFAC Columns:", df_cols['COLUMN_NAME'].tolist()[:15])
            
    except Exception as e:
        print(f"Error checking Saint tables: {e}")

if __name__ == "__main__":
    main()
