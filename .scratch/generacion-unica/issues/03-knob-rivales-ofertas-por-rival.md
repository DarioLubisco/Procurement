Status: resolved

# 03-knob-rivales-ofertas-por-rival

Parent: `.scratch/generacion-unica/PRD.md`  
Also listed in: `tickets.md`

## What to build

Preset/knob schema gains `rivales_ofertas_por_rival` (default 2); `hermanos_top_n` / `rivales_top_n` remain default 3 with existing clamp behaviour.

## Acceptance criteria

- [x] Knob exists on PresetKnobs (or successor) with default 2 and clamp range
- [x] Overrides schema / overrides-schema consumers expose the new knob
- [x] Factory presets do not break; missing key resolves to default 2
- [x] Unit tests cover clamp and default

## Blocked by

None — can start immediately.

## Answer

Added `rivales_ofertas_por_rival: int = 2` to `PresetKnobs`, living + Intermedio override keys, field meta, and `clamp_top_n` in `apply_living_overrides`. Tests: `tests/analytics/test_rivales_ofertas_por_rival.py`.

## Comments
