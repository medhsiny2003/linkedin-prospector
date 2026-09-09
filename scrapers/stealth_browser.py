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
        headless: bool = True
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
                '--disable-features=IsolateOrigins,site-per-process',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-infobars',
                '--disable-background-networking',
                '--disable-default-apps',
                '--no-first-run'
            ]

            proxy_dict = {'server': self.proxy_url} if self.proxy_url else None

            # Launch persistent context using Microsoft Edge channel
            try:
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    channel="msedge",
                    headless=self.headless,
                    args=launch_args,
                    proxy=proxy_dict,
                    viewport={'width': 1440, 'height': 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.2478.80",
                    locale='fr-FR',
                    timezone_id='Europe/Paris'
                )
                logger.info("Navigateur Microsoft Edge initialisé avec profil persistant data/sessions/edge_profile")
            except Exception as edge_err:
                logger.warning(f"Edge channel indisponible ({edge_err}), fallback sur Chromium standard.")
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    args=launch_args,
                    proxy=proxy_dict,
                    viewport={'width': 1440, 'height': 900},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.2478.80",
                    locale='fr-FR',
                    timezone_id='Europe/Paris'
                )

            # Patch navigator.webdriver on all newly created pages
            await self.context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                window.chrome = { runtime: {} };
            """)

            # Add li_at session cookie if provided
            if self.cookie:
                clean_cookie = self.cookie.strip()
                await self.context.add_cookies([
                    {
                        'name': 'li_at',
                        'value': clean_cookie,
                        'domain': '.linkedin.com',
                        'path': '/',
                        'secure': True,
                        'httpOnly': True
                    }
                ])
                logger.info("Cookie li_at pour Microsoft Edge configuré sur .linkedin.com")

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
                    elif "checkpoint" in page.url or "authwall" in page.url or "login" in page.url:
                        logger.warning("Session LinkedIn : Cookie expiré ou vérification requise.")
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

            # Check for captchas or errors
            if await self._detect_captcha(page):
                logger.warning("CAPTCHA ou Challenge détecté sur LinkedIn.")
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
            if "checkpoint/challenge" in url or "chrome-error://" in url:
                return True
            content = await page.content()
            if "captcha" in content.lower() or "security check" in content.lower():
                return True
        except Exception:
            pass
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
