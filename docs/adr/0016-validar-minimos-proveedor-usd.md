# Validar mínimos de proveedor (USD)

Tras Generar, un paso explícito **ValidarMinimosProveedor** compara `sum(qty×precio)` por proveedor contra `ProveedorConfig.MontoMinimoPedidoUSD`. No muta cobertura en el primer Generar Sencillo. Si falta mínimo: el comprador elige % extra de cobertura (default sugerido +50%) solo sobre SKUs ya asignados a ese proveedor; tras el primer fallo ve panel (ahorro vs 2º precio barra→Grupo, costo de rechazo, reemplazos del Grupo) antes de más %; puede reintentar % sin límite, **Aceptar submínimo** o **Rechazar** (reasigna al 2º o huérfano). Proveedores en cola serie (mayor déficit primero); rechazo **re-encola** destinos que queden bajo mínimo. Trazas en `JustificacionDelta` y `meta.validar_minimos`. Distinto del MOQ en unidades del SplitLeadTime. No usar `SAPROD.Minimo`.

**Status:** accepted (grill 2026-07-14)

## Considered options (resumen)

- Completar a $ inventando qty → rechazado (aceptar submínimo o rechazar).
- Mutar cobertura en silencio en Sencillo → rechazado (paso B explícito).
- Resolver varios proveedores en paralelo → rechazado (cola serie + cascada).

## Consequences

- Cablear loader `ProveedorConfig` + endpoint/UI “Validar mínimos”.
- Actualiza semántica de ADR-0015 (fuente USD ya existe; falta implementación del paso).
- kappa / techo cuadrático sigue fuera de este flujo (sesión aparte si se reactiva).
- Aliases `ProveedorCodProvAlias`: cola/boost/rechazo por entidad comercial; el 2º precio **excluye** CodProvs del mismo `ProveedorID`.
