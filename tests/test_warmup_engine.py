"""
Tests unitaires pour le moteur de Warm-up sur 14 jours.
"""

from datetime import date, timedelta
from core.security.warmup_engine import warmup_engine


def test_warmup_schedule_progression():
    today = date.today()

    # Jour 1 (Ancienneté 0 jour) : Limite 0
    lim_j1 = warmup_engine.calculate_daily_limit(campaign_start_date=today)
    assert lim_j1 == 0

    # Jour 5 (Ancienneté 4 jours) : Phase douce (2 à 5)
    lim_j5 = warmup_engine.calculate_daily_limit(campaign_start_date=today - timedelta(days=4))
    assert 2 <= lim_j5 <= 5

    # Jour 10 (Ancienneté 9 jours) : Phase progressive (5 à 18)
    lim_j10 = warmup_engine.calculate_daily_limit(campaign_start_date=today - timedelta(days=9))
    assert 5 <= lim_j10 <= 18

    # Jour 20 (Régime permanent > 14 jours) : Max 20
    lim_j20 = warmup_engine.calculate_daily_limit(campaign_start_date=today - timedelta(days=19))
    assert lim_j20 == 20
