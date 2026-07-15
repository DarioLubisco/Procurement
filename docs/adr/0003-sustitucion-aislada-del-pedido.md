# Sustitución aislada del schema de Pedido

`sust_kappa` / `quadratic_ceiling` están modelados y persistidos pero **nunca se invocan** en `run_optimization`. El `substitution_engine` existe como API adyacente. Decidimos **aislar** la Sustitución del dominio Pedido: eliminar `kappa` del schema de perfil, no cablear techos de sustitución en la distribución, y dejar el engine como módulo con interface propia.

**Status:** superseded by ADR-0005

> **2026-07-11:** El flujo de ComparativaCantidades requiere que el PedidoPropuesto pueda reemplazar BARRAs por sucedáneos del mismo **Grupo** (mercado vivo). Eso reabre la integración de sustitución en el Pedido.
>
> **2026-07-15:** κ / techo cuadrático se reactiva solo en Definitivo (opt-in) — ver **ADR-0017**. Este ADR ya no prohíbe κ en absoluto.

