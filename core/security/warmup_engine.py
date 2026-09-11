"""
Moteur de Warm-Up progressif sur 14 jours.
Régule les quotas journaliers et impose le respect des horaires de travail français.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Any, Optional, Tuple, Union
from config import config
from core.monitoring.audit_logger import audit_logger

try:
    import zoneinfo
    try:
        PARIS_TZ = zoneinfo.ZoneInfo(config.TIMEZONE)
    except Exception:
        # Fallback pour Windows si tzdata n'est pas encore installé (UTC+1 ou UTC+2)
        PARIS_TZ = timezone(timedelta(hours=1))
except Exception:
    PARIS_TZ = timezone(timedelta(hours=1))


class WarmupEngine:
    def __init__(self):
        self.timezone = PARIS_TZ

    def get_current_paris_time(self) -> datetime:
        """Retourne l'heure courante sur le fuseau horaire de Paris."""
        return datetime.now(self.timezone)

    def is_within_working_hours(self) -> Tuple[bool, str]:
        """
        Vérifie si l'heure actuelle est comprise dans la plage autorisée.
        Par défaut : 24/7 activé sans restriction horaire.
        """
        now = self.get_current_paris_time()
        
        # Vérification du week-end
        if getattr(config, "RESTRICT_WEEKENDS", False) and now.weekday() in (5, 6):
            msg = f"Activité bloquée : Le week-end est exclu ({now.strftime('%A')})."
            return False, msg

        if getattr(config, "RESTRICT_WORKING_HOURS", False):
            current_hour = now.hour
            if not (config.WARMUP_HOURS_START <= current_hour < config.WARMUP_HOURS_END):
                msg = (
                    f"Activité bloquée : En dehors des heures ouvrées "
                    f"({config.WARMUP_HOURS_START}h00 - {config.WARMUP_HOURS_END}h00 Paris). Heure actuelle : {now.strftime('%H:%M')}."
                )
                return False, msg

        return True, "Prospection 24/7 active (toutes heures autorisées)."

    def calculate_daily_limit(self, campaign_start_date: Any = None) -> int:
        """
        Calcule la limite d'invitations journalières en fonction de l'ancienneté (14 jours).
        Supporte un objet date, datetime, str, int (numéro de jour) ou None.
        - Jours 1-3 : 0 (navigation passive)
        - Jours 4-7 : 2 à 5
        - Jours 8-14 : 5 à 18
        - > 14 jours : DAILY_CONNECT_LIMIT (max 20)
        """
        today = self.get_current_paris_time().date()
        if isinstance(campaign_start_date, int):
            days_active = campaign_start_date
        elif isinstance(campaign_start_date, datetime):
            days_active = (today - campaign_start_date.date()).days + 1
        elif isinstance(campaign_start_date, date):
            days_active = (today - campaign_start_date).days + 1
        elif isinstance(campaign_start_date, str):
            try:
                dt = datetime.fromisoformat(campaign_start_date).date()
                days_active = (today - dt).days + 1
            except Exception:
                days_active = 1
        else:
            days_active = 1

        if days_active <= 3:
            daily_limit = 0
            phase = "Phase 1 (J1-J3) : Mode passif pur (0 invitation)"
        elif 4 <= days_active <= 7:
            # Progression de 2 à 5
            step = (days_active - 4) / 3.0
            daily_limit = int(2 + step * 3)
            phase = f"Phase 2 (J4-J7) : Montée douce (limite : {daily_limit})"
        elif 8 <= days_active <= 14:
            # Progression de 5 à 18
            step = (days_active - 8) / 6.0
            daily_limit = int(5 + step * 13)
            phase = f"Phase 3 (J8-J14) : Montée progressive (limite : {daily_limit})"
        else:
            daily_limit = config.DAILY_CONNECT_LIMIT
            phase = f"Régime permanent (> 14 jours, limite max : {daily_limit})"

        # Sécurité absolue : ne jamais dépasser la limite maximale configurée
        daily_limit = min(daily_limit, config.DAILY_CONNECT_LIMIT)
        audit_logger.log_event("WARMUP_CALCULATION", f"Jour {days_active} - {phase}", {"daily_limit": daily_limit})
        return daily_limit


warmup_engine = WarmupEngine()
