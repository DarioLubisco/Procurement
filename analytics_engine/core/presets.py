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
        "sust_kappa",  # ADR-0017 Definitivo opt-in
        "kappa",  # alias → sust_kappa
        "max_sustitucion_base",  # Avanzado only
    }
)

# Dead knobs — must never be exposed or applied (ticket 11 / ADR-0017).
DEAD_OPTIMIZER_KEYS = frozenset(
    {
        "s4_enabled",
        "s4_porcentaje_base",
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
        "sust_kappa",
        "kappa",
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
    # ADR-0017: None = kappa off (Sencillo / Definitivo without override)
    sust_kappa: Optional[float] = None
    max_sustitucion_base: Optional[float] = None


_ALIAS = {
    "ext_umbral": "f5_umbral",
    "w1_elasticidad": "w1",
    "w2_demanda": "w2",
    "w4_oportunidad": "w4",
    "w5_extension": "w5",
    "kappa": "sust_kappa",
}

# FE labels / input types for Definitivo overrides (ticket 11 UX).
_OVERRIDE_FIELD_META: Dict[str, Dict[str, Any]] = {
    "amplifier_enabled": {
        "label": "Amplificador de oportunidad",
        "type": "boolean",
        "hint": "Boost por desvío de precio (F4).",
        "help": (
            "Si está activo, cuando una oferta tiene desvío de precio favorable "
            "(más barata vs histórico), el motor puede subir la cantidad pedida "
            "de esa línea. Si está apagado, la qty sigue el Baseline/cobertura "
            "sin ese boost."
        ),
    },
    "amp_a": {
        "label": "Amplificador coeficiente A",
        "type": "number",
        "step": "0.01",
        "hint": "Curva del amplificador.",
        "help": (
            "Parámetro A de la curva exponencial del amplificador. "
            "Junto con B define cuánto crece la cantidad cuando el desvío es fuerte. "
            "Solo aplica si el amplificador está activo."
        ),
    },
    "amp_b": {
        "label": "Amplificador coeficiente B",
        "type": "number",
        "step": "0.01",
        "hint": "Curva del amplificador.",
        "help": (
            "Parámetro B de la curva exponencial del amplificador. "
            "Calibrado con A; no suele tocarse fuera de Avanzado."
        ),
    },
    "amp_max_increment_pct": {
        "label": "Tope amplificador (%)",
        "type": "number",
        "hint": "Máximo incremento %.",
        "help": (
            "Tope del incremento porcentual que el amplificador puede aplicar "
            "sobre la cantidad. Evita sobre-comprar ante desvíos extremos."
        ),
    },
    "amp_floor_pct": {
        "label": "Piso amplificador",
        "type": "number",
        "step": "0.01",
        "hint": "Desvío mínimo para amplificar.",
        "help": (
            "Umbral de desvío: por debajo de este piso el amplificador no dispara. "
            "Sirve para ignorar ahorros de precio muy chicos."
        ),
    },
    "ext_max_dias_extra": {
        "label": "Días extra GapExtension (F5)",
        "type": "number",
        "hint": "Extensión máx. de cobertura en oferta.",
        "help": (
            "Cuando hay ofertas fuertes (desvío bajo el umbral F5), el motor puede "
            "añadir unidades extra solo a productos en oferta, como si extendiera "
            "la cobertura unos días. 0 = F5 apagado."
        ),
    },
    "f5_umbral": {
        "label": "Umbral F5 (desvío)",
        "type": "number",
        "step": "0.01",
        "hint": "Desvío ≤ valor dispara F5.",
        "help": (
            "Desvío de precio (negativo = más barato) a partir del cual una oferta "
            "cuenta como 'fuerte' para GapExtension (F5). Ejemplo: -0.10 = 10% bajo "
            "la referencia histórica."
        ),
    },
    "opp_lambda": {
        "label": "Lambda oportunidad",
        "type": "number",
        "step": "0.1",
        "hint": "Peso de oportunidad de precio.",
        "help": (
            "Intensifica cuánto pesa la señal de oportunidad de precio en el score "
            "al elegir proveedor/código dentro del Grupo."
        ),
    },
    "w1": {
        "label": "Peso w1 elasticidad",
        "type": "number",
        "step": "0.01",
        "hint": "Peso elasticidad en score.",
        "help": (
            "Peso de la elasticidad de demanda en el scoring de ofertas. "
            "En la práctica el motor usa elasticidad sobre todo como tope de "
            "sustitución (κ / mapa), no como único árbitro."
        ),
    },
    "w2": {
        "label": "Peso w2 demanda",
        "type": "number",
        "step": "0.01",
        "hint": "Peso demanda en score.",
        "help": "Peso del factor demanda/rotación en el score de ofertas del Grupo.",
    },
    "w3_posicionamiento": {
        "label": "Peso w3 posicionamiento",
        "type": "number",
        "step": "0.01",
        "hint": "Peso precio (barato gana).",
        "help": (
            "Peso del posicionamiento de precio: ofertas más baratas dentro del "
            "Grupo puntúan más. Es el peso principal en Conservador/Normal."
        ),
    },
    "w4": {
        "label": "Peso w4 oportunidad",
        "type": "number",
        "step": "0.01",
        "hint": "Peso oportunidad (desvío).",
        "help": (
            "Peso de la oportunidad por desvío histórico (cuánto más barata está "
            "la oferta vs su media). Alto = persigue más las liquidaciones."
        ),
    },
    "w5": {
        "label": "Peso w5 extensión",
        "type": "number",
        "step": "0.01",
        "hint": "Peso extensión/oportunidad.",
        "help": (
            "Peso adicional ligado a la extensión de oportunidad (interactúa con "
            "lambda y F5). Subirlo favorece ofertas que también disparan extensión."
        ),
    },
    "lead_time_soft": {
        "label": "Lead time soft",
        "type": "select",
        "options": ["low", "medium", "high"],
        "hint": "Velocidad vs precio en scoring.",
        "help": (
            "Cuánto penaliza el score un lead time largo. low = casi no importa "
            "(prioriza precio); high = prefiere proveedores rápidos aunque cuesten más. "
            "No parte cantidades: eso es Split LeadTime."
        ),
    },
    "split_lead_time_enabled": {
        "label": "Split LeadTime",
        "type": "boolean",
        "hint": "Parte rápido + resto barato.",
        "help": (
            "Si el stock actual no cubre rotación×LT del proveedor más rápido, "
            "compra un mínimo al rápido (MOQ/stock) y el resto al más barato con "
            "peor LT. Genera dos líneas (mismo producto, dos proveedores)."
        ),
    },
    "sust_kappa": {
        "label": "Límite de reemplazo por sucedáneos (κ)",
        "type": "number",
        "step": "0.1",
        "default": 5.0,
        "help": (
            "Si no ajusta este valor, no se limita el reemplazo por sucedáneos. "
            "Con un valor (p. ej. 5), cuando el motor elige otro código del mismo grupo "
            "más barato, solo una fracción del pedido de esa línea puede cambiar de código; "
            "el resto se queda en el producto original. Más alto = permite más cambio "
            "cuando el ahorro de precio es grande."
        ),
        "hint": "Opt-in: vacío = sin tope; tipico 5.",
    },
    "max_sustitucion_base": {
        "label": "Tope base de sustitución (0–1)",
        "type": "number",
        "step": "0.05",
        "help": (
            "Solo Avanzado. Fracción base sustituible antes de expandir con κ "
            "(si vacío, se deriva de la elasticidad del producto: menos elástico = menos reemplazo)."
        ),
        "hint": "Opcional; si vacío usa mapa por elasticidad.",
    },
    "monto_buffer_pct": {
        "label": "Buffer presupuesto (%)",
        "type": "number",
        "step": "0.1",
        "hint": "Holgura sobre presupuesto máx.",
        "help": (
            "Si hay presupuesto máximo, este % añade holgura antes de cortar líneas. "
            "0 = respeta el tope estricto."
        ),
    },
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


def living_override_schema(
    *,
    nivel: str = "Avanzado",
    base_preset: str = "Normal",
) -> Dict[str, Any]:
    """Describe living knobs for FE (excludes dead S4; ADR-0017 exposes sust_kappa)."""
    if nivel == "Intermedio":
        keys = sorted(INTERMEDIO_OVERRIDE_KEYS - set(_ALIAS))
    else:
        keys = sorted(k for k in LIVING_OVERRIDE_KEYS if k not in _ALIAS)
    try:
        preset_enum = PresetSencillo(base_preset)
    except ValueError:
        preset_enum = PresetSencillo.NORMAL
    knobs = resolve_preset_knobs(preset_enum)
    fields_out: list[Dict[str, Any]] = []
    for key in keys:
        meta = dict(_OVERRIDE_FIELD_META.get(key, {"label": key, "type": "number"}))
        if hasattr(knobs, key):
            val = getattr(knobs, key)
            meta["default"] = val
        fields_out.append({"key": key, **meta})
    return {
        "nivel": nivel,
        "base_preset": preset_enum.value,
        "living_keys": keys,
        "fields": fields_out,
        "dead_keys_excluded": sorted(DEAD_OPTIMIZER_KEYS),
        "note": (
            "Si no ajusta el límite de reemplazo (κ), no se limita el cambio a sucedáneos. "
            "S4 sigue excluido."
        ),
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
                "(S4/monto_days_reduction no expuestos)"
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


def max_sustitucion_base_from_elasticidad(elasticidad: float) -> float:
    """ADR-0017 default map: less elastic → lower substitutable fraction."""
    try:
        e = int(round(float(elasticidad)))
    except (TypeError, ValueError):
        e = 0
    if e <= 0:
        return 0.0
    if e == 1:
        return 0.2
    if e == 2:
        return 0.4
    if e == 3:
        return 0.6
    return 0.8
