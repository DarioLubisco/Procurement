import json
import asyncio
import httpx
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from database import get_scraper_db_connection

import os

# Limitador de concurrencia. Permite 30 hilos en paralelo para el orquestador (Pool Aislado)
# Esto deja las 50 conexiones del Pool Principal de Synapse completamente intactas.
scraper_semaphore = asyncio.Semaphore(30)

def write_log(msg):
    try:
        with open("/app/orq.log", "a") as f:
            f.write(msg + "\n")
    except:
        pass

router = APIRouter(prefix="/api/orquestador", tags=["Orquestador"])
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
class AutomationTask(BaseModel):
    TriggerID: int
    ActionCommand: str
    IsActive: bool
    LastTriggered: Optional[str] = None

class ChatMessage(BaseModel):
    agent: str
    message: str

def fetch_pending_records(limit=100):
    try:
        with get_scraper_db_connection() as conn:
            cursor = conn.cursor()
            query = f"""
            SELECT TOP {limit} codbarras AS codigo, codbarras, descrip1art 
            FROM Procurement.por_aprobacion_equivalencias 
            WHERE origen_dato IS NULL OR origen_dato != \'IA_INVESTIGATED_V10_CLEANSE\'
            """
            cursor.execute(query)
            rows = cursor.fetchall()
            lote = [{"codigo": r[0], "codbarras": r[1], "descripcion_original": r[2]} for r in rows]
            return lote
    except Exception as e:
        write_log(f"Error DB: {e}")
        return []

async def analyze_with_ai(lote):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    batch_str = json.dumps(lote, ensure_ascii=False)
    prompt = f"""
    Actúa como el Agente Investigador Farmacéutico. Recibirás un lote de productos.
    Para cada producto, extrae los siguientes atributos basándote en la descripción:
    - principio_activo (string o null si no aplica)
    - concentracion (string o null)
    - forma_farmaceutica (string o null)

    IMPORTANTE: Devuelve ÚNICAMENTE un array JSON válido con este formato, sin markdown extra:
    [
      {{
        "registro": {{"codigo": "...", "codbarras": "...", "descripcion_original": "..."}},
        "atributos": {{"principio_activo": "...", "concentracion": "...", "forma_farmaceutica": "..."}}
      }}
    ]

    LOTE A PROCESAR:
    {batch_str}
    """
    
    data = {
        "model": "google/gemini-2.5-flash",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.1
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=data)
            result = resp.json()
            content = result['choices'][0]['message']['content']
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            return json.loads(content.strip())
        except Exception as e:
            write_log(f"Error AI: {e}")
            return []

async def run_scraper_task(task: AutomationTask):
    if scraper_semaphore.locked():
        write_log(f"[Orquestador] Tarea {task.TriggerID} encolada, esperando liberación del semáforo...")
        
    async with scraper_semaphore:
        write_log(f"[Orquestador] Iniciando tarea: {task.ActionCommand} (ID: {task.TriggerID})")
        webhook_url = "https://n8n.farmaciaamericana.es/webhook/osint-resultados"
    try:
        # Traer registros de base de datos
        lote = await asyncio.to_thread(fetch_pending_records, 100)
        
        if not lote:
            write_log("[Orquestador] No hay registros pendientes.")
            # Mandar webhook de todos modos para que n8n cierre el trigger
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json={"TriggerID": task.TriggerID, "status": "Vacio", "data": []}, timeout=30.0)
            return

        write_log(f"[Orquestador] Procesando {len(lote)} registros con IA...")
        resultados_ia = await analyze_with_ai(lote)

        scraped_results = []
        for item in resultados_ia:
            reg = item.get("registro", {})
            atr = item.get("atributos", {})
            scraped_results.append({
                "codigo": reg.get("codigo"),
                "codbarras": reg.get("codbarras"),
                "principio_activo_Des": atr.get("principio_activo"),
                "concentracion_Des": atr.get("concentracion"),
                "forma_farmaceutica_Des": atr.get("forma_farmaceutica")
            })

        write_log(f"[Orquestador] IA finalizada. Actualizando DB localmente para {len(scraped_results)} items...")
        
        # Realizamos el update de DB localmente usando pyodbc con el Pool Dedicado
        try:
            with get_scraper_db_connection() as conn:
                cursor = conn.cursor()
                for res in scraped_results:
                    cb = res.get("codbarras")
                    if not cb: continue
                    pa = res.get("principio_activo_Des")
                    con = res.get("concentracion_Des")
                    ff = res.get("forma_farmaceutica_Des")
                    
                    # Update by codbarras safely
                    query = """
                        UPDATE Procurement.por_aprobacion_equivalencias 
                        SET principio_activo_Des = ?,
                            concentracion_Des = ?,
                            forma_farmaceutica_Des = ?,
                            origen_dato = 'IA_INVESTIGATED_V10_CLEANSE'
                        WHERE codbarras = ?
                    """
                    cursor.execute(query, pa, con, ff, cb)
                conn.commit()
                write_log("[Orquestador] DB actualizada con éxito.")
        except Exception as e:
            write_log(f"[Orquestador] Error actualizando DB: {e}")

        write_log(f"[Orquestador] IA finalizada. Enviando {len(scraped_results)} items a n8n...")

        payload = {
            "TriggerID": task.TriggerID,
            "status": "Completado",
            "ActionCommand": task.ActionCommand,
            "data": scraped_results
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(webhook_url, json=payload, timeout=30.0)
            if response.status_code == 200:
                write_log(f"[Orquestador] Webhook exitoso.")
            else:
                write_log(f"[Orquestador] Webhook falló: {response.status_code}")

    except Exception as e:
        write_log(f"[Orquestador] Error crítico en tarea {task.TriggerID}: {e}")
        try:
            async with httpx.AsyncClient() as client:
                await client.post(webhook_url, json={"TriggerID": task.TriggerID, "status": "Error", "data": []})
        except:
            pass

@router.post("/start")
async def start_orquestador(task: AutomationTask, background_tasks: BackgroundTasks):
    if not task:
        return {"status": "ignored", "message": "No task"}
        
    background_tasks.add_task(run_scraper_task, task)
    return {"status": "started", "task_queued": task.TriggerID}

@router.get("/status")
async def get_orquestador_status():
    return {
        "agent": "Orquestador Central",
        "model": "deepseek/deepseek-v4-flash",
        "status": "online"
    }

@router.post("/chat")
async def chat_with_orquestador(chat: ChatMessage):
    if not chat.message:
        return {"reply": "Mensaje vacío."}
    
    if chat.agent == "agente_it":
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post("http://10.147.18.204:8001/chat", json={"message": chat.message, "session_id": "default", "channel": "it"})
                if resp.status_code == 200:
                    return {"reply": resp.json().get("response", "Respuesta vacía del Agente IT")}
                return {"reply": f"Error del Agente IT: {resp.status_code}"}
            except Exception as e:
                return {"reply": f"Error de conexión con Debian (Agente IT): {e}"}
                
    if chat.agent == "agente_equivalencias":
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                resp = await client.post("http://10.147.18.204:8001/chat", json={"message": chat.message, "session_id": "default", "channel": "equivalencias"})
                if resp.status_code == 200:
                    return {"reply": resp.json().get("response", "Respuesta vacía del Agente de Equivalencias")}
                return {"reply": f"Error del Agente de Equivalencias: {resp.status_code}"}
            except Exception as e:
                return {"reply": f"Error de conexión con Debian (Agente de Equivalencias): {e}"}
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek/deepseek-v4-flash",
        "messages": [
            {"role": "system", "content": f"Eres {chat.agent}, un sub-agente del ecosistema Synapse. Responde de forma concisa y profesional a las consultas operativas."},
            {"role": "user", "content": chat.message}
        ],
        "temperature": 0.5
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.post(url, headers=headers, json=data)
            result = resp.json()
            if 'choices' in result and len(result['choices']) > 0:
                reply = result['choices'][0]['message']['content']
                return {"reply": reply}
            else:
                write_log(f"[Orquestador Chat] OpenRouter Bad Response: {result}")
                return {"reply": "Lo siento, hubo un error de comunicación con OpenRouter.", "raw": result}
        except Exception as e:
            write_log(f"Error AI Chat: {e}")
            return {"reply": f"Error interno en agente:equivalencias: {str(e)}"}
