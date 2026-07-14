# Plan Técnico: CRM Omnicanal "Agent-Ready" & FinOps-Centric

Este documento detalla la estrategia de optimización de costos y arquitectura de datos para la integración de IA en el ecosistema Chatwoot/n8n.

## 1. Estrategia de Optimización de Contexto (FinOps)

El objetivo es minimizar el costo por mensaje eliminando la redundancia de datos en los prompts.

### Metodologías Clave:
*   **Context Caching (Gemini):** Para manuales de políticas y catálogos estáticos extensos. Se paga por el almacenamiento del caché una vez y se reduce el costo de los tokens de entrada en un 50-75% por cada mensaje.
*   **RAG (Retrieval-Augmented Generation):** Uso de `pgvector` en PostgreSQL para inyectar solo los fragmentos relevantes del catálogo masivo de productos (500 tokens vs 50,000 tokens).
*   **Function Calling (SQL):** Herramientas directas para consultar stock en tiempo real mediante SQL, evitando que el LLM "alucine" o requiera contextos masivos de inventario.

---

## 2. Plan de Optimización Financiera (Comparativa)

| Concepto | Sin Optimización | Con Arquitectura FinOps |
| :--- | :--- | :--- |
| **Tokens por Mensaje** | ~52,000 tokens | ~1,500 tokens |
| **Costo por Mensaje** | ~$0.0039 USD | ~$0.0001 USD |
| **Costo Mensual (30k msg)** | ~$117.00 USD | **~$4.00 USD** |
| **Ahorro Estimado** | 0% | **~96%** |

---

## 3. Guía Táctica n8n: Gestión de Memoria (Windowing)

Para evitar el desbordamiento de tokens en conversaciones largas:
1.  **Nodo Postgres Chat Memory:** Configurar ventana de los últimos 10 mensajes.
2.  **Nodo Summarization:** Si la sesión excede el límite, se genera un resumen ejecutivo del historial previo para liberar tokens sin perder el hilo conductor.

---

## 4. Diseño de Payload (AI-Ready JSON)

Objeto estructurado para la inyección en el Agente:

```json
{
  "system_context": {
    "channel_source": "instagram_business",
    "cache_reference_uri": "models/gemini-2.5-flash/cachedContents/policies_v1",
    "required_tone": "visual_and_friendly_with_emojis"
  },
  "customer_state": {
    "chatwoot_contact_id": "84729",
    "crm_id": "CUST-992",
    "vip_status": false
  },
  "active_request": {
    "message_type": "text",
    "content": "¿Tienen la camisa roja en talla M?",
    "timestamp": "2026-04-25T17:45:00Z"
  }
}
```

---

## 5. Matriz de Selección de Modelos

| Tarea | Modelo | Justificación |
| :--- | :--- | :--- |
| **Clasificación / Triage** | Gemini Flash-Lite | Costo casi nulo, ideal para filtrar ruidos y saludos. |
| **Venta / Resolución / SQL** | Gemini 2.5 Flash | Excelente razonamiento y soporte nativo de Function Calling. |
| **Supervisión (Human-in-the-loop)** | Chatwoot UI | Validación humana antes de envío directo o modo borrador. |
