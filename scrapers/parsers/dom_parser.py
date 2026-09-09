import re
from typing import Dict, List, Tuple
from bs4 import BeautifulSoup

class DOMParser:
    @staticmethod
    def parse_search_results(html: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, 'html.parser')
        results = []
        
        for result in soup.find_all('div', class_='result'):
            title_tag = result.find('a', class_='result__url')
            snippet_tag = result.find('a', class_='result__snippet')
            
            if title_tag and snippet_tag:
                url = title_tag.get('href', '')
                if url.startswith('//duckduckgo.com/l/?'):
                    # Could parse actual URL if needed, but DDG html returns direct links sometimes
                    # Or we extract from result__url text
                    url = title_tag.text.strip()
                
                title_text = result.find('h2', class_='result__title')
                title = title_text.text.strip() if title_text else ""
                snippet = snippet_tag.text.strip()
                
                results.append({
                    'title': title,
                    'url': url,
                    'snippet': snippet
                })
        return results

    @staticmethod
    def parse_linkedin_title(title: str) -> Dict[str, str]:
        # Typical format: "FirstName LastName - Title - Company | LinkedIn"
        # Or: "FirstName LastName - Title | LinkedIn"
        # Or: "FirstName LastName | LinkedIn"
        
        clean_title = title.replace(" | LinkedIn", "").strip()
        parts = [p.strip() for p in clean_title.split(" - ")]
        
        result = {
            'first_name': '',
            'last_name': '',
            'title': '',
            'company': ''
        }
        
        if len(parts) >= 1:
            name_parts = DOMParser.clean_name(parts[0])
            result['first_name'] = name_parts[0]
            result['last_name'] = name_parts[1]
            
        if len(parts) == 2:
            result['title'] = parts[1]
        elif len(parts) >= 3:
            result['title'] = parts[1]
            result['company'] = parts[2]
            
        return result

    @staticmethod
    def parse_company_people_page(html: str) -> List[Dict[str, str]]:
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.find_all('li', class_=re.compile(r'org-people-profile-card'))
        
        results = []
        for card in cards:
            name_tag = card.find('div', class_=re.compile(r'org-people-profile-card__profile-title'))
            title_tag = card.find('div', class_=re.compile(r'lt-line-clamp--multi-line'))
            link_tag = card.find('a', href=True)
            
            if name_tag:
                name = name_tag.text.strip()
                title = title_tag.text.strip() if title_tag else ""
                url = link_tag['href'] if link_tag else ""
                if url and not url.startswith('http'):
                    url = f"https://www.linkedin.com{url}"
                    
                results.append({
                    'name': name,
                    'title': title,
                    'url': url
                })
        return results

    @staticmethod
    def clean_name(name: str) -> Tuple[str, str]:
        # Handle compound names and particles
        name = name.strip()
        if not name:
            return "", ""
            
        parts = name.split()
        if len(parts) == 1:
            return parts[0], ""
            
        particles = {'de', 'du', 'le', 'la', 'van', 'von', 'der', 'den', 'da', 'di'}
        
        first_name = parts[0]
        last_name_parts = []
        
        i = 1
        while i < len(parts):
            if parts[i].lower() in particles:
                last_name_parts.append(parts[i])
            else:
                last_name_parts.extend(parts[i:])
                break
            i += 1
            
        last_name = " ".join(last_name_parts)
        if not last_name:
            last_name = " ".join(parts[1:])
            
        return first_name, last_name
