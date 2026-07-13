"""GapExtensionOferta (F5) — ADR-0012."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class MiembroGrupo:
    barra: str
    rotacion: float
    elasticidad: float  # 0–5
    gap: float
    en_oferta: bool


@dataclass(frozen=True)
class GapExtensionResult:
    f: float
    gap_ext: float
    gap_oferta: float
    gap_grupo: float
    barras_refuerzo: tuple[str, ...]


def compute_f_no_oferta(miembros: Sequence[MiembroGrupo]) -> float:
    """f = Σ (e_i/5) * (rot_i / Σ rot_no_oferta) over non-offer members only."""
    no_oferta = [m for m in miembros if not m.en_oferta]
    denom = sum(max(m.rotacion, 0.0) for m in no_oferta)
    if denom <= 0:
        return 0.0
    return sum((m.elasticidad / 5.0) * (m.rotacion / denom) for m in no_oferta)


def compute_gap_extension_oferta(
    miembros: Sequence[MiembroGrupo],
) -> GapExtensionResult:
    """Gap_ext = Gap_oferta + (Gap_grupo − Gap_oferta) × f; reinforces offers only."""
    ofertas = [m for m in miembros if m.en_oferta]
    gap_grupo = sum(m.gap for m in miembros)
    gap_oferta = sum(m.gap for m in ofertas)
    f = compute_f_no_oferta(miembros)
    gap_ext = gap_oferta + (gap_grupo - gap_oferta) * f
    # Never dump full gap_grupo as the extension target size when f < 1
    return GapExtensionResult(
        f=f,
        gap_ext=gap_ext,
        gap_oferta=gap_oferta,
        gap_grupo=gap_grupo,
        barras_refuerzo=tuple(m.barra for m in ofertas),
    )
