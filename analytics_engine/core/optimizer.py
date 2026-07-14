"""
Synapse Analytics Engine — Optimizer v3.2 (Market-Driven)
=========================================================
Motor de optimización de compras multi-proveedor con 5 factores
no lineales, gobernado por MontoMaximo.

PIVOTE v3.2: El pedido se origina desde el MERCADO EN VIVO,
agrupado por los 3 atributos (PA, FF, Concentración).
La necesidad (gap) se calcula sumando rotación y stock de TODO
el catálogo para cada grupo-molécula.

Capas:
  1. Agrupamiento desde Mercado Vivo → Grupos de Molécula
  2. Gap GRUPAL (rotación y stock de todo el catálogo por molécula)
  2.1. S4 no lineal para SKUs costosos
  2.2. MontoEstimado y MontoMaximo
  3. Scoring 5 factores (F1-F5) para cada oferta del mercado
  4. Distribución proporcional gobernada
  5. Split por lead time + stockout cost
  6. Justificación textual
"""
import logging
import math
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .nonlinear import (
    exponential_amplifier,
    continuous_opportunity_score,
    quadratic_ceiling,
    coverage_extension,
    s4_reduction_factor,
    calculate_price_deviation,
    estimate_order_amount,
    calculate_monto_maximo,
    stockout_probability,
    stockout_cost,
)

logger = logging.getLogger("AnalyticsEngine.Optimizer")


# ══════════════════════════════════════════════════════════════
# SQL QUERIES — v3.2 Market-Driven
# ══════════════════════════════════════════════════════════════

# Paso 1: Traer TODO lo disponible del mercado con stock, unido a los
# atributos del catálogo para poder agrupar por molécula.
SQL_MARKET_WITH_ATTRS = """
    SELECT
        mv.codigo_barras   AS codbarras,
        mv.descripcion_producto AS descripcion_mercado,
        mv.proveedor,
        mv.precio_unitario_final AS precio_unitario,
        mv.stock_disponible  AS stock_proveedor,
        pa.principio_activo,
        pa.forma_farmaceutica,
        pa.concentracion,
        pa.descrip1art       AS descripcion,
        ISNULL(pa.elasticidad_demanda, 1) AS elasticidad
    FROM Analitica.Mercado_Vivo_PDR mv
    INNER JOIN Procurement.por_aprobacion_equivalencias pa
        ON mv.codigo_barras = pa.codbarras
    WHERE mv.precio_unitario_final > 0
      AND mv.stock_disponible > 0
"""

# Paso 2: Para los grupos-molécula identificados, traer TODOS los SKUs del
# catálogo completo con su rotación y stock actual — esto incluye los que
# NO están en el mercado hoy.
SQL_CATALOG_FOR_GROUPS = """
    SELECT
        pa.codbarras,
        pa.descrip1art       AS descripcion,
        pa.principio_activo,
        pa.forma_farmaceutica,
        pa.concentracion,
        ISNULL(r.RotacionMensual, 0) AS rotacion_mensual,
        ISNULL(p.Existen, 0)         AS stock_actual,
        ISNULL(pa.elasticidad_demanda, 1) AS elasticidad
    FROM Procurement.por_aprobacion_equivalencias pa
    LEFT JOIN Procurement.Rotacion r ON pa.codbarras = r.CodItem
    LEFT JOIN SAPROD p ON pa.codbarras = p.CodProd
    WHERE pa.principio_activo IS NOT NULL
"""

SQL_HISTORICAL_PRICES = """
    SELECT
        codigo_barras    AS codbarras,
        AVG(precio_min)  AS media_min_historico,
        MIN(precio_min)  AS min_absoluto,
        AVG(precio_mediana) AS media_de_mediana,
        STDEV(precio_mediana) AS sigma_largo
    FROM Analitica.Mercado_Historico
    WHERE codigo_barras IN ({placeholders})
      AND fecha_snapshot >= DATEADD(DAY, -90, GETDATE())
    GROUP BY codigo_barras
"""

SQL_HISTORICAL_SHORT = """
    SELECT
        codigo_barras    AS codbarras,
        STDEV(precio_mediana) AS sigma_corto
    FROM Analitica.Mercado_Historico
    WHERE codigo_barras IN ({placeholders})
      AND fecha_snapshot >= DATEADD(DAY, -21, GETDATE())
    GROUP BY codigo_barras
"""

SQL_LEAD_TIME = """
    SELECT
        CodProv         AS codprov,
        DiaSemana       AS dia_semana,
        HoraCorte       AS hora_corte,
        HorasEntregaAnteCorte   AS horas_ante_corte,
        HorasEntregaDespuesCorte AS horas_despues_corte,
        AceptaPedidos   AS acepta_pedidos
    FROM Procurement.ProveedorHorarioEntrega
    WHERE AceptaPedidos = 1
"""


# ══════════════════════════════════════════════════════════════
# CAPA 1: AGRUPAMIENTO DESDE EL MERCADO (v3.2)
# ══════════════════════════════════════════════════════════════

def load_market_offers(cursor) -> pd.DataFrame:
    """Carga todas las ofertas del mercado vivo con atributos del catálogo.

    Solo trae productos que existen en el catálogo (INNER JOIN)
    y que tienen stock y precio > 0.
    """
    cursor.execute(SQL_MARKET_WITH_ATTRS)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    processed = []
    for row in rows:
        d = dict(zip(columns, row))
        for col in ["precio_unitario", "stock_proveedor", "elasticidad"]:
            if col in d and d[col] is not None:
                d[col] = float(d[col])
        processed.append(d)

    df = pd.DataFrame(processed)
    logger.info(f"Capa 1: {len(df)} ofertas cargadas del mercado vivo "
                f"({df['codbarras'].nunique()} SKUs únicos)")
    return df


def identify_molecule_groups(market_df: pd.DataFrame) -> pd.DataFrame:
    """Identifica los grupos-molécula únicos desde el mercado.

    Agrupa por (principio_activo, forma_farmaceutica, concentracion).
    Retorna un DataFrame con un row por grupo y métricas del mercado.
    """
    groups = market_df.groupby(
        ["principio_activo", "forma_farmaceutica", "concentracion"],
        dropna=False,
    ).agg(
        skus_mercado=("codbarras", "nunique"),
        ofertas_totales=("codbarras", "count"),
        proveedores_unicos=("proveedor", "nunique"),
        precio_min_mercado=("precio_unitario", "min"),
        precio_mediana_mercado=("precio_unitario", "median"),
    ).reset_index()

    logger.info(f"Capa 1: {len(groups)} grupos-molécula identificados en el mercado")
    return groups


def load_catalog_for_groups(cursor, groups_df: pd.DataFrame) -> pd.DataFrame:
    """Carga TODOS los SKUs del catálogo para los grupos-molécula identificados.

    Esto incluye SKUs que NO están en el mercado hoy — necesarios para
    calcular la rotación y el stock total del grupo.
    """
    cursor.execute(SQL_CATALOG_FOR_GROUPS)
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    processed = []
    for row in rows:
        d = dict(zip(columns, row))
        for col in ["rotacion_mensual", "stock_actual", "elasticidad"]:
            if col in d and d[col] is not None:
                d[col] = float(d[col])
        processed.append(d)

    catalog_df = pd.DataFrame(processed)

    # Filtrar solo los grupos-molécula que existen en el mercado
    if not catalog_df.empty and not groups_df.empty:
        merge_keys = ["principio_activo", "forma_farmaceutica", "concentracion"]
        catalog_df = catalog_df.merge(
            groups_df[merge_keys],
            on=merge_keys,
            how="inner",
        )

    logger.info(f"Capa 1: {len(catalog_df)} SKUs del catálogo mapeados a "
                f"{catalog_df[['principio_activo','forma_farmaceutica','concentracion']].drop_duplicates().shape[0]} "
                f"grupos-molécula")
    return catalog_df


# ══════════════════════════════════════════════════════════════
# CAPA 2: GAP GRUPAL (v3.2)
# ══════════════════════════════════════════════════════════════

def calculate_group_gaps(
    catalog_df: pd.DataFrame,
    dias_cobertura: int,
) -> pd.DataFrame:
    """Calcula el gap a nivel de grupo-molécula.

    Para cada grupo (PA, FF, Conc):
    - rotacion_grupo = SUM(rotacion_mensual / 30) de TODOS los SKUs
    - stock_grupo = SUM(stock_actual) de TODOS los SKUs
    - gap_grupo = (rotacion_grupo * dias_cobertura) - stock_grupo

    Retorna un DataFrame con una fila por grupo y sus métricas.
    """
    group_cols = ["principio_activo", "forma_farmaceutica", "concentracion"]

    catalog_df = catalog_df.copy()
    catalog_df["rotacion_diaria"] = catalog_df["rotacion_mensual"] / 30.0

    group_gaps = catalog_df.groupby(group_cols, dropna=False).agg(
        rotacion_diaria_grupo=("rotacion_diaria", "sum"),
        rotacion_mensual_grupo=("rotacion_mensual", "sum"),
        stock_actual_grupo=("stock_actual", "sum"),
        skus_catalogo=("codbarras", "nunique"),
    ).reset_index()

    group_gaps["necesidad_grupo"] = (
        group_gaps["rotacion_diaria_grupo"] * dias_cobertura
    )
    group_gaps["gap_grupo"] = (
        group_gaps["necesidad_grupo"] - group_gaps["stock_actual_grupo"]
    )

    positivos = (group_gaps["gap_grupo"] > 0).sum()
    negativos = (group_gaps["gap_grupo"] < 0).sum()
    cero = (group_gaps["gap_grupo"] == 0).sum()

    logger.info(
        f"Capa 2: Gaps GRUPALES calculados — "
        f"positivos={positivos} (necesitan compra), "
        f"negativos={negativos} (sobrestock), "
        f"cero={cero}"
    )
    return group_gaps


# ══════════════════════════════════════════════════════════════
# CAPA 2.1: S4 — REDUCCIÓN PARA COSTOSOS (sin cambio conceptual)
# ══════════════════════════════════════════════════════════════

def apply_s4_reduction(
    df: pd.DataFrame,
    s4_enabled: bool,
    porcentaje_base: float,
    dias_cobertura: int,
    historical_prices: pd.DataFrame,
    amplifier_params: tuple,
) -> pd.DataFrame:
    """Aplica reducción S4 no lineal a SKUs costosos con elasticidad=0."""
    if not s4_enabled:
        return df

    df = df.copy()
    mask = df["elasticidad"] == 0

    if not mask.any():
        return df

    for idx in df[mask].index:
        codbarras = df.loc[idx, "codbarras"]

        hist = historical_prices[historical_prices["codbarras"] == codbarras]
        if hist.empty or pd.isna(hist.iloc[0].get("media_de_mediana")):
            factor = porcentaje_base
        else:
            desvio = 0
            factor = s4_reduction_factor(desvio, porcentaje_base, amplifier_params)

        dias_ajustado = max(1, int(dias_cobertura * factor))
        rotacion_diaria = df.loc[idx, "rotacion_diaria"]
        nueva_necesidad = rotacion_diaria * dias_ajustado
        df.loc[idx, "gap_base"] = nueva_necesidad - df.loc[idx, "stock_actual"]
        df.loc[idx, "dias_ajustado_s4"] = dias_ajustado
        df.loc[idx, "factor_s4"] = factor

    n_affected = mask.sum()
    logger.info(f"Capa 2.1: S4 aplicado a {n_affected} SKUs con elasticidad=0")
    return df


# ══════════════════════════════════════════════════════════════
# CAPA 2.2: MONTOESTIMADO Y MONTOMAXIMO
# ══════════════════════════════════════════════════════════════

def calculate_budget(
    group_gaps: pd.DataFrame,
    market_df: pd.DataFrame,
    hist_df: pd.DataFrame,
    dias: int,
    buffer_pct: float,
    override: float = None,
) -> Tuple[float, float]:
    """Calcula MontoEstimado y MontoMaximo a nivel de grupo-molécula."""

    # Para cada grupo con gap > 0, estimar costo usando la mediana del mercado
    monto_est = 0.0
    for _, grp in group_gaps[group_gaps["gap_grupo"] > 0].iterrows():
        pa = grp["principio_activo"]
        ff = grp["forma_farmaceutica"]
        conc = grp["concentracion"]

        # Buscar precio mediana en el mercado para este grupo
        mask = (
            (market_df["principio_activo"] == pa) &
            (market_df["forma_farmaceutica"] == ff)
        )
        if pd.notna(conc):
            mask = mask & (market_df["concentracion"] == conc)
        else:
            mask = mask & (market_df["concentracion"].isna())

        group_market = market_df[mask]
        if not group_market.empty:
            precio_mediana = group_market["precio_unitario"].median()
        else:
            precio_mediana = 0.0

        monto_est += grp["gap_grupo"] * precio_mediana

    monto_max = calculate_monto_maximo(monto_est, buffer_pct, override)

    logger.info(f"Capa 2.2: MontoEstimado=${monto_est:.2f}, MontoMaximo=${monto_max:.2f}")
    return monto_est, monto_max


# ══════════════════════════════════════════════════════════════
# CAPA 3: SCORING — 5 FACTORES (opera por oferta del mercado)
# ══════════════════════════════════════════════════════════════

def score_elasticity(elasticidad: float, r2: float) -> float:
    """F1: Score de elasticidad/sustitución."""
    if r2 <= 0:
        return 0.5
    return min(elasticidad / max(r2, 1), 1.0)


def score_demand(rotacion_mensual: float, r2: float) -> float:
    """F2: Score de demanda (velocidad de rotación)."""
    if r2 <= 0:
        return 0.5
    return min(rotacion_mensual / max(r2, 0.01), 1.0)


def score_positioning(gap: float, necesidad: float) -> float:
    """F3: Score de posicionamiento (urgencia de stock)."""
    if necesidad <= 0:
        return 0.0
    return max(0, min(gap / necesidad, 1.0))


def score_opportunity(desvio: float, sigma: float, lambda_: float) -> float:
    """F4: Score de oportunidad de precio."""
    return continuous_opportunity_score(desvio, sigma, lambda_)


def score_coverage_ext(
    desvio: float,
    max_dias_extra: int,
    eta: float,
    umbral: float,
    dias_base: int,
) -> Tuple[float, int]:
    """F5: Extensión de cobertura por oportunidad."""
    dias_extra = coverage_extension(desvio, max_dias_extra, eta, umbral)
    # Score = dias_extra normalizado
    score = dias_extra / max(max_dias_extra, 1) if max_dias_extra > 0 else 0
    return score, dias_extra


# ══════════════════════════════════════════════════════════════
# CAPA 4: DISTRIBUCIÓN (opera dentro de cada grupo-molécula)
# ══════════════════════════════════════════════════════════════

def distribute_within_group(
    group_market_df: pd.DataFrame,
    gap_grupo: float,
    scores: pd.DataFrame,
    weights: Dict[str, float],
    monto_restante: float,
) -> pd.DataFrame:
    """Distribuye el gap de un grupo-molécula entre las ofertas del mercado.

    Elige las mejores ofertas según el score compuesto ponderado,
    respetando el monto máximo restante.
    """
    df = group_market_df.copy()
    w = weights

    if gap_grupo <= 0 or df.empty:
        df["cantidad"] = 0
        df["costo_linea"] = 0.0
        return df

    # Score compuesto ponderado
    df["score_compuesto"] = (
        scores["F1"] * w["w1"] +
        scores["F2"] * w["w2"] +
        scores["F3"] * w["w3"] +
        scores["F4"] * w["w4"] +
        scores["F5"] * w["w5"]
    )

    # Amplificador de cada oferta
    for idx in df.index:
        amp = scores.loc[idx, "amplificador"] if "amplificador" in scores.columns else 1.0
        dias_extra = scores.loc[idx, "dias_extra"] if "dias_extra" in scores.columns else 0

        rotacion_contrib = df.loc[idx, "rotacion_diaria_contrib"]
        cantidad_base = max(0, gap_grupo * amp * (rotacion_contrib / max(df["rotacion_diaria_contrib"].sum(), 0.001)))
        # Add extension days contribution
        if dias_extra > 0 and rotacion_contrib > 0:
            cantidad_base += rotacion_contrib * dias_extra

        df.loc[idx, "cantidad_raw"] = cantidad_base

    # Asignar la mejor oferta (menor precio) para cubrir el gap
    # Ordenar por score compuesto descendente (mejor primero)
    df = df.sort_values("score_compuesto", ascending=False)

    # Asignar cantidades priorizando el mejor score
    gap_restante = gap_grupo
    for idx in df.index:
        if gap_restante <= 0:
            df.loc[idx, "cantidad"] = 0
            df.loc[idx, "costo_linea"] = 0.0
            continue

        precio = df.loc[idx, "precio_unitario"]
        if pd.isna(precio) or precio <= 0:
            df.loc[idx, "cantidad"] = 0
            df.loc[idx, "costo_linea"] = 0.0
            continue

        stock_prov = df.loc[idx, "stock_proveedor"] or 0

        # Cantidad = lo menor entre lo que necesitamos, lo que tiene el proveedor,
        # y lo que el presupuesto permite
        cantidad_deseada = min(gap_restante, stock_prov)

        if monto_restante > 0:
            max_por_presupuesto = monto_restante / precio
            cantidad_deseada = min(cantidad_deseada, max_por_presupuesto)

        cantidad = max(0, int(round(cantidad_deseada)))
        costo = cantidad * precio

        df.loc[idx, "cantidad"] = cantidad
        df.loc[idx, "costo_linea"] = costo

        gap_restante -= cantidad
        monto_restante -= costo

    return df


# ══════════════════════════════════════════════════════════════
# CAPA 5: SPLIT POR LEAD TIME
# ══════════════════════════════════════════════════════════════

def apply_lead_time_split(
    df: pd.DataFrame,
    lead_times: pd.DataFrame,
) -> pd.DataFrame:
    """Aplica costos de stockout basados en lead time del proveedor."""
    now = datetime.now()
    dia_semana = now.isoweekday()
    hora_actual = now.hour * 100 + now.minute

    df = df.copy()

    for idx in df.index:
        prov = df.loc[idx, "proveedor"]
        lt = lead_times[
            (lead_times["codprov"] == prov) &
            (lead_times["dia_semana"] == dia_semana)
        ]

        if lt.empty:
            df.loc[idx, "lead_time_horas"] = 48
        else:
            lt_row = lt.iloc[0]
            hora_corte = lt_row["hora_corte"]
            if hora_corte is not None:
                corte_minutos = hora_corte.hour * 100 + hora_corte.minute if hasattr(hora_corte, 'hour') else 0
                if hora_actual < corte_minutos:
                    df.loc[idx, "lead_time_horas"] = lt_row["horas_ante_corte"] or 24
                else:
                    df.loc[idx, "lead_time_horas"] = lt_row["horas_despues_corte"] or 48
            else:
                df.loc[idx, "lead_time_horas"] = lt_row["horas_ante_corte"] or 24

    # Calcular probabilidad de stockout
    for idx in df.index:
        rot = df.loc[idx, "rotacion_diaria_contrib"] if "rotacion_diaria_contrib" in df.columns else 0
        lt_dias = df.loc[idx, "lead_time_horas"] / 24.0
        stock = df.loc[idx, "stock_proveedor"] if "stock_proveedor" in df.columns else 0

        prob = stockout_probability(rot, lt_dias, int(stock)) if rot > 0 else 0
        df.loc[idx, "prob_stockout"] = prob

        precio = df.loc[idx, "precio_unitario"]
        margen = precio * 0.30 if precio and precio > 0 else 0
        costo = stockout_cost(prob, rot, lt_dias, margen) if prob > 0 else 0
        df.loc[idx, "costo_stockout"] = costo

    return df


# ══════════════════════════════════════════════════════════════
# CAPA 6: JUSTIFICACIÓN TEXTUAL
# ══════════════════════════════════════════════════════════════

def build_justification(row: pd.Series, scores_row: pd.Series) -> str:
    """Genera justificación textual para una línea del pedido."""
    parts = []

    gap = row.get("gap_grupo", 0)
    if gap > 0:
        parts.append(f"Grupo necesita reposición: gap grupal de {gap:.0f} unidades")

    desvio = row.get("desvio_precio", 0)
    if desvio < -0.10:
        parts.append(f"OPORTUNIDAD: precio {abs(desvio)*100:.0f}% bajo la media histórica")
    elif desvio > 0.10:
        parts.append(f"PRECAUCIÓN: precio {desvio*100:.0f}% sobre la media histórica")

    amp = scores_row.get("amplificador", 1.0)
    if amp > 1.1:
        parts.append(f"Amplificador: {amp:.1f}x por oportunidad de precio")
    elif amp < 0.9:
        parts.append(f"Reducido a {amp:.1f}x por precio alto")

    if row.get("factor_s4") is not None:
        factor = row["factor_s4"]
        if factor < 1.0:
            parts.append(f"S4: cobertura reducida al {factor*100:.0f}% (costoso, elast=0)")

    dias_extra = scores_row.get("dias_extra", 0)
    if dias_extra > 0:
        parts.append(f"+{dias_extra} días extra de cobertura por oportunidad")

    prob = row.get("prob_stockout", 0)
    if prob > 0.5:
        parts.append(f"ALERTA: {prob*100:.0f}% probabilidad de quiebre durante despacho")

    return ". ".join(parts) if parts else "Pedido estándar sin ajustes especiales"


# ══════════════════════════════════════════════════════════════
# ORQUESTADOR PRINCIPAL — v3.2 Market-Driven
# ══════════════════════════════════════════════════════════════

def run_optimization(request_data: dict) -> dict:
    """Ejecuta el pipeline completo de optimización v3.2.

    Flujo:
    1. Leer mercado vivo → agrupar por (PA, FF, Concentración) = Moléculas
    2. Para cada molécula, buscar TODOS los SKUs del catálogo
    3. Sumar rotación y stock del catálogo completo → Gap Grupal
    4. Si Gap > 0 → distribuir compra entre ofertas del mercado
    5. Aplicar factores, MontoMaximo, lead time, justificación
    """
    from .db import db_cursor, query_dataframe

    # Si viene en formato legacy, adaptar
    if "items" in request_data and "constraints" in request_data:
        logger.info("Formato legacy detectado — ejecutando placeholder")
        return _legacy_optimization(request_data)

    # ── CARGAR CONFIGURACIÓN DESDE BD ──
    config_df = query_dataframe(
        "SELECT TOP 1 * FROM Procurement.OptimizerConfig WHERE is_active = 1 ORDER BY id DESC"
    )
    if not config_df.empty:
        c = config_df.iloc[0]
        if "pesos" not in request_data:
            request_data["pesos"] = {
                "w1_elasticidad": float(c["w1_elasticidad"]),
                "w2_demanda": float(c["w2_demanda"]),
                "w3_posicionamiento": float(c["w3_posicionamiento"]),
                "w4_oportunidad": float(c["w4_oportunidad"]),
                "w5_extension": float(c["w5_extension"]),
            }
        if "amplifier" not in request_data:
            request_data["amplifier"] = {
                "a": float(c["amp_a"]),
                "b": float(c["amp_b"]),
                "max_increment_pct": float(c["amp_max_increment_pct"]),
                "floor_pct": float(c["amp_floor_pct"]),
            }
        if "s4" not in request_data:
            request_data["s4"] = {
                "enabled": bool(c["s4_enabled"]),
                "porcentaje_base": float(c["s4_porcentaje_base"]),
            }
        if "monto_maximo" not in request_data:
            request_data["monto_maximo"] = {
                "buffer_pct": float(c["monto_buffer_pct"]),
                "days_reduction_pct": float(c["monto_days_reduction_pct"]),
            }
        if "extension" not in request_data:
            request_data["extension"] = {
                "max_dias_extra": int(c["ext_max_dias_extra"]),
                "umbral_extension": float(c["ext_umbral"]),
                "eta": float(c["ext_eta"]),
            }
        if "sustitucion" not in request_data:
            request_data["sustitucion"] = {
                "kappa": float(c["sust_kappa"]),
            }
        if "opportunity_score" not in request_data:
            request_data["opportunity_score"] = {
                "lambda_sensitivity": float(c["opp_lambda"]),
            }
        logger.info(f"Configuración cargada desde BD: perfil '{c['profile_name']}'")

    # Parsear request
    from ..models.optimization import OptimizationRequestV2, OptimizationResult, OrderLine

    req = OptimizationRequestV2(**request_data)
    logger.info(f"Optimización v3.2 Market-Driven: {req.dias_cobertura} días")

    # ══════════════════════════════════════════════════════════
    # PASO 1: Cargar mercado vivo y agrupar por molécula
    # ══════════════════════════════════════════════════════════
    with db_cursor() as cursor:
        market_df = load_market_offers(cursor)

    if market_df.empty:
        return OptimizationResult(
            grupo="Mercado Vivo (sin ofertas)",
            dias_cobertura=req.dias_cobertura,
            monto_estimado_bs=0,
            monto_maximo_bs=0,
            buffer_pct=req.monto_maximo.buffer_pct,
            monto_total_pedido_bs=0,
            pesos=req.pesos.normalized(),
            lineas=[],
        ).model_dump()

    molecule_groups = identify_molecule_groups(market_df)

    # ══════════════════════════════════════════════════════════
    # PASO 2: Cargar catálogo completo para calcular gap grupal
    # ══════════════════════════════════════════════════════════
    with db_cursor() as cursor:
        catalog_df = load_catalog_for_groups(cursor, molecule_groups)

    # ══════════════════════════════════════════════════════════
    # PASO 3: Calcular Gap Grupal
    # ══════════════════════════════════════════════════════════
    group_gaps = calculate_group_gaps(catalog_df, req.dias_cobertura)

    # Solo procesar grupos con gap positivo (necesitan compra)
    groups_to_buy = group_gaps[group_gaps["gap_grupo"] > 0].copy()
    logger.info(f"Paso 3: {len(groups_to_buy)} grupos-molécula necesitan compra")

    if groups_to_buy.empty:
        return OptimizationResult(
            grupo="Mercado Vivo (todo cubierto)",
            dias_cobertura=req.dias_cobertura,
            monto_estimado_bs=0,
            monto_maximo_bs=0,
            buffer_pct=req.monto_maximo.buffer_pct,
            monto_total_pedido_bs=0,
            pesos=req.pesos.normalized(),
            lineas=[],
            total_skus_procesados=len(catalog_df),
            r2_dinamica_grupo=catalog_df["rotacion_mensual"].sum(),
        ).model_dump()

    # ══════════════════════════════════════════════════════════
    # Datos históricos de precio (para F4 y amplificador)
    # ══════════════════════════════════════════════════════════
    codbarras_market = market_df["codbarras"].unique().tolist()
    hist_dfs = []
    chunk_size = 2000
    for i in range(0, len(codbarras_market), chunk_size):
        chunk = codbarras_market[i:i + chunk_size]
        placeholders = ",".join(["?"] * len(chunk))
        chunk_hist = query_dataframe(
            SQL_HISTORICAL_PRICES.format(placeholders=placeholders),
            chunk,
        )
        hist_dfs.append(chunk_hist)

    hist_df = pd.concat(hist_dfs, ignore_index=True) if hist_dfs else pd.DataFrame()

    lead_times = query_dataframe(SQL_LEAD_TIME)

    # ══════════════════════════════════════════════════════════
    # PASO 4: Budget (MontoEstimado y MontoMaximo)
    # ══════════════════════════════════════════════════════════
    monto_est, monto_max = calculate_budget(
        group_gaps, market_df, hist_df,
        req.dias_cobertura, req.monto_maximo.buffer_pct,
        req.monto_maximo.monto_maximo_override,
    )

    # ══════════════════════════════════════════════════════════
    # PASO 5: Scoring + Distribución por grupo-molécula
    # ══════════════════════════════════════════════════════════
    weights = req.pesos.normalized()
    all_order_lines = []
    monto_restante = monto_max
    r2_total = catalog_df["rotacion_mensual"].sum()

    for _, grp in groups_to_buy.iterrows():
        pa = grp["principio_activo"]
        ff = grp["forma_farmaceutica"]
        conc = grp["concentracion"]
        gap_grupo = grp["gap_grupo"]
        rot_grupo = grp["rotacion_diaria_grupo"]

        if monto_restante <= 0:
            break

        # Filtrar ofertas del mercado para este grupo
        mask = (
            (market_df["principio_activo"] == pa) &
            (market_df["forma_farmaceutica"] == ff)
        )
        if pd.notna(conc):
            mask = mask & (market_df["concentracion"] == conc)
        else:
            mask = mask & (market_df["concentracion"].isna())

        group_offers = market_df[mask].copy()
        if group_offers.empty:
            continue

        # Agregar info de rotación proporcional a cada oferta
        # Cada SKU contribuye proporcionalmente a la rotación del grupo
        for idx in group_offers.index:
            cb = group_offers.loc[idx, "codbarras"]
            cat_match = catalog_df[catalog_df["codbarras"] == cb]
            if not cat_match.empty:
                group_offers.loc[idx, "rotacion_diaria_contrib"] = (
                    cat_match.iloc[0]["rotacion_mensual"] / 30.0
                )
                group_offers.loc[idx, "stock_actual"] = cat_match.iloc[0]["stock_actual"]
            else:
                group_offers.loc[idx, "rotacion_diaria_contrib"] = 0
                group_offers.loc[idx, "stock_actual"] = 0

        group_offers["gap_grupo"] = gap_grupo

        # Calcular scores para cada oferta
        scores = pd.DataFrame(index=group_offers.index)
        for idx in group_offers.index:
            codbarras = group_offers.loc[idx, "codbarras"]

            # F1: Elasticidad
            scores.loc[idx, "F1"] = score_elasticity(
                group_offers.loc[idx, "elasticidad"], r2_total
            )

            # F2: Demanda
            rot_contrib = group_offers.loc[idx, "rotacion_diaria_contrib"]
            scores.loc[idx, "F2"] = score_demand(
                rot_contrib * 30, rot_grupo * 30 if rot_grupo > 0 else 1
            )

            # F3: Posicionamiento
            scores.loc[idx, "F3"] = score_positioning(
                gap_grupo, grp["necesidad_grupo"]
            )

            # Desvío de precio para F4 y F5
            hist = hist_df[hist_df["codbarras"] == codbarras] if not hist_df.empty else pd.DataFrame()
            if not hist.empty and not pd.isna(hist.iloc[0].get("media_de_mediana")):
                media_med = hist.iloc[0]["media_de_mediana"]
                sigma_l = hist.iloc[0].get("sigma_largo", 0) or 0
                precio_actual = group_offers.loc[idx, "precio_unitario"]
                desvio = calculate_price_deviation(precio_actual, media_med)
            else:
                desvio = 0
                sigma_l = 0
                media_med = 0

            group_offers.loc[idx, "desvio_precio"] = desvio
            group_offers.loc[idx, "media_de_mediana"] = media_med

            # F4: Oportunidad
            scores.loc[idx, "F4"] = score_opportunity(
                desvio, sigma_l, req.opportunity_score.lambda_sensitivity
            )

            # Amplificador
            scores.loc[idx, "amplificador"] = exponential_amplifier(
                desvio, req.amplifier.a, req.amplifier.b,
                req.amplifier.max_increment_pct, req.amplifier.floor_pct,
            )

            # F5: Extensión
            f5_score, dias_extra = score_coverage_ext(
                desvio, req.extension.max_dias_extra,
                req.extension.eta, req.extension.umbral_extension,
                req.dias_cobertura,
            )
            scores.loc[idx, "F5"] = f5_score
            scores.loc[idx, "dias_extra"] = dias_extra

            # Precio histórico
            if not hist.empty:
                group_offers.loc[idx, "media_min_historico"] = hist.iloc[0].get("media_min_historico")
                group_offers.loc[idx, "min_absoluto"] = hist.iloc[0].get("min_absoluto")

        # Distribuir gap del grupo entre las ofertas
        group_result = distribute_within_group(
            group_offers, gap_grupo, scores, weights, monto_restante,
        )

        # Aplicar lead time
        group_result = apply_lead_time_split(group_result, lead_times)

        # Generar líneas de pedido
        for idx in group_result.index:
            cantidad = int(group_result.loc[idx, "cantidad"])
            if cantidad <= 0:
                continue

            justificacion = build_justification(group_result.loc[idx], scores.loc[idx])

            linea = OrderLine(
                codbarras=group_result.loc[idx, "codbarras"],
                descripcion=group_result.loc[idx, "descripcion"],
                codprod=None,
                proveedor=group_result.loc[idx, "proveedor"],
                cantidad=cantidad,
                precio_unitario=float(group_result.loc[idx, "precio_unitario"]),
                costo_total=float(group_result.loc[idx, "costo_linea"]),
                media_min_historico_sku=group_result.loc[idx].get("media_min_historico"),
                min_absoluto_sku=group_result.loc[idx].get("min_absoluto"),
                media_de_mediana_sku=group_result.loc[idx].get("media_de_mediana"),
                precio_mediana_actual_sku=float(
                    group_offers[group_offers["codbarras"] == group_result.loc[idx, "codbarras"]]["precio_unitario"].median()
                ) if not group_offers[group_offers["codbarras"] == group_result.loc[idx, "codbarras"]].empty else None,
                gap_base=float(gap_grupo),
                desvio_precio_pct=float(group_result.loc[idx].get("desvio_precio", 0)) * 100,
                score_oportunidad=float(scores.loc[idx, "F4"]),
                amplificador_aplicado=float(scores.loc[idx, "amplificador"]),
                dias_extra_aplicados=int(scores.loc[idx, "dias_extra"]),
                factores_detalle={
                    "F1_elasticidad": float(scores.loc[idx, "F1"]),
                    "F2_demanda": float(scores.loc[idx, "F2"]),
                    "F3_posicionamiento": float(scores.loc[idx, "F3"]),
                    "F4_oportunidad": float(scores.loc[idx, "F4"]),
                    "F5_extension": float(scores.loc[idx, "F5"]),
                },
                justificacion=justificacion,
            )
            all_order_lines.append(linea)
            monto_restante -= linea.costo_total

    # ══════════════════════════════════════════════════════════
    # RESULTADO FINAL
    # ══════════════════════════════════════════════════════════
    monto_total = sum(l.costo_total for l in all_order_lines)
    monto_sobrestock = max(0, monto_total - monto_est)

    # Ahorro vs media_min_historico
    ahorro_pct = 0.0
    costo_a_media_min = sum(
        l.cantidad * (l.media_min_historico_sku or l.precio_unitario)
        for l in all_order_lines
    )
    if costo_a_media_min > 0:
        ahorro_pct = ((costo_a_media_min - monto_total) / costo_a_media_min) * 100

    justificacion_sobrestock = None
    if monto_sobrestock > 0:
        justificacion_sobrestock = (
            f"Sobrecompra de ${monto_sobrestock:.2f} justificada por oportunidades de precio. "
            f"Ahorro estimado vs precio mínimo histórico: {ahorro_pct:.1f}%."
        )

    proveedores = set(l.proveedor for l in all_order_lines)

    result = OptimizationResult(
        grupo=f"Pedido Moléculas Market-Driven ({len(groups_to_buy)} grupos)",
        dias_cobertura=req.dias_cobertura,
        monto_estimado_bs=monto_est,
        monto_maximo_bs=monto_max,
        buffer_pct=req.monto_maximo.buffer_pct,
        monto_total_pedido_bs=monto_total,
        monto_sobrestock_oportunidad_bs=monto_sobrestock,
        ahorro_vs_media_min_historico_pct=round(ahorro_pct, 2),
        justificacion_sobrestock=justificacion_sobrestock,
        excede_monto_maximo=monto_total > monto_max,
        pesos=weights,
        lineas=all_order_lines,
        total_skus_procesados=len(catalog_df),
        total_proveedores_involucrados=len(proveedores),
        r2_dinamica_grupo=r2_total,
        pedido_total_grupo_unidades=sum(l.cantidad for l in all_order_lines),
    )

    logger.info(
        f"Optimización v3.2 completada: {len(all_order_lines)} líneas, "
        f"${monto_total:.2f} total, {len(proveedores)} proveedores, "
        f"{len(groups_to_buy)} grupos-molécula"
    )

    return result.model_dump()


def _legacy_optimization(data: dict) -> dict:
    """Mantiene compatibilidad con el endpoint legacy."""
    items = data.get("items", [])
    df = pd.DataFrame(items) if items else pd.DataFrame()

    decisions = []
    if not df.empty:
        for _, row in df.iterrows():
            decisions.append({
                "item_id": row.get("id"),
                "suggested_quantity": 10,
                "reasoning": "Placeholder logic — use v2 endpoint for real optimization",
            })

    return {
        "status": "success",
        "decisions": decisions,
        "metrics": {
            "processed_items": len(items),
            "solver": "legacy_placeholder",
        },
    }
