"""
Gestionnaire d'authentification fiable et transparent pour LinkedIn.
Gère l'accès direct par session active, la connexion propre avec injection multi-cookies,
la détection proactive des défis de sécurité (CAPTCHA / Checkpoint) avec guidage utilisateur en direct,
et l'auto-sauvegarde du cookie li_at dans .env.
"""

import asyncio
import random
from typing import Any, Callable, Optional, Tuple
from playwright.async_api import BrowserContext, Page
from config import config
from core.auth.cookie_manager import cookie_manager
from core.browser.session_manager import session_manager
from core.monitoring.audit_logger import audit_logger


class AuthManager:
    async def safe_goto(self, page: Page, url: str, timeout: int = 25000) -> bool:
        """
        Navigue vers une URL sans propager d'erreurs bloquantes.
        """
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await asyncio.sleep(1.5)
            return True
        except Exception as e:
            audit_logger.log_event("NAV_WARN", f"Navigation vers {url} : {e}")
            try:
                await page.goto(url, wait_until="commit", timeout=10000)
                await asyncio.sleep(1.5)
                return True
            except Exception:
                return False

    async def is_logged_in(self, page: Page) -> bool:
        """
        Vérifie si la page courante correspond à un utilisateur connecté sur LinkedIn.
        """
        try:
            current_url = page.url.lower()
            # Si on est sur une URL de connexion ou de vérification, on n'est pas encore connecté
            if any(bad in current_url for bad in ["/login", "/checkpoint", "/challenge", "/uas/authenticate", "/signup"]):
                return False

            # Si on est sur le fil, le réseau, les messages, les emplois ou la recherche
            if any(path in current_url for path in ["/feed", "/mynetwork", "/jobs", "/search", "/messaging", "/in/"]):
                return True

            # Vérification des sélecteurs de l'interface connectée
            selectors = [
                ".global-nav__me",
                "nav.global-nav",
                "button[aria-label*='Compte']",
                "button[aria-label*='Account']",
                "button[aria-label*='Me']",
                ".search-global-typeahead__input",
                "input[aria-label*='Recherche']",
                "input[aria-label*='Search']",
                "input[placeholder*='Recherche']",
                "input[placeholder*='Search']",
                ".feed-identity-module"
            ]
            for sel in selectors:
                elem = await page.query_selector(sel)
                if elem:
                    return True
        except Exception:
            pass
        return False

    def is_checkpoint_or_captcha(self, current_url: str) -> bool:
        """
        Détecte si la page actuelle est un défi de sécurité ou CAPTCHA.
        """
        lower_url = current_url.lower()
        checkpoint_signals = [
            "/checkpoint/",
            "/challenge/",
            "security-verification",
            "captcha",
            "identity/challenge",
            "checkpoint/challenge",
            "arkose"
        ]
        return any(sig in lower_url for sig in checkpoint_signals)

    async def authenticate(
        self,
        context: BrowserContext,
        page: Page,
        max_retries: int = 10,
        *args,
        **kwargs
    ) -> bool:
        """
        Stratégie d'authentification robuste sans blocage.
        """
        status_callback = kwargs.get("status_callback", None)
        if not status_callback and len(args) > 0:
            status_callback = args[0]

        def notify(msg: str):
            if status_callback and callable(status_callback):
                try:
                    status_callback(msg)
                except Exception:
                    pass

        audit_logger.log_event("AUTH_START", "Vérification de la session LinkedIn...")
        notify("🔍 Vérification de votre session LinkedIn...")

        # 1. Vérification si la session est déjà active (attente jusqu'à 5 secondes)
        await self.safe_goto(page, "https://www.linkedin.com/feed/")
        
        for _ in range(3):
            if await self.is_logged_in(page):
                audit_logger.log_event("AUTH_SUCCESS", "Compte déjà connecté dans Edge !")
                notify("✅ Compte LinkedIn connecté avec succès !")
                return True
            await asyncio.sleep(1.5)

        # 2. Si un cookie existe dans .env, injection complète multi-domaines
        li_at_val = cookie_manager.extract_li_at_value(config.LINKEDIN_COOKIE)
        if li_at_val:
            notify("🔑 Injection du cookie de session existant...")
            try:
                cookies_list = cookie_manager.format_playwright_cookies(li_at_val)
                await context.add_cookies(cookies_list)
                await self.safe_goto(page, "https://www.linkedin.com/feed/")
                await asyncio.sleep(2)

                if await self.is_logged_in(page):
                    audit_logger.log_event("AUTH_SUCCESS", "Connexion validée via le cookie !")
                    notify("✅ Connexion validée via le cookie !")
                    return True
            except Exception as e:
                audit_logger.log_event("AUTH_COOKIE_WARN", f"Erreur injection cookie : {e}")

        # 3. Ouverture de la page de connexion LinkedIn
        audit_logger.log_event("AUTH_LEVEL_3", "Ouverture de la page de connexion LinkedIn.")
        notify("👉 Connexion à LinkedIn en cours dans Edge...")
        await self.safe_goto(page, "https://www.linkedin.com/login/fr")
        await asyncio.sleep(2)

        # Pré-remplissage avec frappe humaine si identifiants configurés
        if config.LINKEDIN_EMAIL and config.LINKEDIN_PASSWORD:
            try:
                user_field = await page.wait_for_selector("#username, input[name='session_key']", timeout=6000)
                if user_field:
                    notify("✍️ Saisie sécurisée de vos identifiants...")
                    await user_field.click()
                    await asyncio.sleep(0.3)
                    # Saisie humaine caractère par caractère
                    for char in config.LINKEDIN_EMAIL:
                        await page.keyboard.type(char, delay=random.randint(50, 120))
                    await asyncio.sleep(0.4)
                    
                    pass_field = await page.wait_for_selector("#password, input[name='session_password']", timeout=5000)
                    if pass_field:
                        await pass_field.click()
                        await asyncio.sleep(0.3)
                        for char in config.LINKEDIN_PASSWORD:
                            await page.keyboard.type(char, delay=random.randint(50, 120))
                        await asyncio.sleep(0.5)
                        
                        submit_btn = await page.query_selector("button[type='submit'], button[data-litms-control-urn*='login']")
                        if submit_btn:
                            await submit_btn.click()
                        else:
                            await pass_field.press("Enter")
                        await asyncio.sleep(3)
            except Exception as e:
                audit_logger.log_event("AUTH_FILL_WARN", f"Saisie auto : {e}")

        # 4. Surveillance continue en direct avec détection de CAPTCHA / Défi de sécurité
        captcha_notified = False
        for second in range(120):  # 120 x 1.5s = 180s (3 minutes)
            await asyncio.sleep(1.5)
            current_url = page.url.lower()

            # Détection spécifique de CAPTCHA ou Checkpoint
            if self.is_checkpoint_or_captcha(current_url):
                if not captcha_notified:
                    audit_logger.log_event("CAPTCHA_DETECTED", f"Défi de sécurité détecté : {current_url}")
                    notify("⚠️ Vérification de sécurité / CAPTCHA détecté sur LinkedIn ! Veuillez le résoudre dans la fenêtre Edge ouverte...")
                    captcha_notified = True

            if await self.is_logged_in(page):
                audit_logger.log_event("AUTH_SUCCESS", "Connexion validée avec succès !")
                notify("🎉 Connexion validée ! Sauvegarde de la session...")
                
                # Sauvegarde du cookie li_at dans .env pour les prochaines sessions
                try:
                    extracted = await cookie_manager.get_li_at_from_context(context)
                    if extracted:
                        session_manager.save_cookie_to_env(extracted)
                except Exception:
                    pass

                notify("🚀 Démarrage immédiat de la prospection...")
                return True

        audit_logger.log_event("AUTH_FAILED", "Délai de connexion dépassé.")
        notify("❌ Délai de connexion dépassé.")
        return False


auth_manager = AuthManager()
