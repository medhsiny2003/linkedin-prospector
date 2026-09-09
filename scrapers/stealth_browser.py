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
    def __init__(self, cookie: Optional[str] = None, proxy_url: Optional[str] = None, rate_limiter: Any = None):
        self.cookie = cookie
        self.proxy_url = proxy_url
        self.rate_limiter = rate_limiter
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self._session_verified = False

    async def setup(self) -> None:
        if async_playwright is None:
            logger.warning("Playwright n'est pas installe. Le mode Stealth ne fonctionnera pas.")
            return

        if self.context and self.browser:
            return  # Already initialized

        try:
            self.playwright = await async_playwright().start()
            
            launch_args = {
                'headless': True,
                'args': [
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                    '--disable-setuid-sandbox'
                ]
            }
            if self.proxy_url:
                launch_args['proxy'] = {'server': self.proxy_url}
                
            self.browser = await self.playwright.chromium.launch(**launch_args)
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                locale='fr-FR',
                timezone_id='Europe/Paris'
            )
            
            if self.cookie:
                # Add cookie with proper .linkedin.com domain
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
                logger.debug("Cookie li_at configure sur .linkedin.com")
        except Exception as e:
            logger.error(f"Erreur initialisation StealthBrowser: {e}")

    async def search_company_people(self, company_slug: str, keywords: List[str], max_results: int = 50) -> List[Contact]:
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
            # 1. Warm-up navigation on feed if not verified yet
            if not self._session_verified and self.cookie:
                try:
                    logger.info("Verification de la session LinkedIn...")
                    await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=15000)
                    await asyncio.sleep(2)
                    if "feed" in page.url:
                        self._session_verified = True
                        logger.info("Session LinkedIn valide !")
                    elif "checkpoint" in page.url or "authwall" in page.url or "login" in page.url:
                        logger.warning("Le cookie LinkedIn semble expire ou bloque par LinkedIn.")
                except Exception:
                    pass

            # 2. Navigate to Company people page
            query_param = " OR ".join(keywords) if keywords else ""
            url = f"https://www.linkedin.com/company/{company_slug}/people/"
            if query_param:
                url += f"?keywords={query_param}"
                
            logger.info(f"Navigation Stealth vers {url}")
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(3)
            
            if await self._detect_captcha(page):
                logger.warning("CAPTCHA ou Verification demandee sur LinkedIn.")
                return contacts

            # 3. Simulate human scrolling
            await self._simulate_human_behavior(page)
            
            # 4. Extract employee profile cards
            raw_contacts = await self._scroll_and_extract(page, max_scrolls=5)
            
            for rc in raw_contacts:
                parsed_name = DOMParser.clean_name(rc.get('name', ''))
                contacts.append(Contact(
                    first_name=parsed_name[0],
                    last_name=parsed_name[1],
                    title=rc.get('title', ''),
                    linkedin_url=rc.get('url', ''),
                    source='stealth'
                ))
                if len(contacts) >= max_results:
                    break
                    
            logger.info(f"Stealth a extrait {len(contacts)} contacts pour {company_slug}")
        except Exception as e:
            logger.error(f"Erreur scraping Stealth: {e}")
        finally:
            try:
                await page.close()
            except Exception:
                pass
            
        return contacts

    async def _simulate_human_behavior(self, page: Page) -> None:
        for _ in range(random.randint(1, 3)):
            x = random.randint(200, 800)
            y = random.randint(200, 600)
            try:
                await page.mouse.move(x, y, steps=random.randint(5, 10))
            except Exception:
                pass
            await asyncio.sleep(random.uniform(0.5, 1.5))

    async def _scroll_and_extract(self, page: Page, max_scrolls: int = 5) -> List[Dict[str, str]]:
        all_results = []
        for _ in range(max_scrolls):
            try:
                html = await page.content()
                cards = DOMParser.parse_company_people_page(html)
                for card in cards:
                    if card['url'] and card['url'] not in [r['url'] for r in all_results]:
                        all_results.append(card)
                        
                await page.evaluate("window.scrollBy(0, 1000)")
                await asyncio.sleep(random.uniform(1.5, 3.0))
            except Exception:
                break
        return all_results

    async def _detect_captcha(self, page: Page) -> bool:
        try:
            content = await page.content()
            if "checkpoint/challenge" in page.url or "captcha" in content.lower():
                return True
        except Exception:
            pass
        return False

    async def close(self) -> None:
        try:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception:
            pass
        self.context = None
        self.browser = None
        self.playwright = None
