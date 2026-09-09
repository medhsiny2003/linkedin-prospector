"""
LinkedIn browser automation and navigation module.
Provides safe navigation, human-like interaction, and data extraction using Playwright.
"""
import asyncio
import logging
import random
from typing import Any, Dict, List, Optional

from playwright.async_api import Page, Error as PlaywrightError

logger = logging.getLogger(__name__)

class LinkedInNavigationError(Exception):
    """Raised when navigation to a LinkedIn page fails or is blocked."""
    pass

class LinkedInAuthWallError(LinkedInNavigationError):
    """Raised when encountering an authwall or login checkpoint."""
    pass

class LinkedInCaptchaError(LinkedInNavigationError):
    """Raised when encountering a CAPTCHA challenge."""
    pass


class LinkedInBrowserScraper:
    """
    Handles safe browser interactions for LinkedIn scraping.
    """

    @staticmethod
    async def safe_goto(page: Page, url: str, max_retries: int = 3) -> None:
        """
        Navigates to a URL safely with exponential backoff and fallbacks.
        
        Args:
            page: Playwright Page instance.
            url: The URL to navigate to.
            max_retries: Maximum number of retry attempts.
            
        Raises:
            LinkedInNavigationError: If navigation fails after retries.
            LinkedInAuthWallError: If an authwall is detected.
            LinkedInCaptchaError: If a CAPTCHA is detected.
        """
        attempt = 0
        while attempt < max_retries:
            try:
                # Try with domcontentloaded first for speed, fallback to load if needed
                response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                # Check for bad responses or blocked pages
                if response:
                    status = response.status
                    if status in (403, 429, 999):
                        logger.warning(f"Received status {status} on {url}")
                
                await LinkedInBrowserScraper._check_for_blocks(page)
                return

            except PlaywrightError as e:
                logger.warning(f"Navigation error on attempt {attempt + 1}: {e}")
                attempt += 1
                if attempt >= max_retries:
                    raise LinkedInNavigationError(f"Failed to navigate to {url} after {max_retries} attempts.") from e
                
                # Exponential backoff
                await asyncio.sleep(2 ** attempt + random.uniform(0, 1))

    @staticmethod
    async def _check_for_blocks(page: Page) -> None:
        """
        Checks the page for CAPTCHAs, authwalls, or error pages.
        
        Args:
            page: Playwright Page instance.
            
        Raises:
            LinkedInAuthWallError: If authwall is found.
            LinkedInCaptchaError: If CAPTCHA is found.
            LinkedInNavigationError: If generic error or checkpoint is found.
        """
        current_url = page.url
        if "chrome-error://" in current_url:
            raise LinkedInNavigationError("Encountered chrome-error page.")
        
        if "linkedin.com/checkpoint" in current_url or "linkedin.com/signup" in current_url or "linkedin.com/authwall" in current_url:
            raise LinkedInAuthWallError("Encountered LinkedIn authwall or checkpoint.")

        # Check for CAPTCHA elements
        captcha_element = await page.query_selector('div#captcha-internal, iframe[src*="captcha"]')
        if captcha_element:
            raise LinkedInCaptchaError("Encountered CAPTCHA challenge.")

        # Check for blank page
        content = await page.content()
        if not content or len(content.strip()) < 100:
            raise LinkedInNavigationError("Page appears to be blank.")

    @staticmethod
    async def human_scroll(page: Page) -> None:
        """
        Performs human-like scrolling on the page to trigger lazy loading.
        Uses progressive scrollBy with variable delays.
        
        Args:
            page: Playwright Page instance.
        """
        try:
            viewport_size = page.viewport_size
            if not viewport_size:
                return

            viewport_height = viewport_size["height"]
            total_scrolls = random.randint(3, 7)
            
            for _ in range(total_scrolls):
                scroll_amount = random.randint(viewport_height // 4, viewport_height)
                # Playwright mouse wheel for smooth scrolling
                await page.mouse.wheel(delta_x=0, delta_y=scroll_amount)
                
                # Variable delay between 5 to 12s
                delay = random.uniform(5.0, 12.0)
                await asyncio.sleep(delay)
                
        except Exception as e:
            logger.error(f"Error during human scroll: {e}")

    @staticmethod
    async def extract_profile_cards(page: Page) -> List[Dict[str, Any]]:
        """
        Extracts profile cards from the page safely with DOM validation.
        Applicable to company people tab or global search.
        
        Args:
            page: Playwright Page instance.
            
        Returns:
            List of dictionaries containing extracted profile data.
        """
        profiles: List[Dict[str, Any]] = []
        try:
            # Wait for search results or people cards to load
            await page.wait_for_selector('.reusable-search__result-container, .org-people-profile-card', timeout=10000)
        except PlaywrightError:
            logger.warning("Timeout waiting for profile cards to load.")
            return profiles

        # Select both possible card types
        cards = await page.query_selector_all('.reusable-search__result-container, .org-people-profile-card')
        
        for card in cards:
            try:
                # Extract basic info safely
                name_element = await card.query_selector('.app-aware-link span[aria-hidden="true"], .org-people-profile-card__profile-title')
                name = await name_element.inner_text() if name_element else ""
                
                title_element = await card.query_selector('.entity-result__primary-subtitle, .org-people-profile-card__profile-info')
                title = await title_element.inner_text() if title_element else ""
                
                link_element = await card.query_selector('.app-aware-link')
                profile_url = await link_element.get_attribute('href') if link_element else ""

                if profile_url:
                    # Clean URL (remove query params)
                    profile_url = profile_url.split('?')[0]

                if name and profile_url:
                    profiles.append({
                        "name": name.strip(),
                        "title": title.strip(),
                        "profile_url": profile_url.strip()
                    })
            except Exception as e:
                logger.debug(f"Error extracting individual card: {e}")
                continue

        return profiles
