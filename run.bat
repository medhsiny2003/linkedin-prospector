@echo off
chcp 65001 > nul
title LinkedIn Prospector V3.2

echo ========================================================
echo        LinkedIn Prospector V3.2 - Lancement Direct
echo ========================================================
echo.

cd /d "%~dp0"

:: Vérifier si Python est installé
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Python n'est pas détecté dans le PATH.
    echo Veuillez installer Python 3.11+ et l'ajouter au PATH.
    pause
    exit /b 1
)

:: Vérifier le fichier .env
if not exist ".env" (
    echo [ATTENTION] Fichier .env manquant. Copie depuis .env.example...
    copy .env.example .env
)

echo [INFO] Démarrage du pipeline de prospection...
echo.

python main.py --config config/default.json

echo.
echo ========================================================
echo [INFO] Traitement terminé ou interrompu.
echo ========================================================
pause
