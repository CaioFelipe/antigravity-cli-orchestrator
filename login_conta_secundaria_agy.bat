@echo off
title Antigravity CLI - Login da Conta Secundaria
echo ========================================================
echo   Antigravity CLI - Autenticando Conta Secundaria
echo ========================================================
echo.
set GEMINI_CONFIG_DIR=%USERPROFILE%\.gemini\antigravity-cli-secondary
echo Usando diretorio isolado: %GEMINI_CONFIG_DIR%
echo.
echo Abrindo navegador para autenticacao...
"%LOCALAPPDATA%\agy\bin\agy.exe"
pause
