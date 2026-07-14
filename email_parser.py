import os
import sys
import json
import hashlib
import argparse
from datetime import datetime
import pandas as pd
import pyodbc
from dotenv import load_dotenv

# Ensure we can import google.generativeai, wrap in try-except for clear error messages
try:
    import google.generativeai as genai
except ImportError:
    genai = None

# Load environment variables
load_dotenv()

# --- Database Connection ---
DB_SERVER = os.getenv("DB_SERVER", "amc.sql\\efficacis3")
DB_DATABASE = os.getenv("DB_DATABASE", "EnterpriseAdmin_AMC")
DB_USERNAME = os.getenv("DB_USERNAME", "sa")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Twinc3pt.")

def get_db_connection():
    available = pyodbc.drivers()
    driver_name = os.getenv("DRIVER", "ODBC Driver 18 for SQL Server").strip("{}")
    
    if driver_name not in available:
        if "ODBC Driver 18 for SQL Server" in available:
            driver_name = "ODBC Driver 18 for SQL Server"
        elif "ODBC Driver 17 for SQL Server" in available:
            driver_name = "ODBC Driver 17 for SQL Server"
        elif "SQL Server" in available:
            driver_name = "SQL Server"

    conn_str = (
        f"DRIVER={{{driver_name}}};"
        f"SERVER={DB_SERVER};"
        f"DATABASE={DB_DATABASE};"
        f"UID={DB_USERNAME};"
        f"PWD={DB_PASSWORD};"
        f"Encrypt=yes;"
        f"TrustServerCertificate=yes;"
    )
    conn = pyodbc.connect(conn_str)
    conn.timeout = 30
    return conn

# --- Idempotency (Hash checking) ---
def get_file_hash(filepath: str) -> str:
    """Calculate SHA-256 hash of a file."""
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def is_file_processed(conn, file_hash: str) -> bool:
    """Check if the file hash already exists in the database."""
    cursor = conn.cursor()
    # Create tracking table if it doesn't exist
    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='InboundFilesLog' AND xtype='U')
        CREATE TABLE InboundFilesLog (
            FileHash VARCHAR(64) PRIMARY KEY,
            ProviderID VARCHAR(50),
            ProcessedAt DATETIME DEFAULT GETDATE(),
            Status VARCHAR(20)
        )
    """)
    conn.commit()
    
    cursor.execute("SELECT 1 FROM InboundFilesLog WHERE FileHash = ?", (file_hash,))
    return cursor.fetchone() is not None

def mark_file_processed(conn, file_hash: str, provider_id: str, status: str = "SUCCESS"):
    """Mark file as processed to prevent future duplicates."""
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO InboundFilesLog (FileHash, ProviderID, ProcessedAt, Status)
        VALUES (?, ?, GETDATE(), ?)
    """, (file_hash, provider_id, status))
    conn.commit()

import requests

# --- Telegram Notification ---
def send_telegram_alert(message: str):
    """Sends an alert to the Telegram group using env variables."""
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("Telegram variables (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID) not set. Skipping alert.")
        return
        
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        print(f"Failed to send Telegram alert: {e}")

# --- Extraction Logic ---
def extract_pdf_with_gemini(filepath: str, provider_id: str) -> pd.DataFrame:
    """Use Gemini 1.5 Flash to extract table data from unstructured PDFs or CSVs."""
    if genai is None:
        raise ImportError("google-generativeai is not installed. Run 'pip install google-generativeai'")
        
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    print(f"Uploading {filepath} to Gemini API...")
    sample_file = genai.upload_file(path=filepath, display_name=f"Inventory_{provider_id}")
    
    prompt = """
    Actúa como un experto en extracción de datos OCR. Analiza este documento de inventario de farmacia y extrae la tabla de productos.
    Ignora cualquier información de encabezado comercial (logos, direcciones de la droguería, totales de pie de página).
    Extrae solo las filas de productos.
    Devuelve estrictamente un arreglo JSON validado que contenga objetos con las siguientes llaves (si un dato no está presente, pon nulo):
    - "codigo_producto": Código interno del producto (string).
    - "codigo_barras": Código de barras EAN/GTIN (string).
    - "descripcion_producto": Nombre del producto (string).
    - "fecha_lote": Fecha de vencimiento o lote (YYYY-MM-DD o string original).
    - "precio_unitario": Precio base unitario (número float).
    - "pct_oferta_vigente": Descuento comercial o porcentaje de oferta (string o float).
    - "precio_unitario_final": Precio final neto tras descuentos (número float).
    - "stock_disponible": Cantidad disponible (número entero).
    - "articulo_indexado": Si es indexado o no (booleano true/false).
    - "descuento_adicional": Cualquier otro descuento aplicable (string o float).
    
    No devuelvas Markdown extra, solo el arreglo JSON crudo.
    """
    
    print("Requesting extraction from Gemini...")
    response = model.generate_content([sample_file, prompt])
    genai.delete_file(sample_file.name)
    
    response_text = response.text.strip()
    if response_text.startswith("```json"):
        response_text = response_text[7:-3].strip()
    elif response_text.startswith("```"):
        response_text = response_text[3:-3].strip()
        
    try:
        data = json.loads(response_text)
        df = pd.DataFrame(data)
        return df
    except json.JSONDecodeError as e:
        print(f"Raw Gemini output:\n{response.text}")
        raise RuntimeError(f"Failed to decode Gemini JSON response: {str(e)}")

def extract_excel(filepath: str, provider_id: str) -> pd.DataFrame:
    """Extract and standardize data from an Excel file using pandas, with AI fallback."""
    try:
        xl = pd.ExcelFile(filepath)
        best_df = pd.DataFrame()
        keywords = ['codigo', 'código', 'cod', 'descripcion', 'descripción', 'producto', 'barras', 'precio', 'stk']
        
        for sheet in xl.sheet_names:
            df_head = xl.parse(sheet, header=None, nrows=50)
            header_row_index = -1
            for idx, row in df_head.iterrows():
                row_str = ' '.join([str(val).lower() for val in row.values if pd.notna(val)])
                matches = sum(1 for kw in keywords if kw in row_str)
                if matches >= 2:
                    header_row_index = idx
                    break
                    
            if header_row_index != -1:
                df = xl.parse(sheet, skiprows=header_row_index)
                df.columns = [str(c).strip().upper().replace('\n', ' ') for c in df.columns]
                
                col_map = {}
                for col in df.columns:
                    if 'COD' in col and not 'BARRA' in col: col_map[col] = 'codigo_producto'
                    elif 'BARRA' in col or 'EAN' in col: col_map[col] = 'codigo_barras'
                    elif 'DESCRIP' in col or 'PROD' in col: col_map[col] = 'descripcion_producto'
                    elif 'VENCE' in col or 'VENC' in col or 'CADUC' in col or 'LOTE' in col: 
                        if 'fecha_lote' not in col_map.values(): col_map[col] = 'fecha_lote'
                    elif 'PRECIO CON IVA' in col or 'PRECIO - DESC VEN' in col or 'NETO' in col:
                        col_map[col] = 'precio_unitario_final'
                    elif 'PRECIO UNITARIO' in col or ('PRECIO' in col and not 'ANTES' in col and not 'REF' in col): 
                        if 'precio_unitario' not in col_map.values(): col_map[col] = 'precio_unitario'
                    elif 'EXIST' in col or 'CANT' in col or 'STK' in col or 'STOCK' in col: col_map[col] = 'stock_disponible'
                    elif '% DCTO' in col or 'OFERTA' in col or 'DESC COM' in col: 
                        if 'pct_oferta_vigente' not in col_map.values(): col_map[col] = 'pct_oferta_vigente'
                    elif 'DTO VENTA' in col or 'BONIF' in col:
                        col_map[col] = 'descuento_adicional'
                    elif 'INDEX' in col or 'OLIMPIADAS' in col:
                        col_map[col] = 'articulo_indexado'
                        
                df = df.rename(columns=col_map)
                
                required_cols = ['codigo_producto', 'codigo_barras', 'descripcion_producto', 'fecha_lote', 
                                 'precio_unitario', 'pct_oferta_vigente', 'precio_unitario_final', 
                                 'stock_disponible', 'articulo_indexado', 'descuento_adicional']
                
                # We need at least codigo_producto and descripcion_producto to be useful
                if 'codigo_producto' in df.columns and 'descripcion_producto' in df.columns:
                    # Keep all columns that mapped correctly, add missing ones as None
                    for col in required_cols:
                        if col not in df.columns:
                            df[col] = None
                            
                    df = df[required_cols]
                    df = df.dropna(subset=['codigo_producto', 'descripcion_producto'], how='all')
                    
                    if len(df) > len(best_df):
                        best_df = df

        if best_df.empty:
            raise ValueError("No valid tabular data found matching keywords.")
            
        return best_df
        
    except Exception as e:
        print(f"Pandas extraction failed ({e}). Initiating AI Auto-Healing Fallback...")
        
        # Notify Telegram
        msg = (f"⚠️ <b>Auto-Healing Activado</b> 🤖\n"
               f"Proveedor: <b>{provider_id}</b>\n"
               f"El archivo Excel ha cambiado de formato o es complejo.\n"
               f"<i>Pandas falló: {str(e)[:60]}...</i>\n"
               f"⏳ Derivando el procesamiento a Gemini 1.5 Flash.")
        send_telegram_alert(msg)
        
        # Convert Excel to raw CSV so Gemini can parse it easily via File API
        temp_csv = filepath + ".tmp.csv"
        try:
            # We dump all sheets to one massive text file, or just the first one if it's too complex.
            # Actually, standard read_excel gets the first sheet, which is usually enough, but let's try to get all.
            raw_data = ""
            xl_fallback = pd.ExcelFile(filepath)
            for sheet in xl_fallback.sheet_names:
                df_raw = xl_fallback.parse(sheet)
                raw_data += f"\n--- SHEET: {sheet} ---\n"
                raw_data += df_raw.to_csv(index=False)
                
            with open(temp_csv, "w", encoding="utf-8") as f:
                f.write(raw_data)
                
            # Send CSV to Gemini
            healed_df = extract_pdf_with_gemini(temp_csv, provider_id)
            os.remove(temp_csv) # Cleanup
            return healed_df
            
        except Exception as fallback_e:
            if os.path.exists(temp_csv):
                os.remove(temp_csv)
            raise RuntimeError(f"AI Fallback also failed: {fallback_e}")

# --- Database Upsert (MERGE) ---
def upsert_to_sql_server(conn, df: pd.DataFrame, provider_id: str):
    """Perform an idempotent UPSERT (MERGE) into SQL Server matching FTP schema."""
    if df.empty:
        print("DataFrame is empty. Nothing to insert.")
        return
        
    cursor = conn.cursor()
    
    # Obtain current BCV rate to convert Bs to USD
    cursor.execute("SELECT TOP 1 dolarbcv FROM dolartoday ORDER BY id DESC")
    row = cursor.fetchone()
    bcv_rate = float(row[0]) if row and row[0] else 1.0
    print(f"Current BCV rate retrieved: {bcv_rate}")
    
    # 1. Ensure the target table exists
    schema = "Proveedores"
    target_table = f"[{schema}].[{provider_id}]"
    
    cursor.execute(f"""
        IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{schema}')
        BEGIN
            EXEC('CREATE SCHEMA [{schema}]');
        END
        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name='{provider_id}' AND schema_id = SCHEMA_ID('{schema}'))
        CREATE TABLE {target_table} (
            proveedor VARCHAR(50),
            codigo_producto VARCHAR(100),
            codigo_barras VARCHAR(100),
            descripcion_producto VARCHAR(255),
            fecha_lote VARCHAR(100),
            precio_unitario DECIMAL(18,4),
            pct_oferta_vigente VARCHAR(50),
            precio_unitario_final DECIMAL(18,4),
            stock_disponible INT,
            articulo_indexado BIT,
            descuento_adicional VARCHAR(50),
            fecha_carga DATETIME DEFAULT GETDATE(),
            PRIMARY KEY (proveedor, codigo_producto)
        )
    """)
    conn.commit()

    # 2. Create a temporary table for the staging data
    temp_table = f"#TempInventory_{provider_id}"
    cursor.execute(f"""
        IF OBJECT_ID('tempdb..{temp_table}') IS NOT NULL DROP TABLE {temp_table};
        CREATE TABLE {temp_table} (
            codigo_producto VARCHAR(100), codigo_barras VARCHAR(100), descripcion_producto VARCHAR(255),
            fecha_lote VARCHAR(100), precio_unitario DECIMAL(18,4), pct_oferta_vigente VARCHAR(50),
            precio_unitario_final DECIMAL(18,4), stock_disponible INT, articulo_indexado BIT, 
            descuento_adicional VARCHAR(50)
        )
    """)
    
    # 3. Insert data into the temp table
    insert_query = f"""
        INSERT INTO {temp_table} (codigo_producto, codigo_barras, descripcion_producto, fecha_lote, 
                                  precio_unitario, pct_oferta_vigente, precio_unitario_final, 
                                  stock_disponible, articulo_indexado, descuento_adicional)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    
    # Fill NaN with None for pyodbc compatibility
    df = df.where(pd.notnull(df), None)
    
    # Force types and perform Currency Conversion (Bs -> USD) if prices look like Bolivares
    df['precio_unitario'] = pd.to_numeric(df['precio_unitario'], errors='coerce')
    df['precio_unitario_final'] = pd.to_numeric(df['precio_unitario_final'], errors='coerce')
    
    # If the price is abnormally high for USD (e.g., > 1000), it's highly likely in Bolivares.
    # Convert it to USD.
    def convert_to_usd(price):
        if pd.notna(price) and price > 1000:
            return round(price / bcv_rate, 4)
        return round(price, 4) if pd.notna(price) else None

    df['precio_unitario'] = df['precio_unitario'].apply(convert_to_usd)
    df['precio_unitario_final'] = df['precio_unitario_final'].apply(convert_to_usd)
    
    df['stock_disponible'] = pd.to_numeric(df['stock_disponible'], errors='coerce').fillna(0).astype(int)
    df['codigo_producto'] = df['codigo_producto'].astype(str)
    
    # Convert index to boolean/bit representation (1/0 or True/False)
    if 'articulo_indexado' in df.columns:
        df['articulo_indexado'] = df['articulo_indexado'].apply(lambda x: 1 if str(x).lower() in ['true', '1', 'si', 'sí', 'indexado'] else 0)
    else:
        df['articulo_indexado'] = 0

    # Filter out invalid rows (must have codigo_producto)
    df = df[df['codigo_producto'].notna() & (df['codigo_producto'] != 'None') & (df['codigo_producto'] != '')]

    records = df[['codigo_producto', 'codigo_barras', 'descripcion_producto', 'fecha_lote', 
                  'precio_unitario', 'pct_oferta_vigente', 'precio_unitario_final', 
                  'stock_disponible', 'articulo_indexado', 'descuento_adicional']].values.tolist()
    
    if not records:
        print("No valid records found to insert.")
        return

    cursor.executemany(insert_query, records)
    
    # 4. Perform the MERGE operation exactly like FTP script
    merge_query = f"""
        MERGE {target_table} AS T
        USING (SELECT * FROM {temp_table}) AS S
          ON T.codigo_producto = S.codigo_producto AND T.proveedor = ?
        WHEN MATCHED THEN UPDATE SET
            codigo_barras=S.codigo_barras, descripcion_producto=S.descripcion_producto, 
            fecha_lote=S.fecha_lote, precio_unitario=S.precio_unitario, 
            pct_oferta_vigente=S.pct_oferta_vigente, precio_unitario_final=S.precio_unitario_final,
            stock_disponible=S.stock_disponible, articulo_indexado=S.articulo_indexado, 
            descuento_adicional=S.descuento_adicional, fecha_carga=GETDATE()
        WHEN NOT MATCHED THEN INSERT
            (proveedor, codigo_producto, codigo_barras, descripcion_producto, fecha_lote,
             precio_unitario, pct_oferta_vigente, precio_unitario_final,
             stock_disponible, articulo_indexado, descuento_adicional, fecha_carga)
        VALUES (?, S.codigo_producto, S.codigo_barras, S.descripcion_producto, S.fecha_lote,
                S.precio_unitario, S.pct_oferta_vigente, S.precio_unitario_final, 
                S.stock_disponible, S.articulo_indexado, S.descuento_adicional, GETDATE());
    """
    
    cursor.execute(merge_query, (provider_id, provider_id))
    conn.commit()
    print(f"MERGE completed successfully for Provider {provider_id}. Processed {len(records)} records.")

def get_provider_id(contact: str) -> str:
    """Resolve Provider ID from contact (email or phone) using provider_config.json"""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "provider_config.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Warning: {config_path} not found. Using raw contact as Provider ID.")
        return contact.upper()

    contact_clean = contact.strip().lower()
    
    # 1. Exact match (e.g. "pedidos@dropharma.com" or "584141234567")
    for key, val in config.items():
        if key.lower() == contact_clean:
            return val
            
    # 2. Domain match (e.g. "@dropharma.com" -> "dropharma.com")
    if "@" in contact_clean:
        domain = contact_clean.split("@")[1]
        for key, val in config.items():
            if key.lower() == domain:
                return val
                
    # 3. Fallback: return the raw contact uppercase
    print(f"Warning: Could not map contact '{contact}' to a Provider ID. Using raw contact.")
    return contact_clean.upper()

# --- Main Entry Point ---
def main():
    parser = argparse.ArgumentParser(description="Parse Supplier Inventory Files (Excel/PDF) and UPSERT to SQL Server.")
    parser.add_argument("--file", required=True, help="Path to the file to process (.xlsx, .xls, .pdf)")
    parser.add_argument("--contact", required=True, help="Sender Email or WhatsApp Number (e.g. 'pedidos@dropharma.com')")
    parser.add_argument("--force", action="store_true", help="Bypass idempotency (hash check) and force processing")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"Error: File not found: {args.file}")
        sys.exit(1)
        
    file_ext = os.path.splitext(args.file)[1].lower()
    if file_ext not in ['.xlsx', '.xls', '.pdf']:
        print(f"Error: Unsupported file type: {file_ext}. Must be Excel or PDF.")
        sys.exit(1)
        
    provider_id = get_provider_id(args.contact)
    print(f"Starting processing for file: {args.file}")
    print(f"Resolved Contact [{args.contact}] -> Provider ID: {provider_id}")
    
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"Database Connection Error: {e}")
        sys.exit(1)

    file_hash = get_file_hash(args.file)
    print(f"File SHA-256: {file_hash}")
    
    if not args.force and is_file_processed(conn, file_hash):
        print("Idempotency Triggered: This file has already been processed successfully. Exiting.")
        sys.exit(0)
        
    try:
        # Extract Data
        if file_ext in ['.xlsx', '.xls']:
            df = extract_excel(args.file, provider_id)
        elif file_ext == '.pdf':
            df = extract_pdf_with_gemini(args.file, provider_id)
            
        print(f"Extraction successful. {len(df)} records found.")
        
        # Load to SQL Server
        upsert_to_sql_server(conn, df, provider_id)
        
        # Mark success
        mark_file_processed(conn, file_hash, provider_id, "SUCCESS")
        print("Process completed successfully.")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()
