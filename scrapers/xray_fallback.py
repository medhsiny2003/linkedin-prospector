import asyncio
import logging
import random
import re
from typing import Any, Optional, List, Dict
from bs4 import BeautifulSoup
import httpx

from . import Contact
from .parsers.dom_parser import DOMParser

logger = logging.getLogger(__name__)

class XRayScraper:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/117.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 Edg/116.0.1938.81",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/116.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36 Edg/115.0.1901.203",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/117.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15"
    ]

    def __init__(self, rate_limiter: Any = None):
        self.rate_limiter = rate_limiter

    async def search(self, company: str, keywords: List[str], location: str, max_results: int = 50) -> List[Contact]:
        all_contacts = {}
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for keyword in keywords:
                query = f'site:linkedin.com/in/ "{company}" "{keyword}" "{location}"'
                logger.info(f"Searching X-Ray: {query}")
                results = await self._search_duckduckgo(client, query)
                
                for res in results:
                    contact = self._parse_linkedin_result(res['title'], res['url'], res['snippet'])
                    if contact and contact.linkedin_url not in all_contacts:
                        contact.company = company  # Set fallback company
                        all_contacts[contact.linkedin_url] = contact
                
                if len(all_contacts) >= max_results:
                    break

        return list(all_contacts.values())[:max_results]

    async def _search_duckduckgo(self, client: httpx.AsyncClient, query: str, max_pages: int = 5) -> List[Dict[str, str]]:
        results = []
        base_url = "https://html.duckduckgo.com/html/"
        params = {'q': query}
        
        for page in range(max_pages):
            if self.rate_limiter:
                await self.rate_limiter.wait()
            else:
                await asyncio.sleep(random.uniform(1.5, 3.5))
                
            try:
                headers = self._get_random_headers()
                response = await client.post(base_url, data=params, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                page_results = DOMParser.parse_search_results(response.text)
                results.extend(page_results)
                
                # Check for next page
                next_form = soup.find('div', class_='nav-link')
                if not next_form or not next_form.find('form'):
                    break
                    
                form = next_form.find('form')
                for input_tag in form.find_all('input', type='hidden'):
                    params[input_tag.get('name')] = input_tag.get('value')
                    
            except Exception as e:
                logger.error(f"Error searching DuckDuckGo page {page}: {e}")
                break
                
        return results

    def _parse_linkedin_result(self, title: str, url: str, snippet: str) -> Optional[Contact]:
        if not re.search(r'linkedin\.com/in/', url):
            return None
            
        parsed_title = DOMParser.parse_linkedin_title(title)
        if not parsed_title['first_name']:
            return None
            
        return Contact(
            first_name=parsed_title['first_name'],
            last_name=parsed_title['last_name'],
            title=parsed_title.get('title', ''),
            company=parsed_title.get('company', ''),
            linkedin_url=url,
            source='xray'
        )

    def _get_random_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
