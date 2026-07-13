"""Presets Sencillo — knob maps (ADR-0010+) + living OptimizerConfig overrides."""
from __future__ import annotations

from dataclasses import dataclass, fields, replace
from enum import Enum
from typing import Any, Dict, Mapping, Optional


class PresetSencillo(str, Enum):
    CONSERVADOR = "Conservador"
    NORMAL = "Normal"
    AGRESIVO = "Agresivo"


# Living OptimizerConfig fields that may override Definitivo (ADR / grill).
LIVING_OVERRIDE_KEYS = frozenset(
    {
        "amplifier_enabled",
        "amp_a",
        "amp_b",
        "amp_max_increment_pct",
        "amp_floor_pct",
        "ext_max_dias_extra",
        "f5_umbral",
        "ext_umbral",  # alias → f5_umbral
        "ext_eta",  # living; accepted, unused by seam yet
        "opp_lambda",
        "w1",
        "w2",
        "w3_posicionamiento",
        "w4",
        "w5",
        "w1_elasticidad",  # alias → w1
        "w2_demanda",
        "w4_oportunidad",
        "w5_extension",
        "lead_time_soft",
        "split_lead_time_enabled",
        "monto_buffer_pct",
    }
)

# Dead knobs — must never be exposed or applied (ticket 11).
DEAD_OPTIMIZER_KEYS = frozenset(
    {
        "s4_enabled",
        "s4_porcentaje_base",
        "sust_kappa",
        "kappa",
        "monto_days_reduction_pct",
    }
)

# Intermedio exposes a business-facing subset; Avanzado = all living.
INTERMEDIO_OVERRIDE_KEYS = frozenset(
    {
        "amp_max_increment_pct",
        "amp_floor_pct",
        "ext_max_dias_extra",
        "f5_umbral",
        "ext_umbral",
        "opp_lambda",
        "w1",
        "w2",
        "w3_posicionamiento",
        "w4",
        "w5",
        "lead_time_soft",
        "split_lead_time_enabled",
    }
)


@dataclass(frozen=True)
class PresetKnobs:
    amplifier_enabled: bool
    ext_max_dias_extra: int
    w1: float
    w2: float
    w3_posicionamiento: float
    w4: float
    w5: float
    lead_time_soft: str  # low | medium | high
    amp_a: float = 5.84
    amp_b: float = 1.29
    amp_max_increment_pct: float = 500.0
    amp_floor_pct: float = 0.2
    f5_umbral: float = -0.10
    opp_lambda: float = 1.0
    split_lead_time_enabled: bool = False


_ALIAS = {
    "ext_umbral": "f5_umbral",
    "w1_elasticidad": "w1",
    "w2_demanda": "w2",
    "w4_oportunidad": "w4",
    "w5_extension": "w5",
}


def resolve_preset_knobs(preset: PresetSencillo) -> PresetKnobs:
    if preset is PresetSencillo.CONSERVADOR:
        return PresetKnobs(
            amplifier_enabled=False,
            ext_max_dias_extra=0,
            w1=0.0,
            w2=0.0,
            w3_posicionamiento=1.0,
            w4=0.0,
            w5=0.0,
            lead_time_soft="low",
            split_lead_time_enabled=False,
        )
    if preset is PresetSencillo.NORMAL:
        return PresetKnobs(
            amplifier_enabled=True,
            ext_max_dias_extra=21,
            w1=0.15,
            w2=0.25,
            w3_posicionamiento=0.25,
            w4=0.20,
            w5=0.15,
            lead_time_soft="medium",
            amp_a=5.84,
            amp_b=1.29,
            amp_max_increment_pct=500.0,
            amp_floor_pct=0.2,
            f5_umbral=-0.10,
            opp_lambda=1.0,
            split_lead_time_enabled=True,
        )
    if preset is PresetSencillo.AGRESIVO:
        return PresetKnobs(
            amplifier_enabled=True,
            ext_max_dias_extra=45,
            w1=0.05,
            w2=0.20,
            w3_posicionamiento=0.15,
            w4=0.35,
            w5=0.25,
            lead_time_soft="high",
            amp_a=5.84,
            amp_b=1.29,
            amp_max_increment_pct=800.0,
            amp_floor_pct=0.15,
            f5_umbral=-0.05,
            opp_lambda=1.5,
            split_lead_time_enabled=True,
        )
    raise ValueError(f"preset not implemented yet: {preset}")


def living_override_schema(*, nivel: str = "Avanzado") -> Dict[str, Any]:
    """Describe living knobs for FE (excludes dead S4/kappa)."""
    if nivel == "Intermedio":
        keys = sorted(INTERMEDIO_OVERRIDE_KEYS - set(_ALIAS))
    else:
        keys = sorted(k for k in LIVING_OVERRIDE_KEYS if k not in _ALIAS)
    return {
        "nivel": nivel,
        "living_keys": keys,
        "dead_keys_excluded": sorted(DEAD_OPTIMIZER_KEYS),
        "note": "Overrides map onto PresetKnobs / OptimizerConfig living fields only.",
    }


def apply_living_overrides(
    base: PresetKnobs,
    overrides: Optional[Mapping[str, Any]],
    *,
    nivel: str,
) -> PresetKnobs:
    """Apply living OptimizerConfig overrides; reject dead knobs."""
    if not overrides:
        return base
    allowed = INTERMEDIO_OVERRIDE_KEYS if nivel == "Intermedio" else LIVING_OVERRIDE_KEYS
    knob_names = {f.name for f in fields(PresetKnobs)}
    updates: Dict[str, Any] = {}
    for raw_key, value in overrides.items():
        if raw_key in DEAD_OPTIMIZER_KEYS:
            raise ValueError(
                f"override muerto rechazado: {raw_key} "
                "(S4/kappa/monto_days_reduction no expuestos)"
            )
        key = _ALIAS.get(raw_key, raw_key)
        if raw_key not in allowed and key not in allowed:
            if nivel == "Intermedio":
                raise ValueError(
                    f"override {raw_key!r} no permitido en Intermedio; use Avanzado"
                )
            raise ValueError(f"override desconocido: {raw_key!r}")
        if key in ("monto_buffer_pct", "ext_eta"):
            continue
        if key not in knob_names:
            continue
        updates[key] = value
    if not updates:
        return base
    return replace(base, **updates)
