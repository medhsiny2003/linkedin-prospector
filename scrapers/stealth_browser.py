import asyncio
import logging
import random
from typing import Any, Optional, List, Dict

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
except ImportError:
    async_playwright = None
    Page = Any
    BrowserContext = Any
    
try:
    from playwright_stealth import stealth_async
except ImportError:
    stealth_async = None

from . import Contact
from .parsers.dom_parser import DOMParser

logger = logging.getLogger(__name__)

class StealthBrowser:
    def __init__(self, cookie: Optional[str] = None, proxy_url: Optional[str] = None, rate_limiter: Any = None):
        self.cookie = cookie
        self.proxy_url = proxy_url
        self.rate_limiter = rate_limiter
        self.playwright = None
        self.browser = None
        self.context: Optional[BrowserContext] = None

    async def setup(self) -> None:
        if async_playwright is None:
            logger.warning("Playwright is not installed. StealthBrowser will not work.")
            return

        self.playwright = await async_playwright().start()
        
        launch_args = {
            'headless': True,
            'args': ['--disable-blink-features=AutomationControlled']
        }
        if self.proxy_url:
            launch_args['proxy'] = {'server': self.proxy_url}
            
        self.browser = await self.playwright.chromium.launch(**launch_args)
        
        self.context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            locale='fr-FR',
            timezone_id='Europe/Paris',
            geolocation={'latitude': 48.8566, 'longitude': 2.3522},
            permissions=['geolocation']
        )
        
        if self.cookie:
            await self.context.add_cookies([{
                'name': 'li_at',
                'value': self.cookie,
                'domain': '.www.linkedin.com',
                'path': '/'
            }])

    async def search_company_people(self, company_slug: str, keywords: List[str], max_results: int = 50) -> List[Contact]:
        if not self.context:
            logger.error("Browser context not initialized. Call setup() first.")
            return []

        page = await self.context.new_page()
        if stealth_async:
            await stealth_async(page)
            
        contacts = []
        try:
            url = f"https://www.linkedin.com/company/{company_slug}/people/"
            if keywords:
                keyword_query = " OR ".join(keywords)
                url += f"?keywords={keyword_query}"
                
            await page.goto(url, wait_until="domcontentloaded")
            
            if await self._detect_captcha(page):
                logger.error("CAPTCHA detected on LinkedIn.")
                return contacts

            await self._simulate_human_behavior(page)
            
            raw_contacts = await self._scroll_and_extract(page)
            
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
                    
        except Exception as e:
            logger.error(f"Error during stealth scraping: {e}")
        finally:
            await page.close()
            
        return contacts

    async def _simulate_human_behavior(self, page: Page) -> None:
        # Simulate random mouse movements and pauses
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1000)
            y = random.randint(100, 800)
            await page.mouse.move(x, y, steps=random.randint(5, 10))
            await asyncio.sleep(random.uniform(0.5, 2.0))
        await asyncio.sleep(random.uniform(2.0, 4.0))

    async def _scroll_and_extract(self, page: Page, max_scrolls: int = 10) -> List[Dict[str, str]]:
        all_results = []
        previous_height = 0
        
        for _ in range(max_scrolls):
            html = await page.content()
            cards = DOMParser.parse_company_people_page(html)
            
            for card in cards:
                if card not in all_results:
                    all_results.append(card)
                    
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(2.0, 5.0))
            
            new_height = await page.evaluate("document.body.scrollHeight")
            if new_height == previous_height:
                break
            previous_height = new_height
            
        return all_results

    async def _detect_captcha(self, page: Page) -> bool:
        content = await page.content()
        if "checkpoint/challenge" in page.url or "captcha" in content.lower():
            return True
        return False

    async def close(self) -> None:
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
