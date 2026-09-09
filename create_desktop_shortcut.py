"""Create desktop shortcut for LinkedIn Prospector V3.2."""

import os
import sys
import subprocess

def create_shortcut():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    bat_target = os.path.join(base_dir, "LinkedIn-Prospector.bat")
    
    desktop_dir = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop_dir, "LinkedIn Prospector.lnk")
    
    ps_cmd = f"""
    $WshShell = New-Object -comObject WScript.Shell;
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}');
    $Shortcut.TargetPath = '{bat_target}';
    $Shortcut.WorkingDirectory = '{base_dir}';
    $Shortcut.Description = 'LinkedIn Prospector V3.2';
    $Shortcut.IconLocation = '%SystemRoot%\\System32\\imageres.dll,114';
    $Shortcut.Save();
    """
    
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], check=True)
        print(f"[OK] Raccourci cree sur le bureau : {shortcut_path}")
    except Exception as e:
        print(f"[ERREUR] Impossible de creer le raccourci : {e}")

if __name__ == "__main__":
    create_shortcut()
