"""
Gestionnaire de cadencement et de simulation de comportements humains réalistes.
Délais lognormaux, mouvements de souris à courbes de Bézier et défilement avec pauses.
"""

import asyncio
import math
import random
import time
from typing import Any
from config import config
from core.monitoring.audit_logger import audit_logger


class RateLimiter:
    def __init__(self):
        self.action_count = 0
        self.next_pause_threshold = random.randint(
            config.ACTION_BATCH_SIZE_MIN, config.ACTION_BATCH_SIZE_MAX
        )

    def get_lognormal_delay(self, median_sec: float = 6.0, sigma: float = 0.5) -> float:
        """
        Génère un délai aléatoire suivant une distribution lognormale.
        Imite les temps de réaction et de lecture humains.
        """
        # Pour une distribution lognormale, mu = ln(median)
        mu = math.log(median_sec)
        delay = random.lognormvariate(mu, sigma)
        # Tronquer aux bornes configurées
        delay = max(config.REQUEST_DELAY_MIN, min(delay, config.REQUEST_DELAY_MAX * 2))
        return delay

    async def wait_human_delay(self, median_sec: float = 5.0) -> None:
        """Attend un délai aléatoire lognormal."""
        delay = self.get_lognormal_delay(median_sec=median_sec)
        await asyncio.sleep(delay)

    async def check_and_apply_batch_pause(self) -> None:
        """
        Vérifie si une pause longue (20 à 60 minutes) doit être effectuée
        après une série de 3 à 7 actions.
        """
        self.action_count += 1
        if self.action_count >= self.next_pause_threshold:
            pause_duration = random.randint(
                config.LONG_PAUSE_MIN_SECONDS, config.LONG_PAUSE_MAX_SECONDS
            )
            audit_logger.log_event(
                "BATCH_PAUSE",
                f"Pause humaine de sécurité déclenchée après {self.action_count} actions. Durée: {pause_duration // 60} min."
            )
            # Réinitialisation du compteur et du prochain palier
            self.action_count = 0
            self.next_pause_threshold = random.randint(
                config.ACTION_BATCH_SIZE_MIN, config.ACTION_BATCH_SIZE_MAX
            )
            await asyncio.sleep(pause_duration)

    async def simulate_human_mouse_move(self, page: Any, target_x: float, target_y: float) -> None:
        """
        Déplace la souris vers une cible en décrivant une courbe avec micro-oscillations (wobble).
        """
        try:
            current_x = random.randint(100, 300)
            current_y = random.randint(100, 300)
            steps = random.randint(15, 25)

            # Point de contrôle intermédiaire pour une courbe de Bézier quadratique
            control_x = (current_x + target_x) / 2 + random.randint(-80, 80)
            control_y = (current_y + target_y) / 2 + random.randint(-80, 80)

            for step in range(1, steps + 1):
                t = step / steps
                # Formule de Bézier quadratique : B(t) = (1-t)^2*P0 + 2(1-t)t*P1 + t^2*P2
                x = (1 - t) ** 2 * current_x + 2 * (1 - t) * t * control_x + t ** 2 * target_x
                y = (1 - t) ** 2 * current_y + 2 * (1 - t) * t * control_y + t ** 2 * target_y

                # Micro wobble (tremblement humain)
                wobble_x = x + random.uniform(-1.5, 1.5)
                wobble_y = y + random.uniform(-1.5, 1.5)

                await page.mouse.move(wobble_x, wobble_y)
                await asyncio.sleep(random.uniform(0.01, 0.03))
        except Exception:
            pass

    async def simulate_human_scroll(self, page: Any, min_scrolls: int = 3, max_scrolls: int = 6) -> None:
        """
        Défile la page par à-coups réalistes avec retours arrière occasionnels et pauses de lecture.
        """
        try:
            num_scrolls = random.randint(min_scrolls, max_scrolls)
            for _ in range(num_scrolls):
                scroll_delta = random.randint(250, 600)
                await page.mouse.wheel(0, scroll_delta)
                await asyncio.sleep(random.uniform(0.8, 2.2))

                # 20% de chance d'un micro retour arrière (comme pour relire)
                if random.random() < 0.20:
                    await page.mouse.wheel(0, -random.randint(80, 200))
                    await asyncio.sleep(random.uniform(0.5, 1.2))
        except Exception:
            pass


rate_limiter = RateLimiter()
