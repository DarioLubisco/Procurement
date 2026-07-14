import requests
import json

TELEGRAM_TOKEN = "8322313955:AAHwniwWZssrVuQBQGb1excjHKyZ2VQkkdE"
TELEGRAM_CHAT_ID = "-1002075553149"

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

payload = {
    "chat_id": TELEGRAM_CHAT_ID,
    "text": "⚠️ *Test de Integración a Grupo Dev*\n\n¿Llegó este mensaje?",
    "parse_mode": "Markdown"
}

resp = requests.post(url, json=payload).json()
print("Respuesta Grupo Dev:", json.dumps(resp, indent=2))
