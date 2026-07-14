import requests
import json

TELEGRAM_TOKEN = "8322313955:AAHwniwWZssrVuQBQGb1excjHKyZ2VQkkdE"
TELEGRAM_CHAT_ID = "-1003531406167"

url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

keyboard = {
    "inline_keyboard": [
        [
            {"text": "✅ Aprobar", "callback_data": "approve_sudo"},
            {"text": "❌ Denegar", "callback_data": "deny_sudo"}
        ]
    ]
}

payload = {
    "chat_id": TELEGRAM_CHAT_ID,
    "text": "⚠️ *Test de Integración*\n\n¿Funciona el botón?",
    "parse_mode": "Markdown",
    "reply_markup": keyboard
}

print("Enviando...")
resp = requests.post(url, json=payload).json()
print("Respuesta:", json.dumps(resp, indent=2))
