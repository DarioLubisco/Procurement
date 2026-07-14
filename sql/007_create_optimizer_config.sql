-- Script: 007_create_optimizer_config.sql
-- Propósito: Tabla de configuración de parámetros para el motor de optimización v3.1
-- Permite que el frontend y el backend compartan configuración.

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
    PRINT 'Tabla Procurement.OptimizerConfig creada exitosamente.';

    -- Insertar el perfil por defecto (calibrado)
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
    PRINT 'Perfil por defecto insertado en Procurement.OptimizerConfig.';
END
ELSE
BEGIN
    PRINT 'La tabla Procurement.OptimizerConfig ya existe.';
END
