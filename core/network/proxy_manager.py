"""
Gestionnaire de Proxies Résidentiels en Rotation.
Permet de distribuer les requêtes sur un pool d'adresses IP pour éviter les blocages de datacenters.
"""

import os
import random
from typing import Dict, List, Optional
from config import config
from core.monitoring.audit_logger import audit_logger


class ProxyManager:
    def __init__(self):
        self.proxies: List[str] = []
        self._load_proxies()

    def _load_proxies(self) -> None:
        """Charge les proxies depuis .env ou variable d'environnement."""
        raw_proxy = os.getenv("PROXY_URL") or getattr(config, "PROXY_URL", "")
        if raw_proxy and raw_proxy.strip():
            # Support des listes de proxies séparées par des virgules ou points-virgules
            self.proxies = [p.strip() for p in raw_proxy.replace(";", ",").split(",") if p.strip()]

    def get_random_proxy(self) -> Optional[str]:
        """Retourne un proxy aléatoire du pool ou None si aucun configuré."""
        if not self.proxies:
            return None
        selected = random.choice(self.proxies)
        audit_logger.log_event("PROXY_ROTATE", f"Utilisation du proxy : {selected.split('@')[-1] if '@' in selected else selected}")
        return selected

    def get_playwright_proxy_dict(self) -> Optional[Dict[str, str]]:
        """Retourne le format attendu par Playwright launch(proxy=...)."""
        proxy_url = self.get_random_proxy()
        if not proxy_url:
            return None
        
        # Format: http://user:pass@host:port ou http://host:port
        server = proxy_url
        username = None
        password = None

        if "@" in proxy_url:
            parts = proxy_url.split("@")
            server_part = parts[1]
            auth_part = parts[0].replace("http://", "").replace("https://", "")
            server = f"http://{server_part}"
            if ":" in auth_part:
                username, password = auth_part.split(":", 1)

        proxy_dict = {"server": server}
        if username and password:
            proxy_dict["username"] = username
            proxy_dict["password"] = password

        return proxy_dict


proxy_manager = ProxyManager()