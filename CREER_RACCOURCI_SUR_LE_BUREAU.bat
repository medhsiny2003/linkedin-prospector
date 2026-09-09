@echo off
chcp 65001 > nul
title Créer le Raccourci LinkedIn Prospector sur le Bureau

echo ===================================================================
echo   Création du raccourci LinkedIn Prospector sur votre Bureau...
echo ===================================================================
echo.

powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut(\"$([Environment]::GetFolderPath('Desktop'))\LinkedIn Prospector.lnk\"); $Shortcut.TargetPath = \"%~dp0LinkedIn-Prospector.bat\"; $Shortcut.WorkingDirectory = \"%~dp0\"; $Shortcut.Description = \"LinkedIn Prospector V3.2\"; $Shortcut.IconLocation = \"%%SystemRoot%%\System32\imageres.dll,114\"; $Shortcut.Save()"

if %errorlevel% equ 0 (
    echo [SUCCÈS] Le raccourci 'LinkedIn Prospector' a été créé sur votre Bureau !
) else (
    echo [ERREUR] Impossible de créer le raccourci automatiquement.
)

echo.
pause
