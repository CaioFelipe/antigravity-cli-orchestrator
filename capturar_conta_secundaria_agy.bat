@echo off
cd /d "%~dp0"
title Antigravity CLI - Captura da Conta Secundaria
cls
echo ====================================================================
echo      Antigravity CLI - Assistente de Captura da Conta Secundaria
echo ====================================================================
echo.
echo Diretorio do projeto: %CD%
echo.
echo Este script vai:
echo 1. Salvar o backup da sua Conta 1 (atual).
echo 2. Abrir a tela do Google no navegador para voce logar na CONTA 2.
echo    (Importante: No navegador, escolha 'Usar outra conta' ou coloque
echo     o e-mail e senha da sua CONTA SECUNDARIA).
echo 3. Capturar o token da Conta 2 e salvar em .agents\credentials\conta2.json.
echo 4. Restaurar a Conta 1 no seu computador imediatamente.
echo.
echo ====================================================================
echo Pressione qualquer tecla para comecar...
pause >nul
echo.
python ".agents\skills\cli-orchestrator\scripts\capture_secondary_account.py"
echo.
echo ====================================================================
echo Processo finalizado! Pressione qualquer tecla para fechar...
pause >nul
