"""PedidoBaseline — legacy rotation need without the optimizer motor."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

import pandas as pd


@dataclass(frozen=True)
class BaselineLine:
    barra: str
    descripcion: str
    cantidad: int


@dataclass(frozen=True)
class FiltrosOperativos:
    categorias: Optional[Sequence[str]] = None
    include_generics: bool = True
    include_brands: bool = True
    umbral_rotacion: float = 0.0
    num_rows: int = 5000


def compute_pedido_baseline(
    catalog: pd.DataFrame,
    cobertura_dias: float,
    filtros: FiltrosOperativos,
    criterios_agrupacion: Optional[Sequence[str]] = None,
) -> List[BaselineLine]:
    """Compute PedidoBaseline: rotacion × cobertura/30 − stock.

    No PriceOpportunity, pesos, SplitLeadTime, or F5.
    """
    if catalog.empty:
        return []

    df = catalog.copy()
    required = {"barra", "descripcion", "rotacion_mensual", "existen"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"catalog missing columns: {sorted(missing)}")

    df["barra"] = df["barra"].astype(str)
    df["descripcion"] = df["descripcion"].fillna("").astype(str)
    df["rotacion_mensual"] = pd.to_numeric(df["rotacion_mensual"], errors="coerce").fillna(0.0)
    df["existen"] = pd.to_numeric(df["existen"], errors="coerce").fillna(0.0)

    df = _apply_filtros_tipo(df, filtros)
    df = _apply_filtros_categoria(df, filtros)

    rot = df["rotacion_mensual"]
    stock = df["existen"]
    if criterios_agrupacion:
        attrs = list(criterios_agrupacion)
        missing_attrs = [a for a in attrs if a not in df.columns]
        if missing_attrs:
            raise ValueError(
                f"catalog missing CriteriosAgrupacion columns: {missing_attrs}"
            )
        # Drop attrs that are blank for the entire catalog (no discriminative power).
        attrs = [
            a
            for a in attrs
            if df[a].fillna("").astype(str).str.strip().ne("").any()
        ]
        if attrs:
            for a in attrs:
                df[a] = df[a].fillna("").astype(str).str.strip()
            # Rows without MDM must not share one empty mega-key (stock_sum ≫ rot).
            blank_rows = True
            for a in attrs:
                blank_rows = blank_rows & df[a].eq("")
            df["_grp_key"] = [
                ("__sku__", b) if blank else tuple(vals)
                for blank, b, vals in zip(
                    blank_rows.tolist(),
                    df["barra"].tolist(),
                    df[attrs].itertuples(index=False, name=None),
                )
            ]
            grouped = (
                df.groupby("_grp_key", dropna=False)[["rotacion_mensual", "existen"]]
                .sum()
                .reset_index()
                .rename(
                    columns={
                        "rotacion_mensual": "_rot_grupo",
                        "existen": "_stock_grupo",
                    }
                )
            )
            df = df.merge(grouped, on="_grp_key", how="left")
            rot = df["_rot_grupo"].fillna(df["rotacion_mensual"])
            stock = df["_stock_grupo"].fillna(df["existen"])

    df = df.assign(_rot_eff=rot, _stock_eff=stock)
    df["cantidad"] = (df["_rot_eff"] * float(cobertura_dias) / 30.0 - df["_stock_eff"]).round().astype(int)

    # Umbral uses effective rotation (group-aware when criterios apply)
    df = df[df["_rot_eff"] >= float(filtros.umbral_rotacion)]
    df = df[df["cantidad"] > 0]
    df = df.drop_duplicates(subset=["barra"])
    limit = int(filtros.num_rows) if filtros.num_rows > 0 else 5000
    df = df.head(limit)

    out: List[BaselineLine] = []
    for barra, descripcion, cantidad in zip(
        df["barra"].tolist(),
        df["descripcion"].tolist(),
        df["cantidad"].tolist(),
    ):
        out.append(
            BaselineLine(
                barra=str(barra),
                descripcion=str(descripcion),
                cantidad=int(cantidad),
            )
        )
    return out


def _apply_filtros_tipo(df: pd.DataFrame, filtros: FiltrosOperativos) -> pd.DataFrame:
    if filtros.include_generics and filtros.include_brands:
        return df
    if not filtros.include_generics and not filtros.include_brands:
        return df.iloc[0:0]
    if "es_generico" not in df.columns:
        return df
    if filtros.include_generics and not filtros.include_brands:
        return df[df["es_generico"] == True]  # noqa: E712
    if filtros.include_brands and not filtros.include_generics:
        return df[df["es_generico"] == False]  # noqa: E712
    return df


def _apply_filtros_categoria(df: pd.DataFrame, filtros: FiltrosOperativos) -> pd.DataFrame:
    if not filtros.categorias:
        return df
    if "categoria" not in df.columns:
        return df
    wanted = {str(c).strip() for c in filtros.categorias if str(c).strip()}
    if not wanted:
        return df
    return df[df["categoria"].astype(str).isin(wanted)]
