# Intent: Git Tracking en Notion

## Outcome
Agregar una propiedad visible en Notion (select con dos estados: `🔴 Sin commit` / `🟢 En GitHub`) que se actualice automáticamente vía el webhook de GitHub cuando un push referencia el ID o nombre de la tarea.

## User
Dario, para tener trazabilidad instantánea de qué trabajo de Antigravity ya está seguro en el repositorio.

## Why now
Se han creado muchos archivos nuevos (`analytics_engine/`, `docs/intent/`, scripts varios) y no hay forma de saber visualmente en Notion cuáles ya están commiteados.

## Success Criteria
Al abrir el tablero de Notion, cada tarea muestra claramente si su código ya fue pusheado a GitHub o si sigue solo en el filesystem de Debian sin versionar.

## Constraint
El mecanismo debe ser automático (no depender de marcado manual), usando el webhook de GitHub que ya existe en n8n.

## Out of Scope
- No se implementará un tercer estado de "En Producción" por ahora.
- No se modificará el flujo de deploy existente ni se crearán pipelines CI/CD nuevos.
