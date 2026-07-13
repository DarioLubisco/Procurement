"""Presets Sencillo — knob maps (ADR-0010+)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PresetSencillo(str, Enum):
    CONSERVADOR = "Conservador"
    NORMAL = "Normal"
    AGRESIVO = "Agresivo"


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


def resolve_preset_knobs(preset: PresetSencillo) -> PresetKnobs:
    if preset is PresetSencillo.CONSERVADOR:
        # ADR-0010
        return PresetKnobs(
            amplifier_enabled=False,
            ext_max_dias_extra=0,
            w1=0.0,
            w2=0.0,
            w3_posicionamiento=1.0,
            w4=0.0,
            w5=0.0,
            lead_time_soft="low",
        )
    raise ValueError(f"preset not implemented yet: {preset}")
