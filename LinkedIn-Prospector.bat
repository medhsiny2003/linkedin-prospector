@echo off
title LinkedIn Prospector V3.2
cd /d "%~dp0"

python server.py
if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo  Une erreur est survenue lors du lancement de Python.
    echo ========================================================
    pause
)
