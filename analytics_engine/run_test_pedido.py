"""
Test del motor de optimización v3.2 — Ejecutado via MCP queries
================================================================
Como el servidor SQL no es accesible directamente desde Python/pyodbc
en esta máquina, este script espera los DataFrames ya cargados como CSV.

Uso:
  1. El agente extrae los datos via MCP y los guarda como CSV
  2. Este script carga los CSV y ejecuta la lógica del motor
"""
import sys
import os
import json
import logging
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("TestPedido_v3.2")

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_data")


def load_data():
    """Carga los datos pre-extraídos via MCP."""
    market_df = pd.read_csv(os.path.join(DATA_DIR, "market_offers.csv"))
    catalog_df = pd.read_csv(os.path.join(DATA_DIR, "catalog_groups.csv"))
    hist_df_path = os.path.join(DATA_DIR, "historical_prices.csv")
    hist_df = pd.read_csv(hist_df_path) if os.path.exists(hist_df_path) else pd.DataFrame()
    lead_times_path = os.path.join(DATA_DIR, "lead_times.csv")
    lead_times = pd.read_csv(lead_times_path) if os.path.exists(lead_times_path) else pd.DataFrame()
    return market_df, catalog_df, hist_df, lead_times


def run_v32_offline(market_df, catalog_df, hist_df, lead_times, dias_cobertura=30):
    """Ejecuta la lógica del motor v3.2 offline con datos pre-cargados."""
    from analytics_engine.core.optimizer import (
        identify_molecule_groups,
        calculate_group_gaps,
        calculate_budget,
        score_elasticity,
        score_demand,
        score_positioning,
        score_opportunity,
        score_coverage_ext,
        distribute_within_group,
        build_justification,
    )
    from analytics_engine.core.nonlinear import (
        exponential_amplifier,
        calculate_price_deviation,
        calculate_monto_maximo,
    )
    from analytics_engine.models.optimization import OptimizationResult, OrderLine

    # Parámetros
    weights = {"w1": 0.15, "w2": 0.25, "w3": 0.25, "w4": 0.20, "w5": 0.15}
    amp_a, amp_b = 5.84, 1.29
    amp_max = 500.0
    amp_floor = 0.2
    buffer_pct = 20.0
    lambda_sens = 1.0
    max_dias_extra = 21
    eta = 4.0
    umbral_ext = -0.10

    # ── Paso 1: Enriquecer mercado con atributos del catálogo ──
    # El CSV del mercado solo tiene codbarras — necesitamos PA, FF, Conc del catálogo
    catalog_attrs = catalog_df[["codbarras", "principio_activo", "forma_farmaceutica",
                                 "concentracion", "descripcion", "elasticidad"]].copy()
    catalog_attrs["codbarras"] = catalog_attrs["codbarras"].astype(str)
    market_df["codbarras"] = market_df["codbarras"].astype(str)

    market_df = market_df.merge(catalog_attrs, on="codbarras", how="inner")
    logger.info(f"Mercado enriquecido con atributos: {len(market_df)} ofertas "
                f"({market_df['codbarras'].nunique()} SKUs con match en catálogo)")

    # ── Paso 2: Grupos molécula ──
    molecule_groups = identify_molecule_groups(market_df)
    logger.info(f"Grupos molécula identificados: {len(molecule_groups)}")

    # ── Paso 2: Filtrar catálogo a los grupos del mercado ──
    merge_keys = ["principio_activo", "forma_farmaceutica", "concentracion"]

    # Convertir tipos para merge (pueden ser str o int según el CSV)
    for col in merge_keys:
        if col in catalog_df.columns:
            catalog_df[col] = catalog_df[col].astype(str)
        if col in molecule_groups.columns:
            molecule_groups[col] = molecule_groups[col].astype(str)
        if col in market_df.columns:
            market_df[col] = market_df[col].astype(str)

    catalog_filtered = catalog_df.merge(
        molecule_groups[merge_keys],
        on=merge_keys,
        how="inner",
    )
    logger.info(f"Catálogo filtrado a grupos del mercado: {len(catalog_filtered)} SKUs")

    # ── Paso 3: Gap grupal ──
    group_gaps = calculate_group_gaps(catalog_filtered, dias_cobertura)
    groups_to_buy = group_gaps[group_gaps["gap_grupo"] > 0].copy()
    logger.info(f"Grupos que necesitan compra: {len(groups_to_buy)}")

    # ── Paso 4: Budget ──
    monto_est, monto_max = calculate_budget(
        group_gaps, market_df, hist_df, dias_cobertura, buffer_pct,
    )

    # ── Paso 5: Scoring + Distribución ──
    all_order_lines = []
    monto_restante = monto_max
    r2_total = catalog_filtered["rotacion_mensual"].sum() if "rotacion_mensual" in catalog_filtered.columns else 1

    for _, grp in groups_to_buy.iterrows():
        pa = str(grp["principio_activo"])
        ff = str(grp["forma_farmaceutica"])
        conc = str(grp["concentracion"])
        gap_grupo = grp["gap_grupo"]
        rot_grupo = grp["rotacion_diaria_grupo"]

        if monto_restante <= 0:
            break

        # Filtrar ofertas del mercado
        mask = (market_df["principio_activo"] == pa) & (market_df["forma_farmaceutica"] == ff)
        if conc != "nan" and conc != "None":
            mask = mask & (market_df["concentracion"] == conc)

        group_offers = market_df[mask].copy()
        if group_offers.empty:
            continue

        # Agregar rotación proporcional
        for idx in group_offers.index:
            cb = str(group_offers.loc[idx, "codbarras"])
            cat_match = catalog_filtered[catalog_filtered["codbarras"].astype(str) == cb]
            if not cat_match.empty:
                group_offers.loc[idx, "rotacion_diaria_contrib"] = (
                    cat_match.iloc[0]["rotacion_mensual"] / 30.0
                )
                group_offers.loc[idx, "stock_actual"] = cat_match.iloc[0]["stock_actual"]
            else:
                group_offers.loc[idx, "rotacion_diaria_contrib"] = 0
                group_offers.loc[idx, "stock_actual"] = 0

        group_offers["gap_grupo"] = gap_grupo

        # Scores
        scores = pd.DataFrame(index=group_offers.index)
        for idx in group_offers.index:
            codbarras = str(group_offers.loc[idx, "codbarras"])

            scores.loc[idx, "F1"] = score_elasticity(
                group_offers.loc[idx, "elasticidad"], r2_total
            )
            rot_c = group_offers.loc[idx, "rotacion_diaria_contrib"]
            scores.loc[idx, "F2"] = score_demand(
                rot_c * 30, rot_grupo * 30 if rot_grupo > 0 else 1
            )
            scores.loc[idx, "F3"] = score_positioning(
                gap_grupo, grp["necesidad_grupo"]
            )

            # Desvío
            hist = hist_df[hist_df["codbarras"].astype(str) == codbarras] if not hist_df.empty else pd.DataFrame()
            if not hist.empty and pd.notna(hist.iloc[0].get("media_de_mediana")):
                media_med = hist.iloc[0]["media_de_mediana"]
                sigma_l = hist.iloc[0].get("sigma_largo", 0) or 0
                precio_act = group_offers.loc[idx, "precio_unitario"]
                desvio = calculate_price_deviation(precio_act, media_med)
            else:
                desvio = 0
                sigma_l = 0
                media_med = 0

            group_offers.loc[idx, "desvio_precio"] = desvio
            group_offers.loc[idx, "media_de_mediana"] = media_med

            scores.loc[idx, "F4"] = score_opportunity(desvio, sigma_l, lambda_sens)
            scores.loc[idx, "amplificador"] = exponential_amplifier(
                desvio, amp_a, amp_b, amp_max, amp_floor,
            )
            f5_score, dias_extra = score_coverage_ext(
                desvio, max_dias_extra, eta, umbral_ext, dias_cobertura,
            )
            scores.loc[idx, "F5"] = f5_score
            scores.loc[idx, "dias_extra"] = dias_extra

            if not hist.empty:
                group_offers.loc[idx, "media_min_historico"] = hist.iloc[0].get("media_min_historico")
                group_offers.loc[idx, "min_absoluto"] = hist.iloc[0].get("min_absoluto")

        # Distribuir
        group_result = distribute_within_group(
            group_offers, gap_grupo, scores, weights, monto_restante,
        )

        for idx in group_result.index:
            cantidad = int(group_result.loc[idx, "cantidad"])
            if cantidad <= 0:
                continue

            justificacion = build_justification(group_result.loc[idx], scores.loc[idx])

            linea = OrderLine(
                codbarras=str(group_result.loc[idx, "codbarras"]),
                descripcion=str(group_result.loc[idx, "descripcion"]),
                proveedor=str(group_result.loc[idx, "proveedor"]),
                cantidad=cantidad,
                precio_unitario=float(group_result.loc[idx, "precio_unitario"]),
                costo_total=float(group_result.loc[idx, "costo_linea"]),
                media_min_historico_sku=group_result.loc[idx].get("media_min_historico"),
                min_absoluto_sku=group_result.loc[idx].get("min_absoluto"),
                media_de_mediana_sku=group_result.loc[idx].get("media_de_mediana"),
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

    # Resultado
    monto_total = sum(l.costo_total for l in all_order_lines)
    return {
        "monto_estimado_usd": monto_est,
        "monto_maximo_usd": monto_max,
        "monto_total_pedido_usd": monto_total,
        "total_lineas": len(all_order_lines),
        "total_unidades": sum(l.cantidad for l in all_order_lines),
        "total_grupos_compra": len(groups_to_buy),
        "total_skus_catalogo": len(catalog_filtered),
        "lineas": [l.model_dump() for l in all_order_lines],
    }


def main():
    logger.info("=" * 60)
    logger.info("MOTOR v3.2 — MARKET-DRIVEN (Offline Mode)")
    logger.info("=" * 60)

    market_df, catalog_df, hist_df, lead_times = load_data()

    logger.info(f"Mercado: {len(market_df)} ofertas, {market_df['codbarras'].nunique()} SKUs")
    logger.info(f"Catálogo: {len(catalog_df)} SKUs")
    logger.info(f"Histórico: {len(hist_df)} registros")

    result = run_v32_offline(market_df, catalog_df, hist_df, lead_times, dias_cobertura=30)

    logger.info("=" * 60)
    logger.info("RESULTADOS v3.2")
    logger.info("=" * 60)
    logger.info(f"  Monto Estimado:      ${result['monto_estimado_usd']:,.2f}")
    logger.info(f"  Monto Máximo:        ${result['monto_maximo_usd']:,.2f}")
    logger.info(f"  Monto Total Pedido:  ${result['monto_total_pedido_usd']:,.2f}")
    logger.info(f"  Total líneas:        {result['total_lineas']}")
    logger.info(f"  Total unidades:      {result['total_unidades']}")
    logger.info(f"  Grupos con compra:   {result['total_grupos_compra']}")

    if result["lineas"]:
        lineas_sorted = sorted(result["lineas"], key=lambda x: x["costo_total"], reverse=True)
        logger.info("\n  TOP 10 líneas más costosas:")
        for i, l in enumerate(lineas_sorted[:10]):
            logger.info(
                f"    {i+1}. {str(l['descripcion'])[:40]:40s} | "
                f"Prov: {str(l['proveedor'])[:15]:15s} | "
                f"Cant: {l['cantidad']:5d} | "
                f"P/U: ${l['precio_unitario']:8.2f} | "
                f"Total: ${l['costo_total']:10.2f}"
            )

        # Excel
        df_out = pd.DataFrame(result["lineas"])
        output_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "Pedido_Moleculas_v3.2_30Dias.xlsx"
        )
        df_out.to_excel(output_path, index=False, sheet_name="Pedido_v3.2")
        logger.info(f"\n  Excel generado: {output_path}")

    # JSON
    json_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "resultado_v3.2.json"
    )
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    logger.info(f"  JSON generado: {json_path}")


if __name__ == "__main__":
    main()
