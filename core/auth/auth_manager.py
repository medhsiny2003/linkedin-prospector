"""
Gestionnaire d'authentification fiable et transparent pour LinkedIn.
Gère l'accès direct par session active, la connexion propre sans suppression de cookies,
et l'auto-sauvegarde du cookie dans .env.
"""

import asyncio
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
            # Si on est sur le fil, le réseau, les messages, les emplois ou la recherche
            if any(path in current_url for path in ["/feed", "/mynetwork", "/jobs", "/search", "/messaging", "/in/"]):
                if not any(bad in current_url for bad in ["/login", "/checkpoint", "/uas/authenticate", "/signup"]):
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

    async def authenticate(
        self,
        context: BrowserContext,
        page: Page,
        max_retries: int = 10,
        *args,
        **kwargs
    ) -> bool:
        """
        Stratégie d'authentification robuste sans suppression de cookies.
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

        # 1. Vérification si la session est déjà active (attente jusqu'à 6 secondes)
        await self.safe_goto(page, "https://www.linkedin.com/feed/")
        
        for _ in range(3):
            if await self.is_logged_in(page):
                audit_logger.log_event("AUTH_SUCCESS", "Compte déjà connecté dans Edge !")
                notify("✅ Compte LinkedIn connecté avec succès !")
                return True
            await asyncio.sleep(1.5)

        # 2. Si un cookie existe dans .env, tentative d'injection propre
        li_at_val = cookie_manager.extract_li_at_value(config.LINKEDIN_COOKIE)
        if li_at_val:
            notify("🔑 Test du cookie de session existant...")
            try:
                cookie_dict = cookie_manager.format_playwright_cookie(li_at_val)
                await context.add_cookies([cookie_dict])
                await self.safe_goto(page, "https://www.linkedin.com/feed/")
                await asyncio.sleep(2)

                if await self.is_logged_in(page):
                    audit_logger.log_event("AUTH_SUCCESS", "Connexion validée via le cookie !")
                    notify("✅ Connexion validée via le cookie !")
                    return True
            except Exception:
                pass

        # 3. Ouverture de la page de connexion LinkedIn
        audit_logger.log_event("AUTH_LEVEL_3", "Ouverture de la page de connexion LinkedIn.")
        notify("👉 Connexion à LinkedIn en cours...")
        await self.safe_goto(page, "https://www.linkedin.com/login/fr")
        await asyncio.sleep(2)

        # Pré-remplissage et soumission automatique si identifiants configurés
        if config.LINKEDIN_EMAIL and config.LINKEDIN_PASSWORD:
            try:
                user_field = await page.wait_for_selector("#username, input[name='session_key']", timeout=8000)
                if user_field:
                    notify("🤖 Saisie automatique de vos identifiants...")
                    await user_field.fill(config.LINKEDIN_EMAIL)
                    await asyncio.sleep(0.5)
                    
                    pass_field = await page.wait_for_selector("#password, input[name='session_password']", timeout=5000)
                    if pass_field:
                        await pass_field.fill(config.LINKEDIN_PASSWORD)
                        await asyncio.sleep(0.5)
                        
                        submit_btn = await page.query_selector("button[type='submit'], button[data-litms-control-urn*='login']")
                        if submit_btn:
                            await submit_btn.click()
                        else:
                            await pass_field.press("Enter")
                        await asyncio.sleep(3)
            except Exception as e:
                audit_logger.log_event("AUTH_FILL_WARN", f"Saisie auto : {e}")

        # Surveillance continue : courte en mode Cloud/Headless (6s) pour basculer vite sur X-Ray, plus longue en local avec interface (90s)
        max_wait_iterations = 3 if getattr(config, "HEADLESS", False) or sys.platform != "win32" else 45
        for second in range(max_wait_iterations):
            await asyncio.sleep(2)
            
            if await self.is_logged_in(page):
                audit_logger.log_event("AUTH_SUCCESS", "Connexion validée avec succès !")
                notify("🎉 Connexion validée ! Sauvegarde de la session...")
                
                # Sauvegarde du cookie li_at dans .env
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
