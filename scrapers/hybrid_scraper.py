import logging
import re
from typing import Any, List

from . import Contact
from .xray_fallback import XRayScraper
from .stealth_browser import StealthBrowser

logger = logging.getLogger(__name__)

class HybridScraper:
    def __init__(self, config: Any, rate_limiter: Any):
        self.config = config
        self.rate_limiter = rate_limiter
        self.xray = XRayScraper(rate_limiter=rate_limiter)
        self.stealth = None
        if getattr(config, 'linkedin_cookie', None):
            self.stealth = StealthBrowser(
                cookie=config.linkedin_cookie,
                proxy_url=getattr(config, 'proxy_url', None),
                rate_limiter=rate_limiter
            )

    async def search(self, company: str, keywords: List[str], location: str) -> List[Contact]:
        contacts: List[Contact] = []
        
        # Phase 1: X-Ray search
        try:
            contacts = await self.xray.search(company, keywords, location)
            logger.info(f"X-Ray a trouve {len(contacts)} contacts pour {company}")
        except Exception as e:
            logger.debug(f"Erreur X-Ray pour {company}: {e}")
        
        # Phase 2: Stealth fallback if X-Ray found < 5 profiles and cookie is provided
        if len(contacts) < 5 and self.stealth:
            logger.info(f"X-Ray yielded {len(contacts)} contacts (< 5). Switching to Stealth fallback for {company}")
            try:
                company_slug = self._get_company_slug(company)
                stealth_contacts = await self.stealth.search_company_people(company_slug, keywords)
                contacts = self._merge_contacts(contacts, stealth_contacts)
            except Exception as e:
                logger.error(f"Erreur Stealth fallback pour {company}: {e}")
        elif len(contacts) < 5 and not self.stealth:
            logger.info(f"X-Ray yielded {len(contacts)} contacts (< 5), but no valid stealth session is configured.")
        
        return contacts

    def _get_company_slug(self, company: str) -> str:
        slug = company.lower()
        slug = re.sub(r'[^a-z0-9\s-]', '', slug)
        slug = re.sub(r'\s+', '-', slug).strip('-')
        return slug

    def _merge_contacts(self, existing: List[Contact], new: List[Contact]) -> List[Contact]:
        merged = {c.linkedin_url: c for c in existing if c.linkedin_url}
        for contact in new:
            if contact.linkedin_url and contact.linkedin_url not in merged:
                merged[contact.linkedin_url] = contact
            elif not contact.linkedin_url:
                merged[f"{contact.first_name}_{contact.last_name}"] = contact
        return list(merged.values())

    async def close(self) -> None:
        if self.stealth:
            try:
                await self.stealth.close()
            except Exception:
                pass
