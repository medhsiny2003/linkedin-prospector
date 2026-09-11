"""
Configuration du navigateur Playwright en mode Headful (VISIBLE) avec Microsoft Edge natif.
Respecte les directives de protection du compte LinkedIn :
- Utilise l'exécutable natif Microsoft Edge (msedge.exe)
- Pas de mode headless (toujours visible)
- Empreinte navigateur réaliste et masquage d'automatisation
"""

import os
import sys
from pathlib import Path
from typing import Optional, Tuple
from playwright.async_api import BrowserContext, Page, async_playwright
from config import config
from core.browser.session_manager import session_manager
from core.monitoring.audit_logger import audit_logger

try:
    from playwright_stealth import stealth_async
    HAS_PLAYWRIGHT_STEALTH = True
except ImportError:
    HAS_PLAYWRIGHT_STEALTH = False

STEALTH_EVASION_SCRIPT = """
(() => {
    // 1. Masquage de navigator.webdriver
    try {
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined
        });
    } catch(e) {}

    // 2. Émulation des objets runtime natifs
    if (!window.chrome) {
        window.chrome = {};
    }
    if (!window.chrome.runtime) {
        window.chrome.runtime = {};
    }

    // 3. Normalisation des langues
    try {
        Object.defineProperty(navigator, 'languages', {
            get: () => ['fr-FR', 'fr', 'en-US', 'en']
        });
    } catch(e) {}
})();
"""


class StealthBrowser:
    def __init__(self):
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    def find_edge_executable(self) -> Optional[str]:
        """Détecte l'emplacement officiel de Microsoft Edge sur le système Windows."""
        candidate_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe")
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                return path
        return None

    async def launch(self) -> Tuple[BrowserContext, Page]:
        """
        Lance le contexte de navigation persistant en utilisant l'exécutable Microsoft Edge.
        """
        session_dir = session_manager.ensure_session_directory()
        self.playwright = await async_playwright().start()

        # Configuration des options du navigateur (Anti-délégation & Session isolée)
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--disable-background-mode",
            "--no-default-browser-check",
            "--no-first-run",
            "--start-maximized",
            "--lang=fr-FR",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage"
        ]

        proxy_dict = None
        from core.network.proxy_manager import proxy_manager
        proxy_dict = proxy_manager.get_playwright_proxy_dict()
        if proxy_dict:
            audit_logger.log_event("PROXY_CONFIG", f"Utilisation du proxy : {proxy_dict.get('server')}")

        edge_exe = self.find_edge_executable()

        if edge_exe:
            audit_logger.log_event(
                "BROWSER_LAUNCH",
                f"Lancement direct de Microsoft Edge : {edge_exe}",
                {"session_dir": str(session_dir)}
            )
            # Lancement direct de msedge.exe
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(session_dir),
                executable_path=edge_exe,
                headless=config.HEADLESS,
                args=launch_args,
                ignore_default_args=["--enable-automation"],
                proxy=proxy_dict,
                viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
                locale=config.LOCALE,
                timezone_id=config.TIMEZONE
            )
        else:
            audit_logger.log_event(
                "BROWSER_LAUNCH",
                "Lancement de Chromium en mode universel / cloud",
                {"session_dir": str(session_dir)}
            )
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(session_dir),
                    channel=config.BROWSER_CHANNEL if sys.platform == "win32" else None,
                    headless=config.HEADLESS,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                    proxy=proxy_dict,
                    viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
                    locale=config.LOCALE,
                    timezone_id=config.TIMEZONE
                )
            except Exception:
                # Fallback standard Chromium sans canal spécifique
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=str(session_dir),
                    headless=config.HEADLESS,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                    proxy=proxy_dict,
                    viewport={"width": config.VIEWPORT_WIDTH, "height": config.VIEWPORT_HEIGHT},
                    locale=config.LOCALE,
                    timezone_id=config.TIMEZONE
                )

        # Injection des scripts d'évasion sur chaque nouvelle page
        await self.context.add_init_script(STEALTH_EVASION_SCRIPT)

        # Récupération ou création de la page active
        if self.context.pages:
            self.page = self.context.pages[0]
        else:
            self.page = await self.context.new_page()

        if HAS_PLAYWRIGHT_STEALTH:
            try:
                await stealth_async(self.page)
            except Exception:
                pass

        return self.context, self.page

    async def close(self) -> None:
        """Ferme proprement le contexte et le moteur Playwright."""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
            audit_logger.log_event("BROWSER_CLOSE", "Microsoft Edge fermé avec succès.")
        except Exception as e:
            audit_logger.log_event("BROWSER_ERROR", f"Erreur lors de la fermeture : {e}")


stealth_browser = StealthBrowser()
