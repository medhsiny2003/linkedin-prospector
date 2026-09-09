"""
Session Manager module for handling LinkedIn authentication and session validation.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

class SessionManager:
    """
    Manages LinkedIn sessions, including cookie validation, formatting, and session state persistence.
    """

    def __init__(self, session_dir: Union[str, Path] = "d:/PROJECT hsiny/DATA/linkedin-prospector/data/sessions"):
        """
        Initializes the SessionManager.

        Args:
            session_dir: Directory where session cookies and states are stored.
        """
        self.session_dir = Path(session_dir)
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self.cookie_file = self.session_dir / "cookies.json"
        
    def format_cookie(self, li_at: str) -> Dict[str, Any]:
        """
        Formats the li_at cookie with appropriate parameters.

        Args:
            li_at: The raw li_at cookie value.

        Returns:
            A dictionary containing the formatted cookie parameters.
        """
        return {
            "name": "li_at",
            "value": li_at,
            "domain": ".linkedin.com",
            "path": "/",
            "secure": True,
            "httpOnly": True,
            "sameSite": "None"
        }

    def save_cookies(self, cookies: List[Dict[str, Any]]) -> None:
        """
        Saves cookies to the session directory.

        Args:
            cookies: A list of cookie dictionaries to save.
        """
        try:
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, indent=4)
            logger.info(f"Cookies successfully saved to {self.cookie_file}")
        except IOError as e:
            logger.error(f"Failed to save cookies: {e}")

    def load_cookies(self) -> List[Dict[str, Any]]:
        """
        Loads cookies from the session directory.

        Returns:
            A list of cookie dictionaries, or an empty list if not found or on error.
        """
        if not self.cookie_file.exists():
            logger.warning(f"Cookie file not found at {self.cookie_file}")
            return []

        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load cookies: {e}")
            return []

    async def validate_session(self, page_or_context: Any) -> bool:
        """
        Validates the active session by checking for challenges or session expiry on a lightweight endpoint.

        Args:
            page_or_context: A Playwright Page or BrowserContext object. If a context is provided, 
                             a new page is created and then closed.

        Returns:
            True if the session is valid, False otherwise.
        """
        close_page = False
        
        # Check if it's a context by looking for 'new_page' attribute
        if hasattr(page_or_context, 'new_page') and callable(getattr(page_or_context, 'new_page')):
            page = await page_or_context.new_page()
            close_page = True
        else:
            page = page_or_context

        try:
            # Navigate to a lightweight endpoint to avoid full bot detection on main profiles
            response = await page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=30000)
            
            if not response:
                logger.error("Failed to receive a response from LinkedIn.")
                return False

            url = page.url
            
            # Check for common challenge or authwall URLs
            if "authwall" in url or "checkpoint/challenge" in url or "login-submit" in url:
                logger.error(f"Session invalid or challenged. Redirected to: {url}")
                logger.error("Please update your 'li_at' cookie and ensure it is fresh.")
                return False

            # Check if we are redirected to login page
            if "login" in url or "signup" in url:
                logger.error(f"Session expired. Redirected to: {url}")
                logger.error("Please obtain a new 'li_at' cookie.")
                return False
                
            # Basic DOM check to ensure we are actually logged in
            # We can check if the global nav bar exists or search input exists
            is_logged_in = await page.locator("input[placeholder='Search']").count() > 0 or \
                           await page.locator("#global-nav").count() > 0 or \
                           await page.locator(".feed-identity-module").count() > 0 or \
                           await page.locator(".global-nav__primary-items").count() > 0
                           
            if is_logged_in:
                logger.info("Session validated successfully.")
                return True
            else:
                logger.warning("Could not verify logged-in state from DOM elements. Session might be restricted.")
                return False

        except Exception as e:
            logger.error(f"An error occurred during session validation: {e}")
            return False
        finally:
            if close_page:
                await page.close()
