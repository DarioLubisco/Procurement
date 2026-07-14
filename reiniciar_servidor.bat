@echo off
cls
echo ===================================================
echo     REINICIANDO SERVIDOR LOCAL SYNAPSE
echo ===================================================
echo.
echo [1] Deteniendo procesos viejos...
taskkill /IM "python.exe" /F >nul 2>&1
taskkill /IM "uvicorn.exe" /F >nul 2>&1

echo.
echo [2] Esperando 3 segundos...
timeout /t 3 /nobreak > NUL

echo.
echo [3] Iniciando servidor con Python 3.13...
cd /d "C:\source\Synapse\backend"
start "Synapse API" cmd /k ""C:\Users\DARIO LUBISCO\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"

echo.
echo [4] Abriendo el navegador en 3 segundos...
timeout /t 3 /nobreak > NUL
start http://localhost:8000/modulo_caja.html

echo.
echo ===================================================
echo   Servidor iniciado. Puerto: 8000
echo ===================================================
pause
