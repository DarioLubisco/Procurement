"""
SQL Migration Script — Synapse Auth System
Crea las tablas: synapse_usuarios, synapse_permisos, synapse_log_actividad
Inserta un usuario admin por defecto.

EJECUTAR UNA VEZ en producción o local para inicializar el schema.
Contraseña admin default: synapse2024  (¡cambiar después de primer login!)
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import bcrypt
from database import get_db_connection

MIGRATION_SQL = """
-- =============================================
-- TABLA: synapse_usuarios
-- =============================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'synapse_usuarios')
BEGIN
    CREATE TABLE dbo.synapse_usuarios (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        username    NVARCHAR(100) NOT NULL UNIQUE,
        nombre      NVARCHAR(200) NOT NULL,
        password_hash NVARCHAR(500) NOT NULL,
        email       NVARCHAR(200),
        activo      BIT NOT NULL DEFAULT 1,
        creado_en   DATETIME NOT NULL DEFAULT GETDATE(),
        ultimo_login DATETIME
    );
    PRINT 'Tabla synapse_usuarios creada.';
END
ELSE
    PRINT 'synapse_usuarios ya existe.';

-- =============================================
-- TABLA: synapse_permisos
-- =============================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'synapse_permisos')
BEGIN
    CREATE TABLE dbo.synapse_permisos (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        usuario_id  INT NOT NULL REFERENCES dbo.synapse_usuarios(id) ON DELETE CASCADE,
        modulo      NVARCHAR(50) NOT NULL,  -- 'chat' | 'caja' | 'cxp' | 'admin'
        puede_leer  BIT NOT NULL DEFAULT 1,
        puede_escribir BIT NOT NULL DEFAULT 0,
        CONSTRAINT UQ_usuario_modulo UNIQUE (usuario_id, modulo)
    );
    PRINT 'Tabla synapse_permisos creada.';
END
ELSE
    PRINT 'synapse_permisos ya existe.';

-- =============================================
-- TABLA: synapse_log_actividad
-- =============================================
IF NOT EXISTS (SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'synapse_log_actividad')
BEGIN
    CREATE TABLE dbo.synapse_log_actividad (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        usuario_id  INT REFERENCES dbo.synapse_usuarios(id),
        username    NVARCHAR(100),
        accion      NVARCHAR(200) NOT NULL,
        modulo      NVARCHAR(50),
        detalle     NVARCHAR(MAX),
        ip          NVARCHAR(50),
        timestamp   DATETIME NOT NULL DEFAULT GETDATE()
    );
    PRINT 'Tabla synapse_log_actividad creada.';
END
ELSE
    PRINT 'synapse_log_actividad ya existe.';
"""

def run_migration():
    print("🔄 Conectando a SQL Server...")
    conn = get_db_connection()
    cursor = conn.cursor()

    print("🔄 Ejecutando migration DDL...")
    cursor.execute(MIGRATION_SQL)
    conn.commit()

    # Verificar si ya existe el admin
    cursor.execute("SELECT COUNT(*) FROM dbo.synapse_usuarios WHERE username = 'admin'")
    exists = cursor.fetchone()[0]

    if not exists:
        print("🔄 Creando usuario admin por defecto...")
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw("synapse2024".encode('utf-8'), salt).decode('utf-8')
        cursor.execute(
            """INSERT INTO dbo.synapse_usuarios (username, nombre, password_hash, email)
               VALUES (?, ?, ?, ?)""",
            "admin", "Administrador Synapse", hashed, "admin@synapse.local"
        )
        conn.commit()

        # Obtener el ID del admin recién creado
        cursor.execute("SELECT id FROM dbo.synapse_usuarios WHERE username = 'admin'")
        admin_id = cursor.fetchone()[0]

        # Asignar todos los permisos al admin
        modulos = ["chat", "caja", "cxp", "admin"]
        for mod in modulos:
            cursor.execute(
                """INSERT INTO dbo.synapse_permisos (usuario_id, modulo, puede_leer, puede_escribir)
                   VALUES (?, ?, 1, 1)""",
                admin_id, mod
            )
        conn.commit()
        print(f"✅ Usuario admin creado con ID={admin_id}. Contraseña: synapse2024")
    else:
        print("ℹ️  Usuario admin ya existe — no se recrea.")

    conn.close()
    print("✅ Migration completada exitosamente.")

if __name__ == "__main__":
    run_migration()
