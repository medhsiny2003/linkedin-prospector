@echo off
chcp 65001 > nul
title LinkedIn Prospector V3.2 - Menu Principal

cd /d "%~dp0"

:menu
cls
echo ===================================================================
echo                     LinkedIn Prospector V3.2
echo ===================================================================
echo.
echo   [1] Lancer la prospection (Scraper + Enrichissement + Export)
echo   [2] Reprendre la dernière session interrompue (--resume)
echo   [3] Ouvrir l'Interface Graphique Web (app/index.html)
echo   [4] Lancer les Tests Unitaires (pytest)
echo   [5] Installer/Mettre à jour les dépendances (pip + playwright)
echo   [6] Ouvrir le dossier des résultats (output/)
echo   [0] Quitter
echo.
echo ===================================================================
set /p choice="Votre choix [0-6] : "

if "%choice%"=="1" goto run_scraper
if "%choice%"=="2" goto resume_scraper
if "%choice%"=="3" goto open_ui
if "%choice%"=="4" goto run_tests
if "%choice%"=="5" goto install_deps
if "%choice%"=="6" goto open_output
if "%choice%"=="0" goto exit_app

echo Choix invalide.
timeout /t 2 > nul
goto menu

:run_scraper
cls
echo [INFO] Démarrage de la prospection avec config/default.json...
echo.
python main.py --config config/default.json
echo.
pause
goto menu

:resume_scraper
cls
echo [INFO] Reprise depuis le dernier checkpoint...
echo.
python main.py --config config/default.json --resume
echo.
pause
goto menu

:open_ui
cls
echo [INFO] Ouverture de l'interface utilisateur dans votre navigateur...
start "" "%~dp0app\index.html"
timeout /t 2 > nul
goto menu

:run_tests
cls
echo [INFO] Exécution de la suite de tests unitaires...
echo.
python -m pytest tests/ -v
echo.
pause
goto menu

:install_deps
cls
echo [INFO] Installation des dépendances Python...
pip install -r requirements.txt
playwright install chromium
echo.
echo [INFO] Dépendances installées avec succès.
pause
goto menu

:open_output
if not exist "output" mkdir output
start "" "%~dp0output"
goto menu

:exit_app
exit /b 0
