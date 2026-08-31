"""
Moteur 3 : OSINT & Dorks Search (Open Source Intelligence).
Interroge les moteurs publics pour retrouver les emails exacts indexés sur le web.
"""

import re
import urllib.request
import urllib.parse
from typing import List, Set


class OSINTSearcher:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def search_person_email_dork(self, first_name: str, last_name: str, domain: str) -> List[str]:
        """
        Recherche par Google/Bing Dorks les mentions publiques d'adresses emails de cette personne.
        """
        if not first_name or not last_name or not domain or domain == "gmail.com":
            return []

        f = first_name.strip().lower()
        l = last_name.strip().lower()
        query = f'"{f} {l}" "@{domain}"'
        bing_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"

        discovered = set()
        try:
            req = urllib.request.Request(bing_url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    html = resp.read().decode('utf-8', errors='ignore')
                    pattern = r'[a-zA-Z0-9_.+-]+@' + re.escape(domain)
                    matches = re.findall(pattern, html, re.IGNORECASE)
                    for m in matches:
                        email_clean = m.lower().strip()
                        if f in email_clean or l in email_clean or (f[0] + l) in email_clean:
                            discovered.add(email_clean)
        except Exception:
            pass

        return list(discovered)


osint_searcher = OSINTSearcher()
