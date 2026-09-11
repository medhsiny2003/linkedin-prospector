"""
Module de diagnostic et de vérification d'état (Health Checks).
Teste la connectivité DNS, l'intégrité de la base de données, la validité des logs et la session.
"""

import socket
import sqlite3
from typing import Any, Dict
from config import config
from core.browser.session_manager import session_manager
from core.monitoring.audit_logger import audit_logger


class HealthCheck:
    def check_dns(self) -> Dict[str, Any]:
        """Vérifie la capacité de résolution DNS du système."""
        try:
            ip = socket.gethostbyname("linkedin.com")
            return {"status": "OK", "details": f"Résolution DNS fonctionnelle (linkedin.com -> {ip})"}
        except Exception as e:
            return {"status": "ERROR", "details": f"Échec de résolution DNS : {e}"}

    def check_database(self) -> Dict[str, Any]:
        """Vérifie l'accessibilité de SQLite et le mode WAL."""
        try:
            config.DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(config.DATABASE_PATH))
            cursor = conn.cursor()
            cursor.execute("PRAGMA journal_mode=WAL;")
            mode = cursor.fetchone()[0]
            conn.close()
            return {"status": "OK", "details": f"Base SQLite opérationnelle (journal_mode={mode})"}
        except Exception as e:
            return {"status": "ERROR", "details": f"Erreur d'accès à SQLite : {e}"}

    def check_session(self) -> Dict[str, Any]:
        """Vérifie l'état du profil Chrome persistant."""
        has_session = session_manager.has_existing_session()
        return {
            "status": "OK" if has_session else "INFO",
            "details": "Session existante détectée" if has_session else "Nouvelle session (aucun profil stocké)"
        }

    def check_audit_log(self) -> Dict[str, Any]:
        """Vérifie l'intégrité cryptographique du journal d'audit."""
        is_valid = audit_logger.verify_integrity()
        return {
            "status": "OK" if is_valid else "ERROR",
            "details": "Chaîne de hash SHA-256 intègre et valide" if is_valid else "Altération ou corruption détectée dans audit.json"
        }

    def run_all_checks(self) -> Dict[str, Any]:
        """Exécute la suite complète de diagnostics."""
        results = {
            "dns": self.check_dns(),
            "database": self.check_database(),
            "session": self.check_session(),
            "audit_log": self.check_audit_log(),
            "proxy_configured": bool(config.PROXY_URL),
            "mcp_enabled": config.USE_MCP_SERVER
        }
        all_ok = all(r.get("status") in ("OK", "INFO") for k, r in results.items() if isinstance(r, dict))
        results["overall_health"] = "HEALTHY" if all_ok else "UNHEALTHY"
        return results


health_checker = HealthCheck()
