@echo off
title Antigravity & Claude Orchestrator Dashboard
cd /d "%~dp0"

echo =======================================================
echo    Iniciando Dashboard do Antigravity Orchestrator
echo =======================================================
echo.

:: Inicia o servidor Python em segundo plano se nao estiver rodando
netstat -ano | findstr :5050 >nul
if %errorlevel% neq 0 (
    echo [INFO] Iniciando servidor web local na porta 5050...
    start /B python .agents\skills\cli-orchestrator\scripts\dashboard_server.py
    timeout /t 2 /nobreak >nul
) else (
    echo [INFO] Servidor web ja esta em execucao na porta 5050.
)

echo [OK] Abrindo navegador em http://localhost:5050 ...
start http://localhost:5050

echo.
echo Dashboard ativo! Voce pode fechar esta janela a qualquer momento.
timeout /t 3 >nul
exit
