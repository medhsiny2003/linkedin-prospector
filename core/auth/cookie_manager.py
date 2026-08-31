"""
Gestionnaire et formateur de cookies d'authentification LinkedIn (notamment li_at).
"""

import re
from typing import Any, Dict, List, Optional
from config import config
from core.monitoring.audit_logger import audit_logger


class CookieManager:
    @staticmethod
    def extract_li_at_value(raw_cookie: Optional[str]) -> Optional[str]:
        """
        Extrait la valeur brute du cookie li_at depuis une chaîne ou un en-tête.
        Gère les formats: 'li_at=AQED...', 'AQED...', ou 'li_at=AQED...; JSESSIONID=...'
        """
        if not raw_cookie:
            return None

        clean_cookie = raw_cookie.strip().strip('"').strip("'")
        if "li_at=" in clean_cookie:
            match = re.search(r'li_at="?([a-zA-Z0-9_\-\.]+)"?', clean_cookie)
            if match:
                return match.group(1).strip()

        if len(clean_cookie) > 20 and not "=" in clean_cookie:
            return clean_cookie

        return None

    @classmethod
    def format_playwright_cookies(cls, cookie_value: str) -> List[Dict[str, Any]]:
        """
        Formate les cookies nécessaires pour LinkedIn (.linkedin.com et .www.linkedin.com).
        """
        val = cls.extract_li_at_value(cookie_value) or cookie_value.strip().strip('"').strip("'")
        return [
            {
                "name": "li_at",
                "value": val,
                "domain": ".linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Lax"
            },
            {
                "name": "li_at",
                "value": val,
                "domain": ".www.linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": True,
                "sameSite": "Lax"
            },
            {
                "name": "JSESSIONID",
                "value": '"ajax:0"',
                "domain": ".www.linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "Lax"
            },
            {
                "name": "JSESSIONID",
                "value": '"ajax:0"',
                "domain": ".linkedin.com",
                "path": "/",
                "secure": True,
                "httpOnly": False,
                "sameSite": "Lax"
            }
        ]

    @classmethod
    def format_playwright_cookie(cls, cookie_value: str) -> Dict[str, Any]:
        """Méthode de compatibilité unitaire."""
        val = cls.extract_li_at_value(cookie_value) or cookie_value.strip().strip('"').strip("'")
        return {
            "name": "li_at",
            "value": val,
            "domain": ".linkedin.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "Lax"
        }

    @staticmethod
    async def get_li_at_from_context(context: Any) -> Optional[str]:
        """Récupère le cookie li_at depuis le contexte de navigation Playwright actif."""
        try:
            cookies = await context.cookies(["https://www.linkedin.com", "https://www.linkedin.com/feed/"])
            for c in cookies:
                if c.get("name") == "li_at":
                    return c.get("value")
        except Exception as e:
            audit_logger.log_event("COOKIE_ERROR", f"Impossible d'extraire li_at du contexte : {e}")
        return None


cookie_manager = CookieManager()
