"""
Système de journalisation sécurisé et infalsifiable (Tamper-Evident).
Chaque événement est lié au précédent par un hachage cryptographique SHA-256 en chaîne.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import config

# Configuration du logging standard pour la console
logger = logging.getLogger("LinkedInProspector")
logger.setLevel(logging.INFO)
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    ch.setFormatter(formatter)
    logger.addHandler(ch)


class AuditLogger:
    def __init__(self, log_path: Optional[Path] = None):
        self.log_path = log_path or config.AUDIT_LOG_PATH
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Initialise le fichier de log avec un bloc Genesis si vide."""
        if not self.log_path.exists() or self.log_path.stat().st_size == 0:
            genesis_event = {
                "index": 0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "event_type": "GENESIS",
                "message": "Initialisation du journal d'audit cryptographique",
                "data": {},
                "previous_hash": "0" * 64
            }
            genesis_event["hash"] = self._compute_hash(genesis_event)
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([genesis_event], f, indent=2, ensure_ascii=False)

    def _compute_hash(self, event_dict: Dict[str, Any]) -> str:
        """Calcule le hash SHA-256 des données de l'événement."""
        payload = (
            f"{event_dict['index']}|"
            f"{event_dict['timestamp']}|"
            f"{event_dict['event_type']}|"
            f"{event_dict['message']}|"
            f"{json.dumps(event_dict['data'], sort_keys=True)}|"
            f"{event_dict['previous_hash']}"
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def log_event(self, event_type: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Enregistre un événement auditable dans la chaîne cryptographique.
        """
        data = data or {}
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                chain: List[Dict[str, Any]] = json.load(f)
        except Exception:
            chain = []

        if not chain:
            previous_hash = "0" * 64
            next_index = 0
        else:
            previous_hash = chain[-1].get("hash", "0" * 64)
            next_index = len(chain)

        event = {
            "index": next_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "message": message,
            "data": data,
            "previous_hash": previous_hash
        }
        event["hash"] = self._compute_hash(event)
        chain.append(event)

        with open(self.log_path, "w", encoding="utf-8") as f:
            json.dump(chain, f, indent=2, ensure_ascii=False)

        # Affichage console formaté
        level = logging.WARNING if "RISK" in event_type or "WARN" in event_type else logging.INFO
        logger.log(level, f"[{event_type}] {message}")
        return event

    def verify_integrity(self) -> bool:
        """
        Vérifie la validité de l'intégralité de la chaîne d'audit.
        Retourne True si aucun bloc n'a été altéré.
        """
        if not self.log_path.exists():
            return False

        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                chain: List[Dict[str, Any]] = json.load(f)
        except Exception as e:
            logger.error(f"Erreur de lecture du journal d'audit : {e}")
            return False

        if not chain:
            return False

        expected_prev_hash = "0" * 64
        for idx, event in enumerate(chain):
            if event.get("index") != idx:
                logger.error(f"Index invalide au bloc {idx}")
                return False
            if event.get("previous_hash") != expected_prev_hash:
                logger.error(f"Rupture de chaîne de hash au bloc {idx}")
                return False

            calculated_hash = self._compute_hash(event)
            if event.get("hash") != calculated_hash:
                logger.error(f"Hash falsifié ou invalide au bloc {idx}")
                return False

            expected_prev_hash = calculated_hash

        return True


audit_logger = AuditLogger()
