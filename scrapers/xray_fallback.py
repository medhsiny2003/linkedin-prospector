import asyncio
import logging
import random
import re
import base64
import urllib.parse
from typing import Any, Optional, List, Dict
from bs4 import BeautifulSoup
import httpx

from . import Contact
from .parsers.dom_parser import DOMParser

logger = logging.getLogger(__name__)

class XRayScraper:
    """Multi-Engine X-Ray search scraper (Bing + DuckDuckGo + Google)."""

    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0"
    ]

    def __init__(self, rate_limiter: Any = None):
        self.rate_limiter = rate_limiter

    async def search(self, company: str, keywords: List[str], location: str = "France", max_results: int = 50) -> List[Contact]:
        all_contacts: Dict[str, Contact] = {}
        
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            for keyword in keywords:
                query = f'site:linkedin.com/in "{company}" "{keyword}" "{location}"'
                logger.info(f"Recherche X-Ray: {query}")
                
                # Try Bing X-Ray first (most reliable without captcha)
                results = await self._search_bing(client, query)
                
                # If insufficient, try DuckDuckGo
                if len(results) < 3:
                    ddg_results = await self._search_duckduckgo(client, query)
                    results.extend(ddg_results)
                    
                for res in results:
                    contact = self._parse_linkedin_result(res['title'], res['url'], res.get('snippet', ''))
                    if contact and contact.linkedin_url not in all_contacts:
                        if not contact.company:
                            contact.company = company
                        all_contacts[contact.linkedin_url] = contact
                
                if len(all_contacts) >= max_results:
                    break
                    
                if self.rate_limiter:
                    await self.rate_limiter.wait()

        return list(all_contacts.values())[:max_results]

    async def _search_bing(self, client: httpx.AsyncClient, query: str) -> List[Dict[str, str]]:
        """Search Bing and decode redirect URLs."""
        results = []
        try:
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&count=20"
            headers = self._get_random_headers()
            r = await client.get(url, headers=headers)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for li in soup.find_all('li', class_='b_algo'):
                    h2 = li.find('h2')
                    snippet_div = li.find('div', class_='b_caption') or li.find('p')
                    snippet = snippet_div.text.strip() if snippet_div else ""
                    if h2 and h2.find('a'):
                        a = h2.find('a')
                        title = a.text.strip()
                        raw_href = a.get('href', '')
                        actual_url = self._decode_bing_url(raw_href)
                        if 'linkedin.com/in/' in actual_url:
                            results.append({'title': title, 'url': actual_url, 'snippet': snippet})
        except Exception as e:
            logger.debug(f"Erreur recherche Bing: {e}")
        return results

    async def _search_duckduckgo(self, client: httpx.AsyncClient, query: str) -> List[Dict[str, str]]:
        """Search DuckDuckGo with fallback parsing."""
        results = []
        try:
            base_url = "https://html.duckduckgo.com/html/"
            headers = self._get_random_headers()
            headers['Referer'] = 'https://duckduckgo.com/'
            response = await client.post(base_url, data={'q': query}, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                for div in soup.find_all('div', class_=re.compile(r'result')):
                    a_title = div.find('a', class_=re.compile(r'result__a'))
                    snippet_tag = div.find('a', class_=re.compile(r'result__snippet'))
                    if a_title:
                        title = a_title.text.strip()
                        raw_url = a_title.get('href', '')
                        if 'uddg=' in raw_url:
                            actual_url = urllib.parse.unquote(raw_url.split('uddg=')[1].split('&')[0])
                        else:
                            actual_url = raw_url
                        if 'linkedin.com/in/' in actual_url:
                            results.append({
                                'title': title,
                                'url': actual_url,
                                'snippet': snippet_tag.text.strip() if snippet_tag else ''
                            })
        except Exception as e:
            logger.debug(f"Erreur recherche DuckDuckGo: {e}")
        return results

    def _decode_bing_url(self, href: str) -> str:
        """Decode Bing Base64 redirect link into the original target URL."""
        if 'bing.com/ck/a' in href and 'u=a1' in href:
            try:
                u_part = href.split('u=a1')[1].split('&')[0]
                padding = 4 - (len(u_part) % 4)
                if padding != 4:
                    u_part += '=' * padding
                return base64.urlsafe_b64decode(u_part).decode('utf-8', errors='ignore')
            except Exception:
                pass
        return href

    def _parse_linkedin_result(self, title: str, url: str, snippet: str) -> Optional[Contact]:
        if not re.search(r'linkedin\.com/in/', url):
            return None
            
        parsed_title = DOMParser.parse_linkedin_title(title)
        if not parsed_title.get('first_name'):
            # Try to extract name from URL slug
            slug_match = re.search(r'linkedin\.com/in/([a-zA-Z0-9\-_]+)', url)
            if slug_match:
                slug_name = slug_match.group(1).split('-')
                if len(slug_name) >= 2 and slug_name[0].isalpha() and slug_name[1].isalpha():
                    parsed_title['first_name'] = slug_name[0].capitalize()
                    parsed_title['last_name'] = slug_name[1].capitalize()

        if not parsed_title.get('first_name'):
            return None

        # Clean linkedin URL
        clean_url = url.split('?')[0]
        if not clean_url.startswith('http'):
            clean_url = f"https://{clean_url}"

        return Contact(
            first_name=parsed_title.get('first_name', ''),
            last_name=parsed_title.get('last_name', ''),
            title=parsed_title.get('title', ''),
            company=parsed_title.get('company', ''),
            linkedin_url=clean_url,
            source='xray'
        )

    def _get_random_headers(self) -> Dict[str, str]:
        return {
            'User-Agent': random.choice(self.USER_AGENTS),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
