import os
from openai import OpenAI
from dotenv import load_dotenv
import json

load_dotenv("c:\\source\\Synapse\\backend\\.env")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "execute_bash",
            "description": "Ejecuta comandos de terminal/bash en el servidor Debian. Úsalo para revisar Docker, logs o configuración.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "El comando bash a ejecutar. Ej: 'docker ps'"
                    }
                },
                "required": ["command"]
            }
        }
    }
]

messages = [
    {"role": "system", "content": "Eres el Sub-agente IT. Tienes la herramienta 'execute_bash'. Úsala obligatoriamente para responder si te piden un comando."},
    {"role": "user", "content": "ejecuta sudo docker ps"}
]

try:
    response = client.chat.completions.create(
        model="deepseek/deepseek-chat",
        messages=messages,
        tools=tools,
        tool_choice="auto"
    )
    
    msg = response.choices[0].message
    print("Content:", msg.content)
    if msg.tool_calls:
        print("Tool calls:", [t.function.name for t in msg.tool_calls])
        print("Args:", [t.function.arguments for t in msg.tool_calls])
    else:
        print("No tool calls made.")
except Exception as e:
    print("Error:", e)
