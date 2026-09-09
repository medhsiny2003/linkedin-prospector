@echo off
chcp 65001 > nul
title LinkedIn Prospector V3.2

echo ===================================================================
echo               🚀 LinkedIn Prospector V3.2
echo ===================================================================
echo.
echo [1/2] Démarrage du serveur et de l'interface graphique...

cd /d "%~dp0"

:: Vérifier si Python est présent
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'a pas été trouvé dans le PATH système.
    echo Veuillez installer Python 3.11+ depuis https://www.python.org/
    pause
    exit /b 1
)

:: Lancer le serveur d'application Web
echo [2/2] Ouverture de l'application dans votre navigateur...
echo.
echo 💡 Vous pouvez fermer cette fenêtre pour arrêter l'application.
echo.

python server.py

pause
