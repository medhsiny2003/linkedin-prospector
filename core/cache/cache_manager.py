"""
Gestionnaire de Cache Intelligent avec TTL (Time-To-Live).
Évite de re-scraper les mêmes entreprises plusieurs fois dans un intervalle de 7 jours,
réduisant drastiquement le volume de requêtes et protégeant les quotas.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import config
from core.monitoring.audit_logger import audit_logger


class CacheManager:
    def __init__(self, ttl_seconds: int = 43200):  # 12 heures par défaut (nouvelle session = nouveaux résultats)
        self.ttl = ttl_seconds
        self.cache_file = config.DATA_DIR / "search_cache.json"
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        """Charge le cache depuis le fichier JSON persisté."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}

    def _save_cache(self) -> None:
        """Sauvegarde le cache sur disque."""
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _generate_key(self, company: str, keywords: str, location: str) -> str:
        """Génère une clé normalisée pour la requête."""
        c = company.strip().lower()
        k = keywords.strip().lower()
        l = location.strip().lower()
        return f"{c}___{k}___{l}"

    def get(self, company: str, keywords: str, location: str = "") -> Optional[List[Dict[str, Any]]]:
        """Récupère les profils en cache si le TTL est encore valide."""
        key = self._generate_key(company, keywords, location)
        if key in self._cache:
            entry = self._cache[key]
            saved_at = entry.get("timestamp", 0)
            if time.time() - saved_at < self.ttl:
                data = entry.get("data", [])
                if data:
                    audit_logger.log_event("CACHE_HIT", f"Résultats récupérés depuis le cache ({len(data)} profils) : {company} - {keywords}")
                    return data
            else:
                # Expiré
                del self._cache[key]
                self._save_cache()
        return None

    def set(self, company: str, keywords: str, location: str, profiles: List[Dict[str, Any]]) -> None:
        """Enregistre une liste de profils en cache avec timestamp."""
        if not profiles:
            return
        key = self._generate_key(company, keywords, location)
        self._cache[key] = {
            "timestamp": time.time(),
            "data": profiles
        }
        self._save_cache()


cache_manager = CacheManager()