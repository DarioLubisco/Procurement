"""Structured Comparativa justification factors + short summary (grill 2026-07-15)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

# Celda truncada: priority order (grill C). Top N títulos.
FACTOR_PRIORITY: Tuple[str, ...] = (
    "sucedaneo",
    "split_lead_time",
    "kappa",
    "f5",
    "amplificador",
    "pdr",
    "oferta",
    "compensacion_grupo",
    "delta_qty",
    "sin_oferta",
    "sin_catalogo",
    "validar_minimos",
)

_TITULOS: Dict[str, str] = {
    "sucedaneo": "Sucedáneo",
    "split_lead_time": "Split LeadTime",
    "kappa": "Techo κ",
    "f5": "F5",
    "amplificador": "Amplificador",
    "pdr": "PDR",
    "oferta": "Oferta",
    "compensacion_grupo": "Compensación grupo",
    "delta_qty": "Delta qty",
    "sin_oferta": "Sin oferta",
    "sin_catalogo": "Sin catálogo",
    "validar_minimos": "Validar mínimos",
}


@dataclass(frozen=True)
class JustificacionFactor:
    codigo: str
    titulo: str
    detalle: str
    datos: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "codigo": self.codigo,
            "titulo": self.titulo,
            "detalle": self.detalle,
            "datos": dict(self.datos or {}),
        }


def factor(
    codigo: str,
    detalle: str,
    *,
    titulo: Optional[str] = None,
    datos: Optional[Mapping[str, Any]] = None,
) -> JustificacionFactor:
    return JustificacionFactor(
        codigo=codigo,
        titulo=titulo or _TITULOS.get(codigo, codigo),
        detalle=detalle,
        datos=dict(datos or {}),
    )


def resumen_corto(
    factores: Sequence[JustificacionFactor],
    *,
    max_n: int = 2,
) -> str:
    """Celda truncada: top factores by FACTOR_PRIORITY (grill C)."""
    if not factores:
        return ""
    by_code = {f.codigo: f for f in factores}
    ordered: List[JustificacionFactor] = []
    for code in FACTOR_PRIORITY:
        if code in by_code:
            ordered.append(by_code[code])
    # Any unknown codes last
    for f in factores:
        if f.codigo not in FACTOR_PRIORITY and f not in ordered:
            ordered.append(f)
    if not ordered:
        return ""
    top = ordered[: max(1, int(max_n))]
    parts = [f.titulo for f in top]
    rest = len(ordered) - len(top)
    if rest > 0:
        parts.append(f"+{rest}")
    return " · ".join(parts)


def factors_to_dicts(
    factores: Sequence[JustificacionFactor],
) -> List[Dict[str, Any]]:
    return [f.to_dict() for f in factores]


def factors_from_dicts(
    raw: Optional[Sequence[Mapping[str, Any]]],
) -> List[JustificacionFactor]:
    out: List[JustificacionFactor] = []
    for item in raw or []:
        if not isinstance(item, Mapping):
            continue
        codigo = str(item.get("codigo") or "").strip()
        if not codigo:
            continue
        out.append(
            JustificacionFactor(
                codigo=codigo,
                titulo=str(item.get("titulo") or _TITULOS.get(codigo, codigo)),
                detalle=str(item.get("detalle") or ""),
                datos=dict(item.get("datos") or {}),
            )
        )
    return out


def append_factor(
    factores: Sequence[JustificacionFactor],
    nuevo: JustificacionFactor,
) -> Tuple[JustificacionFactor, ...]:
    """Replace same codigo if present, else append; keep stable-ish order."""
    out: List[JustificacionFactor] = []
    replaced = False
    for f in factores:
        if f.codigo == nuevo.codigo:
            out.append(nuevo)
            replaced = True
        else:
            out.append(f)
    if not replaced:
        out.append(nuevo)
    return tuple(out)


def finalize(
    factores: Sequence[JustificacionFactor],
) -> Tuple[str, Tuple[JustificacionFactor, ...]]:
    tup = tuple(factores)
    return resumen_corto(tup), tup
