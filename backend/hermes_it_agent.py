import os
import asyncio
import httpx
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="agente:equivalencias IT Subagent API")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Client init helper
def get_openai_client():
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY", "")
        
    if not api_key:
        print("WARNING: OPENAI_API_KEY o OPENROUTER_API_KEY no están configuradas.")
        
    return AsyncOpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key
    )
def clean_json_response(content: str) -> str:
    content = content.strip()
    if content.startswith("```json"):
        content = content[7:]
    elif content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    return content.strip()

class ChatMessage(BaseModel):
    message: str
    session_id: str
    channel: str = "it"

async def ask_telegram_approval(command: str) -> bool:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram Token/Chat ID faltante. Denegando comando sudo por seguridad.")
        return False
        
    async with httpx.AsyncClient() as client:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Aprobar Sudo", "callback_data": "approve_sudo"},
                    {"text": "❌ Denegar", "callback_data": "deny_sudo"}
                ]
            ]
        }
        
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": f"⚠️ *HITL: Solicitud de Ejecución Sudo*\n\nEl Sub-agente IT intenta ejecutar:\n`{command}`\n\n¿Autorizas esta acción en Debian?",
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }
        
        try:
            resp = await client.post(url, json=payload)
            data = resp.json()
            if not data.get("ok"):
                print("Error enviando a Telegram:", data)
                return False
                
            message_id = data["result"]["message_id"]
            
            # Polling async para esperar respuesta
            offset = 0
            approved = False
            answered = False
            
            print(f"Esperando aprobación HITL en Telegram para el mensaje {message_id}...")
            
            # Tiempo máximo de espera: 280 segundos (un poco menos que el timeout de Nginx)
            timeout_hitl = 280 
            start_time = asyncio.get_event_loop().time()
            
            while not answered:
                if (asyncio.get_event_loop().time() - start_time) > timeout_hitl:
                    print(f"Timeout de espera HITL alcanzado para {message_id}")
                    break
                    
                updates_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={offset}&timeout=5"
                try:
                    upd_resp = await client.get(updates_url, timeout=10)
                    updates = upd_resp.json()
                    if updates.get("ok"):
                        for update in updates.get("result", []):
                            offset = update["update_id"] + 1
                            if "callback_query" in update:
                                cb = update["callback_query"]
                                if cb.get("message", {}).get("message_id") == message_id:
                                    action = cb.get("data")
                                    answered = True
                                    approved = (action == "approve_sudo")
                                    
                                    # Responder al callback
                                    await client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", 
                                                    json={"callback_query_id": cb["id"], "text": "Respuesta registrada."})
                                    
                                    # Editar el mensaje original para reflejar la decisión
                                    decision_text = "✅ APROBADO" if approved else "❌ DENEGADO"
                                    await client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                                                    json={
                                                        "chat_id": TELEGRAM_CHAT_ID,
                                                        "message_id": message_id,
                                                        "text": f"⚠️ *HITL: Ejecución Sudo*\n\nComando: `{command}`\n\nEstado: *{decision_text}*",
                                                        "parse_mode": "Markdown"
                                                    })
                    await asyncio.sleep(2)
                except Exception as e:
                    print("Error polling Telegram:", e)
                    await asyncio.sleep(5)
            
            return approved
        except Exception as e:
            print("Error en comunicación con Telegram:", e)
            return False

async def execute_bash(command: str) -> str:
    """Ejecuta un comando bash. Intercepta comandos destructivos o 'sudo' para HITL."""
    command = command.strip()
    
    destructive_keywords = ["rm ", "stop ", "kill ", "prune", "down", "restart ", "systemctl", "apt-get install", "apt remove"]
    
    requires_approval = False
    if command.startswith("sudo ") or " sudo " in command:
        requires_approval = True
    else:
        for kw in destructive_keywords:
            if kw in command:
                requires_approval = True
                break
                
    if requires_approval:
        print(f"Interceptado comando sensible: {command}")
        approved = await ask_telegram_approval(command)
        if not approved:
            return "SYSTEM_ERROR: El administrador ha denegado la ejecución de este comando o se alcanzó el timeout de aprobación."
            
    try:
        # Ejecución asíncrona del comando
        proc = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60.0)
            output = stdout.decode().strip()
            if stderr:
                output += f"\n[STDERR]:\n{stderr.decode().strip()}"
            if not output.strip():
                output = "Comando ejecutado con éxito (sin salida)."
            return output
        except asyncio.TimeoutError:
            proc.kill()
            return "Error de ejecución: Timeout de 60 segundos alcanzado para el proceso local."
            
    except Exception as e:
        return f"Error de ejecución: {str(e)}"

# Definición de la Tool
tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Ejecuta comandos de terminal/bash en el servidor Debian. Úsalo para revisar Docker, contenedores, logs, ZeroTier, o configuración del sistema. IMPORTANTE: Usa prefijo 'sudo' para tareas de administración.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando bash a ejecutar. Ej: 'docker ps' o 'sudo systemctl restart nginx'."
                    }
                },
                "required": ["command"]
            }
        }
    }
]

@app.post("/chat")
async def chat_endpoint(req: ChatMessage):
    if not req.message:
        raise HTTPException(status_code=400, detail="El mensaje no puede estar vacío")
        
    print(f"[{req.channel}] Mensaje recibido: {req.message}")
    
    client = get_openai_client()
    
    if req.channel == "it":
        return await handle_it_agent(req.message, client)
    elif req.channel == "hermes" or req.channel == "equivalencias":
        return await handle_equivalencias_agent(req.message, client)
    else:
        raise HTTPException(status_code=400, detail="Canal no soportado")

async def handle_it_agent(message: str, client: AsyncOpenAI):
    if not client.api_key:
        return {"response": "Error: Claves de API no configuradas."}
        
    messages = [
        {"role": "system", "content": """Eres el Especialista de Soporte IT de Synapse. Tu prioridad es la continuidad operativa de la Farmacia Americana.
Protocolo de Actuación:
Al recibir un reporte, realiza un diagnóstico silencioso (ping, docker logs, etc.).
Si el fallo es crítico (Base de datos caída), genera una alerta de alta prioridad.
Si puedes resolverlo con un comando de terminal (ej. reiniciar un contenedor), hazlo y reporta el éxito.
Si requiere intervención humana de Dario, crea un ticket con el siguiente formato JSON y envíalo al canal de Soporte:
ID_Ticket: (Autogenerado)
Gravedad: (Baja/Media/Crítica)
Sistema Afectado: (Red/Saint/Docker)
Diagnóstico Inicial: (Resumen técnico de 1 línea)"""},
        {"role": "user", "content": message}
    ]
    
    try:
        response = await client.chat.completions.create(
            model="deepseek/deepseek-chat",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        
        if response_message.tool_calls:
            messages.append(response_message)
            
            for tool_call in response_message.tool_calls:
                if tool_call.function.name == "execute_bash":
                    args = json.loads(tool_call.function.arguments)
                    cmd_result = await execute_bash(args["command"])
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "execute_bash",
                        "content": cmd_result
                    })
            
            final_response = await client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=messages
            )
            return {"response": final_response.choices[0].message.content}
        
        return {"response": response_message.content}
    except Exception as e:
        return {"response": f"Error del modelo de IA: {str(e)}"}

async def handle_equivalencias_agent(message: str, client: AsyncOpenAI):
    messages = [
        {"role": "system", "content": "Eres el agente:equivalencias. IMPORTANTE: Tu salida debe ser estrictamente un objeto JSON válido."},
        {"role": "user", "content": message}
    ]
    
    try:
        response = await client.chat.completions.create(
            model="deepseek/deepseek-v4-flash",
            messages=messages
        )
        content = response.choices[0].message.content
        cleaned_content = clean_json_response(content)
        
        try:
            json.loads(cleaned_content)
        except json.JSONDecodeError:
            print("El modelo no retornó un JSON válido incluso después de limpiar:", cleaned_content)
            
        return {"response": cleaned_content}
    except Exception as e:
        return {"response": f"Error del modelo de IA: {str(e)}"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
