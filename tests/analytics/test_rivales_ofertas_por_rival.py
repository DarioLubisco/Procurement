"""rivales_ofertas_por_rival knob — generacion-unica ticket 03."""
from __future__ import annotations

from analytics_engine.core.presets import (
    PresetKnobs,
    PresetSencillo,
    apply_living_overrides,
    living_override_schema,
    resolve_preset_knobs,
)


def test_rivales_ofertas_por_rival_default_is_two():
    knobs = resolve_preset_knobs(PresetSencillo.NORMAL)
    assert knobs.rivales_ofertas_por_rival == 2
    # Explicit field default on the dataclass
    assert PresetKnobs(
        amplifier_enabled=False,
        ext_max_dias_extra=0,
        w1=1,
        w2=0,
        w3_posicionamiento=0,
        w4=0,
        w5=0,
        lead_time_soft="low",
    ).rivales_ofertas_por_rival == 2


def test_rivales_ofertas_por_rival_clamped_on_override():
    base = resolve_preset_knobs(PresetSencillo.NORMAL)
    hi = apply_living_overrides(
        base, {"rivales_ofertas_por_rival": 99}, nivel="Avanzado"
    )
    assert hi.rivales_ofertas_por_rival == 10
    lo = apply_living_overrides(
        base, {"rivales_ofertas_por_rival": 0}, nivel="Avanzado"
    )
    assert lo.rivales_ofertas_por_rival == 1
    mid = apply_living_overrides(
        base, {"rivales_ofertas_por_rival": 4}, nivel="Intermedio"
    )
    assert mid.rivales_ofertas_por_rival == 4
    bad = apply_living_overrides(
        base, {"rivales_ofertas_por_rival": "nope"}, nivel="Avanzado"
    )
    assert bad.rivales_ofertas_por_rival == 2


def test_rivales_ofertas_por_rival_in_overrides_schema():
    schema = living_override_schema(nivel="Avanzado")
    keys = {f["key"] for f in schema["fields"]}
    assert "rivales_ofertas_por_rival" in keys
    field = next(f for f in schema["fields"] if f["key"] == "rivales_ofertas_por_rival")
    assert field["type"] == "number"
    assert field.get("default") == 2
