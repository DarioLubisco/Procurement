# F5: refuerzo solo a ofertas; Gap intermedio por elasticidades de no-oferta

La Extensión de Cobertura (F5) no es ni “por oferta pura” (código actual) ni “+días al Grupo entero repartido a todos”.

**Reglas acordadas:**

1. **Disparo:** hay oferta(s) del Grupo con Desvío bajo el umbral.
2. **Destino de las unidades extra:** solo el producto o productos **en oferta** (reforzar ofertas). No aumentar compra de otros miembros del Grupo en la distribución.
3. **No** volcar el Gap grupal completo a la(s) oferta(s).
4. **Tamaño:** `Gap_ext = Gap_oferta + (Gap_grupo − Gap_oferta) × f`, con `f = Σ (e_i/5)×(rot_i/Σ rot_no_oferta)` sobre no-oferta. **Denominador = solo no-oferta** (grill: A).

**Status:** accepted

## Ejemplo

X1 e=4 rot=10; X2 e=1 rot=5; Σ rot_no_oferta=15 → f=(0.8)(10/15)+(0.2)(5/15)≈0.533 → Gap_ext≈258 solo a Y.

## Consequences

- Runtime F5 actual no implementa esto; rediseño en P1+.
- JustificacionDelta cita f y pesos de rotación de no-oferta.
