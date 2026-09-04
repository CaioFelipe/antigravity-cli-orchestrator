@echo off
cd /d "%~dp0"
title agyclaude - Autenticacao Google Antigravity
cls
echo ====================================================================
echo      agyclaude - Login OAuth do Google Antigravity
echo ====================================================================
echo.
echo Este script vai abrir o seu navegador para conectar uma conta Google
echo ao proxy do agyclaude.
echo.
echo (Voce pode escolher qualquer conta Google com acesso ao Antigravity).
echo.
echo ====================================================================
echo Pressione qualquer tecla para abrir o login no navegador...
pause >nul
echo.
call antigravity-claude-proxy accounts add
echo.
echo ====================================================================
echo Verificando status do agyclaude...
call agyclaude --agy-status
echo.
echo Processo finalizado! Pressione qualquer tecla para fechar...
pause >nul
