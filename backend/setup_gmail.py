"""
Script de configuración de Gmail API.
Ejecutar UNA SOLA VEZ desde la consola para autorizar el acceso.
Genera token.json que el servidor usará para enviar correos.

Para usar:
1. Ve a https://console.cloud.google.com/
2. Crea un proyecto (o usa uno existente)
3. Activa la Gmail API
4. En "Credenciales" → "Crear credenciales" → "ID de cliente de OAuth"
5. Tipo: "Aplicación de escritorio", descarga el JSON
6. Guárdalo como credentials.json en esta carpeta
7. Ejecuta: .venv\\Scripts\\python.exe setup_gmail.py
"""

import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def main():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("ERROR: No se encontró credentials.json")
                print("Descárgalo de Google Cloud Console y guárdalo como credentials.json")
                return
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
        print("✅ token.json generado exitosamente. El servidor está autorizado para enviar correos.")
    else:
        print("✅ Ya hay un token válido en token.json")

if __name__ == '__main__':
    main()
