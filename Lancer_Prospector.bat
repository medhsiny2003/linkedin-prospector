@echo off
title LinkedIn Prospector V3.1
color 0B
cls
echo ==============================================================================
echo                      LINKEDIN PROSPECTOR V3.1
echo       Assistant Intelligent de Prospection B2B ^& Candidatures de Stage
echo ==============================================================================
echo.
echo  [*] Verification de Python et Streamlit...
echo  [*] Lancement de l'interface graphique...
echo.

cd /d "%~dp0"
start "" "http://localhost:8501"
"%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -m streamlit run app/streamlit_app.py --server.headless=false --server.port=8501

pause