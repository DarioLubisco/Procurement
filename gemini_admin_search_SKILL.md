---
name: gemini_admin_search
description: >
  Herramienta de búsqueda en manuales administrativos y normativos de la farmacia
  usando la API de Google Gemini File Search. Permite consultar políticas internas,
  procedimientos, reglamentos y normativas legales sin necesidad de bases de datos
  vectoriales locales.
tools:
  - consultar_manual_administrativo
  - listar_manuales_disponibles
---

# Gemini Administrative Manual Search

## Propósito
Esta skill permite al agente buscar información en los manuales administrativos
y normativos de la farmacia (PDFs subidos a Google AI Studio) usando la API
nativa de Google Gemini.

## Herramientas Disponibles

### `consultar_manual_administrativo(pregunta: str) -> str`
Busca respuestas en el manual administrativo. Usar SOLO para:
- Reglas internas y políticas de la farmacia
- Procedimientos operativos (devoluciones, despacho, recepción de mercancía)
- Normativas legales y regulatorias del sector farmacéutico
- Políticas de RRHH, horarios administrativos, turnos
- Cualquier información administrativa que NO esté en el inventario/DB

**NO usar para:** stock, precios, inventario (usar `consultar_inventario` del skill CRM).

### `listar_manuales_disponibles() -> str`
Diagnóstico: lista los manuales configurados y verifica su disponibilidad en Google.

## Configuración
- **API Key**: Variable de entorno `GEMINI_API_KEY` en el servidor
- **Archivos**: Subidos a Google AI Studio, IDs configurados en `gemini_admin_search.py`
- **Modelo**: Gemini 2.5 Flash (rápido y económico)

## Ejemplo de uso
```
Pregunta del cliente: "¿Aceptan devoluciones de jarabes abiertos?"
→ El agente ejecuta: consultar_manual_administrativo("Política de devolución de jarabes abiertos")
→ Respuesta del manual: "Según el reglamento interno, no se aceptan devoluciones de frascos abiertos..."
```
