"""
Détecteur de risques et coupe-circuit anti-bannissement.
Intercepte les CAPTCHA, pages de vérification (checkpoint) et codes HTTP anormaux.
"""

from typing import Optional, Tuple
from core.monitoring.audit_logger import audit_logger


class RiskDetector:
    def __init__(self):
        self.checkpoint_keywords = [
            "/checkpoint/",
            "/challenge/",
            "security-verification",
            "captcha",
            "identity/challenge",
            "checkpoint/challenge",
            "login-submit"
        ]
        self.rate_limit_keywords = [
            "too many requests",
            "please try again later",
            "unusual activity",
            "compte temporairement restreint"
        ]

    def assess_risk(
        self,
        current_url: str,
        page_content: str = "",
        status_code: Optional[int] = None
    ) -> Tuple[bool, str]:
        """
        Analyse l'état actuel pour déceler tout signal d'alarme de LinkedIn.
        Retourne (is_risk, explanation).
        """
        # 1. Vérification des codes HTTP de blocage
        if status_code in (429, 999):
            msg = f"Code HTTP critique détecté : {status_code} (Rate limit / Blocage LinkedIn)"
            audit_logger.log_event("SECURITY_RISK_HTTP", msg, {"status_code": status_code, "url": current_url})
            return True, msg

        # 2. Vérification des URLs de checkpoint
        lower_url = current_url.lower()
        for kw in self.checkpoint_keywords:
            if kw in lower_url:
                msg = f"URL de vérification ou CAPTCHA détectée : {kw} dans {current_url}"
                audit_logger.log_event("SECURITY_RISK_CHECKPOINT", msg, {"url": current_url})
                return True, msg

        # 3. Vérification du contenu texte
        lower_content = page_content.lower()
        for kw in self.rate_limit_keywords:
            if kw in lower_content:
                msg = f"Message d'alerte détecté dans la page : '{kw}'"
                audit_logger.log_event("SECURITY_RISK_CONTENT", msg, {"keyword": kw, "url": current_url})
                return True, msg

        return False, "Aucun risque détecté."


risk_detector = RiskDetector()
