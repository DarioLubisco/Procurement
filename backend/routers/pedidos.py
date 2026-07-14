import os
import io
import logging
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Form, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
import pandas as pd
import pyodbc
import math
import database

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])

# Ruta absoluta/relativa a la query
QUERY_PATH = os.path.join(os.path.dirname(__file__), "..", "queries", "pedidos.sql")

def load_query():
    try:
        with open(QUERY_PATH, 'r', encoding='utf-8-sig') as f:
            return f.read().strip()
    except Exception as e:
        logging.error(f"Error cargando query de pedidos: {e}")
        return None

@router.get("/categories")
async def get_categories():
    try:
        try:
            from backend.services.categories_loader import load_categories_with_retry
        except ImportError:
            from services.categories_loader import load_categories_with_retry  # type: ignore

        categories = load_categories_with_retry(database.get_db_connection)
        return {"categories": categories}
    except Exception as e:
        logging.error(f"Error fetching categories: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/generate")
async def generate_report(
    pedido_days: str = Form(...),
    num_rows: int = Form(...),
    categories: Optional[str] = Form(None),
    subtraction_files: Optional[List[UploadFile]] = File(None),
    umbral_rotacion: float = Form(0.0),
    forced_includes: Optional[str] = Form(None),
    preview_mode: str = Form("false"),
    include_generics: str = Form("true"),
    include_brands: str = Form("true"),
    nivel_rotacion: str = Form("sku"),       # 'sku' = R1 individual (actual), 'base' = R2 grupo, 'custom' = dinámico
    atributos_custom: Optional[str] = Form(None)  # Solo si nivel_rotacion='custom': 'origen,generico'
):
    try:
        query = load_query()
        if not query:
            raise HTTPException(status_code=500, detail="No se pudo cargar la consulta SQL maestra.")

        filter_condition = """
            SELECT 1
            FROM Procurement.principio_activo pa
            WHERE
              LEFT (p.Descrip, 7) = LEFT (pa.descripcion, 7)
              OR (
                CHARINDEX(' ', p.Descrip) > 0
                AND CHARINDEX(' ', pa.descripcion) > 0
                AND LEFT(
                  SUBSTRING(
                    p.Descrip,
                    CHARINDEX(' ', p.Descrip) + 1,
                    LEN(p.Descrip)
                  ),
                  7
                ) = LEFT(
                  SUBSTRING(
                    pa.descripcion,
                    CHARINDEX(' ', pa.descripcion) + 1,
                    LEN(pa.descripcion)
                  ),
                  7
                )
              )
        """

        if include_generics.lower() == "true" and include_brands.lower() == "true":
            filter_sql = "" # Sin filtro, trae todo
        elif include_generics.lower() == "true":
            filter_sql = f"AND EXISTS ({filter_condition})"
        elif include_brands.lower() == "true":
            filter_sql = f"AND NOT EXISTS ({filter_condition})"
        else:
            raise HTTPException(status_code=400, detail="Debe seleccionar al menos un tipo de producto (Marcas o Genéricos).")

        query = query.replace('/* PRODUCT_FILTER_PLACEHOLDER */', filter_sql)

        # Validar entradas
        if num_rows <= 0:
            num_rows = 5000
        
        # Procesar archivos de resta
        subtraction_dfs = []
        if subtraction_files:
            for file in subtraction_files:
                if file.filename:
                    try:
                        content = await file.read()
                        if len(content) > 0:
                            df_sub = pd.read_excel(io.BytesIO(content))
                            subtraction_dfs.append(df_sub)
                    except Exception as e:
                        logging.warning(f"Error procesando archivo de resta {file.filename}: {e}")

        # Ejecutar Query Maestra
        conn = database.get_db_connection()
        df = pd.read_sql(query, conn)
        conn.close()

        if df.empty:
            raise HTTPException(status_code=404, detail="No se encontraron datos en la base de datos para generar el pedido.")

        # Filtrar por categorías si aplica
        if categories:
            parsed_categories = [cat.strip() for cat in categories.split(",") if cat.strip()]
            if 'Instancia' in df.columns:
                df = df[df['Instancia'].isin(parsed_categories)]

        # Lógica de Generación (Cálculo dinámico en Python)
        df['RotacionMensual'] = pd.to_numeric(df.get('RotacionMensual', 0.0), errors='coerce').fillna(0.0)
        df['Existen'] = pd.to_numeric(df.get('Existen', 0), errors='coerce').fillna(0)
        
        try:
            days = float(pedido_days)
        except ValueError:
            days = 14.0

        # ── Rotación Grupal: Si nivel_rotacion != 'sku', usar rotación agrupada ──
        if nivel_rotacion.lower() in ('base', 'custom'):
            try:
                conn_rg = database.get_db_connection()
                
                if nivel_rotacion.lower() == 'base':
                    # R2 cached: leer rot_base e inv_base de RotacionGrupal
                    df_rg = pd.read_sql("""
                        SELECT codbarras, rot_base, inv_base
                        FROM Procurement.RotacionGrupal
                    """, conn_rg)
                elif nivel_rotacion.lower() == 'custom' and atributos_custom:
                    # Motor dinámico: calcular on-the-fly con atributos seleccionados
                    from routers.rotacion_grupal import ATRIBUTOS_VALIDOS, ATRIBUTOS_BASE
                    attrs = ATRIBUTOS_BASE | {a.strip() for a in atributos_custom.split(',') if a.strip() in ATRIBUTOS_VALIDOS}
                    group_cols = ', '.join(sorted(attrs))
                    
                    df_rg = pd.read_sql(f"""
                        SELECT 
                            rg.codbarras,
                            SUM(rg.rot_sku) OVER (PARTITION BY {group_cols}) AS rot_base,
                            SUM(rg.existen_sku) OVER (PARTITION BY {group_cols}) AS inv_base
                        FROM Procurement.RotacionGrupal rg
                    """, conn_rg)
                else:
                    df_rg = pd.DataFrame()  # fallback a SKU individual
                
                conn_rg.close()
                
                if not df_rg.empty:
                    # Merge con datos principales
                    df_rg['codbarras'] = df_rg['codbarras'].astype(str)
                    df['CodProd'] = df['CodProd'].astype(str)
                    df = df.merge(df_rg, left_on='CodProd', right_on='codbarras', how='left')
                    
                    # Reemplazar rotación y existencia con valores grupales
                    df['RotacionMensual'] = pd.to_numeric(df['rot_base'], errors='coerce').fillna(df['RotacionMensual'])
                    df['Existen'] = pd.to_numeric(df['inv_base'], errors='coerce').fillna(df['Existen'])
                    
                    logging.info(f"Pedido con rotación grupal nivel='{nivel_rotacion}': {len(df_rg)} SKUs mapeados")
                    
            except Exception as e:
                logging.warning(f"Error cargando rotación grupal, usando SKU individual: {e}")
                # Fallback silencioso a rotación individual

        df['CANTIDAD'] = (df['RotacionMensual'] * days / 30.0) - df['Existen']
        df['CANTIDAD'] = df['CANTIDAD'].round().astype(int)

        cols_to_keep = ['CodProd', 'CANTIDAD', 'RotacionMensual', 'Existen']
        if 'Descrip' in df.columns: cols_to_keep.append('Descrip')
        
        df_final = df[cols_to_keep].copy()
        df_final.rename(columns={'CodProd': 'BARRA'}, inplace=True)

        # Aplicar Resta si hay archivos
        if subtraction_dfs:
            valid_sub_dfs = []
            for sub_df in subtraction_dfs:
                if not sub_df.empty and 'BARRA' in sub_df.columns and 'CANTIDAD' in sub_df.columns:
                    sub_df['BARRA'] = sub_df['BARRA'].astype(str)
                    valid_sub_dfs.append(sub_df)
            
            if valid_sub_dfs:
                combined_sub = pd.concat(valid_sub_dfs, ignore_index=True)
                agg_sub = combined_sub.groupby('BARRA', as_index=False)['CANTIDAD'].sum()
                
                df_merged = pd.merge(df_final, agg_sub, on='BARRA', how='left', suffixes=('', '_subtract'))
                df_merged['CANTIDAD_subtract'] = df_merged['CANTIDAD_subtract'].fillna(0)
                df_merged['CANTIDAD'] = df_merged['CANTIDAD'] - df_merged['CANTIDAD_subtract']
                df_final = df_merged.copy()

        df_final['RotacionMensual'] = pd.to_numeric(df_final['RotacionMensual'], errors='coerce').fillna(0.0)

        # Separar por umbral de rotación ANTES de filtrar CANTIDAD > 0
        # Excluidos: todos los que tengan rotación por debajo del umbral (para que el usuario los force si quiere)
        df_excluidos = df_final[df_final['RotacionMensual'] < umbral_rotacion].copy()
        df_excluidos = df_excluidos.drop_duplicates(subset=['BARRA'])

        # Prefiltrados: los que tienen buena rotación Y ADEMÁS tienen CANTIDAD calculada > 0
        df_prefiltrados = df_final[(df_final['RotacionMensual'] >= umbral_rotacion) & (df_final['CANTIDAD'] > 0)].copy()
        df_prefiltrados = df_prefiltrados.drop_duplicates(subset=['BARRA'])

        if preview_mode.lower() == "true":
            excluidos_list = df_excluidos.to_dict(orient='records')
            
            # Limpiar valores NaN/Infinity para asegurar serialización JSON válida
            for item in excluidos_list:
                for k, v in item.items():
                    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
                        item[k] = 0.0
            
            return JSONResponse(content={"excluidos": excluidos_list})

        # Aplicar inclusiones forzadas de productos excluidos seleccionados por el usuario
        forced_barcodes = []
        if forced_includes:
            forced_barcodes = [b.strip() for b in forced_includes.split(",") if b.strip()]

        df_forced = df_excluidos[df_excluidos['BARRA'].astype(str).isin(forced_barcodes)].copy()
        df_final_export = pd.concat([df_prefiltrados, df_forced], ignore_index=True)

        # Ordenar opcionalmente si hiciera falta (mantendremos el orden natural)
        # Aplicar Límite al final
        df_final_export = df_final_export.head(num_rows)

        # Limpieza final: Forzar mínimo de 1 para evitar CANTIDAD=0 en Excel exportado
        df_final_export['CANTIDAD'] = df_final_export['CANTIDAD'].astype(int)
        df_final_export.loc[df_final_export['CANTIDAD'] < 1, 'CANTIDAD'] = 1
        df_final_export['BARRA'] = df_final_export['BARRA'].astype(str)

        # Dejar solo las columnas requeridas para el Excel
        df_excel = df_final_export[['BARRA', 'CANTIDAD']].copy()

        # Crear Excel en Memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_excel.to_excel(writer, sheet_name='Precios', index=False)
        output.seek(0)

        if include_generics.lower() == "true" and include_brands.lower() == "true":
            tipo_pedido = "Mixto"
        elif include_generics.lower() == "true":
            tipo_pedido = "Generico"
        else:
            tipo_pedido = "Marcas"
        filename = f"Pedido_Synapse_{tipo_pedido}_{datetime.now().strftime('%Y%m%d')}_{pedido_days}Dias.xlsx"
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            output, 
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'}
        )

    except Exception as e:
        logging.error(f"Error generando reporte de pedidos: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
