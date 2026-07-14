# Carpeta de Pruebas / Tests

## Propósito

Esta carpeta contiene **todos los scripts de prueba, diagnóstico, experimentos y validaciones temporales** del proyecto Synapse-Procurement.

## Reglas

1. **Todo script de prueba nuevo** debe crearse dentro de esta carpeta, no en la raíz del proyecto.
2. **Organización por módulo:** Usa subcarpetas según el área que estás probando:
   - `tests/backend/` — Pruebas del backend FastAPI
   - `tests/frontend/` — Pruebas del frontend clásico
   - `tests/dashboard/` — Pruebas del dashboard React
   - `tests/analytics/` — Pruebas del motor de analítica
   - `tests/sql/` — Pruebas de consultas SQL
   - `tests/integracion/` — Pruebas de integración entre módulos
3. **Limpieza:** Los scripts temporales que ya no sirvan deben eliminarse, no acumularse.
4. **Nombres descriptivos:** Usa nombres que indiquen qué se está probando (ej. `test_conexion_bd.py`, `check_api_health.py`).

## Excepciones

- Los tests formales de frameworks (`pytest`, `jest`, etc.) pueden ir aquí o en la ubicación que defina el framework.
- Los scripts de producción NUNCA van aquí.

## Referencia

Los scripts antiguos que estaban dispersos en la raíz del proyecto fueron movidos a:
`/home/synapse/source/Referencia_obsoleta/Synapse-Procurement/scripts-diagnostico-prueba-obsoletos/`
