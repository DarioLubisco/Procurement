@echo off
TITLE Synapse Business Suite - Local Server
echo [INFO] Iniciando Synapse Central Localmente...
cd /d %~dp0backend
echo [INFO] Verificando dependencias...
pip install -r requirements.txt
echo [INFO] Lanzando servidor Uvicorn en http://localhost:8000
python main.py
pause
