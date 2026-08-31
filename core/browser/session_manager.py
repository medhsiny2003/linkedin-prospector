"""
Gestionnaire de persistance des sessions de navigation (Profil Edge / Chrome).
Garantit la conservation des cookies et la suppression des verrous résiduels (SingletonLock).
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional
from config import config
from core.monitoring.audit_logger import audit_logger


class SessionManager:
    def __init__(self, session_dir: Optional[Path] = None):
        self._session_dir = session_dir

    @property
    def session_dir(self) -> Path:
        """Retourne dynamiquement le chemin configuré pour la session."""
        return self._session_dir or config.SESSION_PATH

    def ensure_session_directory(self) -> Path:
        """Garantit l'existence du dossier de session et nettoie les verrous résiduels."""
        target_dir = self.session_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        self.clean_stale_locks()
        return target_dir

    def clean_stale_locks(self) -> None:
        """Nettoie les fichiers de verrouillage (SingletonLock) laissés par une fermeture forcée."""
        target_dir = self.session_dir
        lock_names = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile"]
        for lock_name in lock_names:
            lock_path = target_dir / lock_name
            if lock_path.exists():
                try:
                    if lock_path.is_file() or lock_path.is_symlink():
                        lock_path.unlink(missing_ok=True)
                except Exception:
                    pass

    def has_existing_session(self) -> bool:
        """Vérifie si des données de profil existent déjà."""
        target_dir = self.session_dir
        if not target_dir.exists():
            return False
        items = list(target_dir.glob("*"))
        return len(items) > 0

    def save_cookie_to_env(self, li_at_value: str) -> bool:
        """Enregistre automatiquement le cookie li_at valide dans le fichier .env."""
        if not li_at_value:
            return False
        env_path = Path(__file__).resolve().parent.parent.parent / ".env"
        try:
            content = ""
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    content = f.read()

            if "LINKEDIN_COOKIE=" in content:
                new_content = re.sub(
                    r"LINKEDIN_COOKIE=.*",
                    f'LINKEDIN_COOKIE="{li_at_value}"',
                    content
                )
            else:
                new_content = content.rstrip() + f'\nLINKEDIN_COOKIE="{li_at_value}"\n'

            with open(env_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            config.LINKEDIN_COOKIE = li_at_value
            audit_logger.log_event("SESSION_SAVED", "Nouveau cookie li_at persisté dans .env")
            return True
        except Exception as e:
            audit_logger.log_event("SESSION_WARN", f"Impossible d'écrire le cookie dans .env : {e}")
            return False

    def reset_session(self) -> bool:
        """Efface le dossier de session pour forcer une réinitialisation propre."""
        target_dir = self.session_dir
        try:
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            self.ensure_session_directory()
            audit_logger.log_event("SESSION_RESET", "Dossier de session réinitialisé avec succès.")
            return True
        except Exception as e:
            audit_logger.log_event("SESSION_ERROR", f"Échec de la réinitialisation de session : {e}")
            return False


session_manager = SessionManager()
