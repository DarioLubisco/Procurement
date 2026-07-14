"""Load catalog + market offers for Generar Sencillo (DB adapters)."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd

from analytics_engine.core.criterios_agrupacion import CRITERIOS_AGRUPACION_DEFAULT

logger = logging.getLogger(__name__)

QUERY_PATH = os.path.join(os.path.dirname(__file__), "..", "queries", "pedidos.sql")


def _ensure_analytics_path() -> None:
    import sys

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def map_catalog_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Map legacy pedidos.sql columns → seam catalog rows."""
    if df.empty:
        return []
    out = df.copy()
    rename = {}
    if "CodProd" in out.columns:
        rename["CodProd"] = "barra"
    if "Descrip" in out.columns:
        rename["Descrip"] = "descripcion"
    if "RotacionMensual" in out.columns:
        rename["RotacionMensual"] = "rotacion_mensual"
    if "Existen" in out.columns:
        rename["Existen"] = "existen"
    if "Instancia" in out.columns:
        rename["Instancia"] = "categoria"
    out = out.rename(columns=rename)
    out["barra"] = out["barra"].astype(str)
    if "descripcion" not in out.columns:
        out["descripcion"] = ""
    if "rotacion_mensual" not in out.columns:
        out["rotacion_mensual"] = 0.0
    if "existen" not in out.columns:
        out["existen"] = 0.0
    if "es_generico" not in out.columns:
        out["es_generico"] = True
    for attr in CRITERIOS_AGRUPACION_DEFAULT:
        if attr not in out.columns:
            out[attr] = ""
    cols = [
        "barra",
        "descripcion",
        "rotacion_mensual",
        "existen",
        "es_generico",
        "categoria",
        *CRITERIOS_AGRUPACION_DEFAULT,
    ]
    cols = [c for c in cols if c in out.columns]
    return out[cols].to_dict(orient="records")


def map_mercado_vivo_dataframe(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """Map Analitica.Mercado_Vivo → market_offers rows."""
    if df.empty:
        return []
    out = df.copy()
    rename = {
        "codigo_barras": "barra",
        "precio_unitario_final": "precio",
        "stock_disponible": "stock_proveedor",
        "descripcion_producto": "descripcion",
    }
    out = out.rename(columns={k: v for k, v in rename.items() if k in out.columns})
    if "barra" not in out.columns:
        return []
    out["barra"] = out["barra"].astype(str)
    if "proveedor" not in out.columns:
        out["proveedor"] = ""
    if "precio" not in out.columns:
        out["precio"] = 0.0
    if "stock_proveedor" not in out.columns:
        out["stock_proveedor"] = None
    cols = ["barra", "proveedor", "precio", "stock_proveedor"]
    if "descripcion" in out.columns:
        cols.append("descripcion")
    return out[cols].to_dict(orient="records")


def load_catalog_and_offers_from_db(
    *,
    categorias: Optional[Sequence[str]] = None,
    include_generics: bool = True,
    include_brands: bool = True,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load SAPROD rotation catalog + Mercado_Vivo offers (productive path)."""
    _ensure_analytics_path()
    import database

    with open(QUERY_PATH, "r", encoding="utf-8-sig") as f:
        query = f.read().strip()

    # Same filter placeholder strategy as legacy generate (generics/brands)
    if include_generics and include_brands:
        filter_sql = "1=1"
    elif include_generics and not include_brands:
        filter_sql = f"""EXISTS (
            SELECT 1 FROM Procurement.principio_activo pa
            WHERE LEFT(p.Descrip, 7) = LEFT(pa.descripcion, 7)
        )"""
    elif include_brands and not include_generics:
        filter_sql = f"""NOT EXISTS (
            SELECT 1 FROM Procurement.principio_activo pa
            WHERE LEFT(p.Descrip, 7) = LEFT(pa.descripcion, 7)
        )"""
    else:
        filter_sql = "1=0"
    query = query.replace("/* PRODUCT_FILTER_PLACEHOLDER */", f"AND ({filter_sql})")

    conn = database.get_db_connection()
    try:
        catalog_df = pd.read_sql(query, conn)
        if categorias:
            wanted = {str(c).strip() for c in categorias if str(c).strip()}
            if wanted and "Instancia" in catalog_df.columns:
                catalog_df = catalog_df[
                    catalog_df["Instancia"].astype(str).isin(wanted)
                ]
        catalog_rows = map_catalog_dataframe(catalog_df)
        barras = [r["barra"] for r in catalog_rows]
        offers_df = pd.DataFrame(
            columns=[
                "codigo_barras",
                "proveedor",
                "precio_unitario_final",
                "stock_disponible",
                "descripcion_producto",
            ]
        )
        if barras:
            # Cap IN-list size — large lists timeout ODBC against Mercado_Vivo
            sample = barras[:200]
            placeholders = ",".join(["?"] * len(sample))
            try:
                offers_df = pd.read_sql(
                    f"""
                    SELECT codigo_barras, proveedor, precio_unitario_final,
                           stock_disponible, descripcion_producto
                    FROM Analitica.Mercado_Vivo
                    WHERE codigo_barras IN ({placeholders})
                    """,
                    conn,
                    params=sample,
                )
            except Exception as exc:
                logger.warning("Mercado_Vivo unavailable: %s", exc)
                offers_df = pd.DataFrame(
                    columns=[
                        "codigo_barras",
                        "proveedor",
                        "precio_unitario_final",
                        "stock_disponible",
                        "descripcion_producto",
                    ]
                )
        offers_rows = map_mercado_vivo_dataframe(offers_df)
        return catalog_rows, offers_rows
    finally:
        try:
            conn.close()
        except Exception:
            pass
