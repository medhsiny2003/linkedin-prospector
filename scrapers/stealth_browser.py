import os
import asyncio
import logging
import random
import re
from typing import Any, Optional, List, Dict

try:
    from playwright.async_api import async_playwright, Page, BrowserContext, Browser
except ImportError:
    async_playwright = None
    Page = Any
    BrowserContext = Any
    Browser = Any

try:
    import playwright_stealth
except ImportError:
    playwright_stealth = None

from . import Contact
from .parsers.dom_parser import DOMParser

logger = logging.getLogger(__name__)

class StealthBrowser:
    """Microsoft Edge browser automation with persistent session and anti-detection."""

    def __init__(
        self,
        cookie: Optional[str] = None,
        proxy_url: Optional[str] = None,
        rate_limiter: Any = None,
        user_data_dir: str = "data/sessions/edge_profile",
        headless: bool = False
    ):
        self.cookie = cookie
        self.proxy_url = proxy_url
        self.rate_limiter = rate_limiter
        self.user_data_dir = user_data_dir
        self.headless = headless
        self.playwright = None
        self.context: Optional[BrowserContext] = None
        self._session_verified = False

    async def setup(self) -> None:
        """Initializes Microsoft Edge with persistent user profile and anti-detection."""
        if async_playwright is None:
            logger.warning("Playwright n'est pas installé. Le mode Edge ne fonctionnera pas.")
            return

        if self.context:
            return  # Already initialized

        try:
            os.makedirs(self.user_data_dir, exist_ok=True)
            self.playwright = await async_playwright().start()

            launch_args = [
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--no-default-browser-check',
                '--no-first-run',
                '--start-maximized',
                '--lang=fr-FR'
            ]

            proxy_dict = {'server': self.proxy_url} if self.proxy_url else None

            # Launch persistent context using Microsoft Edge channel with native full-screen resolution
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    channel="msedge",
                    headless=self.headless,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                    proxy=proxy_dict,
                    no_viewport=True,
                    locale='fr-FR',
                    timezone_id='Europe/Paris'
                )
                logger.info("Navigateur Microsoft Edge initialisé avec profil persistant data/sessions/edge_profile")
            except Exception as edge_err:
                logger.warning(f"Edge channel direct indisponible ({edge_err}), tentative de lancement standard.")
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    args=launch_args,
                    ignore_default_args=["--enable-automation"],
                    proxy=proxy_dict,
                    no_viewport=True,
                    locale='fr-FR',
                    timezone_id='Europe/Paris'
                )

            # Patch navigator.webdriver and runtime on all newly created pages
            await self.context.add_init_script("""
                try {
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    delete Object.getPrototypeOf(navigator).webdriver;
                } catch(e) {}
                if (!window.chrome) window.chrome = {};
                if (!window.chrome.runtime) window.chrome.runtime = {};
            """)

            # Add li_at session cookie if provided
            if self.cookie:
                clean_cookie = self.cookie.strip().strip('"').strip("'")
                match = re.search(r'li_at="?([a-zA-Z0-9_\-\.]+)"?', clean_cookie)
                if match:
                    clean_cookie = match.group(1).strip()

                await self.context.add_cookies([
                    {
                        'name': 'li_at',
                        'value': clean_cookie,
                        'domain': '.linkedin.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': True,
                        'sameSite': 'Lax'
                    },
                    {
                        'name': 'li_at',
                        'value': clean_cookie,
                        'domain': '.www.linkedin.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': True,
                        'sameSite': 'Lax'
                    },
                    {
                        'name': 'JSESSIONID',
                        'value': '"ajax:0"',
                        'domain': '.www.linkedin.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': False,
                        'sameSite': 'Lax'
                    }
                ])
                logger.info("Cookies de session LinkedIn configurés sur Microsoft Edge.")

        except Exception as e:
            logger.error(f"Erreur initialisation StealthBrowser Edge: {e}")

    async def search_company_people(self, company_slug: str, keywords: List[str], max_results: int = 50) -> List[Contact]:
        """Navigates to company people page and extracts matching employee contacts."""
        await self.setup()
        if not self.context:
            return []

        page = await self.context.new_page()
        if playwright_stealth:
            try:
                await playwright_stealth.stealth(page)
            except Exception:
                pass

        contacts = []
        try:
            # 1. Verify LinkedIn session
            if not self._session_verified and self.cookie:
                try:
                    logger.info("Vérification de la session Edge LinkedIn...")
                    await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(2)
                    if "feed" in page.url:
                        self._session_verified = True
                        logger.info("Session Edge LinkedIn validée avec succès !")
                    elif await self._handle_captcha_challenge(page):
                        self._session_verified = True
                        logger.info("Défi de sécurité validé avec succès !")
                except Exception:
                    pass

            # 2. Build target URL
            query_param = " OR ".join(keywords) if keywords else ""
            url = f"https://www.linkedin.com/company/{company_slug}/people/"
            if query_param:
                url += f"?keywords={query_param}"

            logger.info(f"Navigation Edge vers {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)

            # Check and handle captchas or checkpoint challenges
            if await self._detect_captcha(page):
                solved = await self._handle_captcha_challenge(page)
                if not solved:
                    logger.warning("CAPTCHA ou Défi non résolu, interruption pour cette entreprise.")
                    return contacts

            # 3. Human behavior simulation & progressive scroll
            await self._simulate_human_behavior(page)
            raw_contacts = await self._scroll_and_extract(page, max_scrolls=6)

            for rc in raw_contacts:
                parsed_name = DOMParser.clean_name(rc.get('name', ''))
                if parsed_name[0] or parsed_name[1]:
                    contacts.append(Contact(
                        first_name=parsed_name[0],
                        last_name=parsed_name[1],
                        title=rc.get('title', ''),
                        linkedin_url=rc.get('url', ''),
                        source='stealth_edge'
                    ))
                if len(contacts) >= max_results:
                    break

            logger.info(f"Edge Stealth a extrait {len(contacts)} contacts pour {company_slug}")
        except Exception as e:
            logger.error(f"Erreur scraping Edge Stealth: {e}")
        finally:
            try:
                await page.close()
            except Exception:
                pass

        return contacts

    async def _simulate_human_behavior(self, page: Page) -> None:
        """Simulates natural mouse movements and pauses."""
        for _ in range(random.randint(2, 4)):
            x = random.randint(150, 850)
            y = random.randint(150, 650)
            try:
                await page.mouse.move(x, y, steps=random.randint(6, 12))
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.5, 1.8))

    async def _scroll_and_extract(self, page: Page, max_scrolls: int = 6) -> List[Dict[str, str]]:
        """Scrolls down smoothly and extracts profile cards from the people tab."""
        all_results = []
        for _ in range(max_scrolls):
            try:
                html = await page.content()
                cards = DOMParser.parse_company_people_page(html)
                for card in cards:
                    if card.get('url') and card['url'] not in [r['url'] for r in all_results]:
                        all_results.append(card)

                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(random.uniform(2.0, 4.0))
            except Exception:
                break
        return all_results

    async def _detect_captcha(self, page: Page) -> bool:
        """Checks for captcha or authwall."""
        try:
            url = page.url.lower()
            if any(sig in url for sig in ["checkpoint", "challenge", "security-verification", "captcha"]):
                return True
            content = (await page.content()).lower()
            if "captcha" in content or "security check" in content or "vérification de sécurité" in content:
                return True
        except Exception:
            pass
        return False

    async def _handle_captcha_challenge(self, page: Page, timeout_seconds: int = 120) -> bool:
        """Guides user and waits for manual resolution of CAPTCHA in headful Edge window."""
        logger.warning("=" * 60)
        logger.warning("⚠️  DÉFI DE SÉCURITÉ / CAPTCHA DÉTECTÉ SUR LINKEDIN")
        logger.warning("Veuillez résoudre le CAPTCHA dans la fenêtre Microsoft Edge ouverte...")
        logger.warning("=" * 60)

        for _ in range(int(timeout_seconds / 2)):
            await asyncio.sleep(2)
            try:
                url = page.url.lower()
                if not any(sig in url for sig in ["checkpoint", "challenge", "security-verification", "captcha", "login"]):
                    # Résolution réussie
                    logger.info("✅ Défi de sécurité résolu avec succès ! Reprise de l'automatisation...")
                    return True
            except Exception:
                pass

        logger.error("❌ Délai de résolution du défi de sécurité dépassé.")
        return False

    async def close(self) -> None:
        """Closes browser context and playwright instance."""
        try:
            if self.context:
                await self.context.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.context = None
        self.playwright = None
