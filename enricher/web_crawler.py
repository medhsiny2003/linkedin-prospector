"""
Moteur 2 : Crawling Web & Extraction d'Emails Publics (Website Scraping).
Explore les pages publiques d'entreprises (contact, équipe, mentions légales)
pour extraire les adresses emails officielles publiées sur leur domaine.
"""

import re
import urllib.request
import urllib.parse
from typing import List, Set


class WebEmailCrawler:
    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

    def fetch_page_emails(self, url: str, target_domain: str) -> Set[str]:
        """Télécharge une page web et extrait tous les emails appartenant au target_domain."""
        found_emails = set()
        try:
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                if resp.status == 200:
                    html = resp.read().decode('utf-8', errors='ignore')
                    # Regex robuste d'extraction d'emails
                    email_pattern = r'[a-zA-Z0-9_.+-]+@' + re.escape(target_domain)
                    matches = re.findall(email_pattern, html, re.IGNORECASE)
                    for m in matches:
                        clean_email = m.lower().strip()
                        # Filtrage des faux positifs (images, polices)
                        if not any(clean_email.endswith(ext) for ext in ['.png', '.jpg', '.svg', '.webp']):
                            found_emails.add(clean_email)
        except Exception:
            pass
        return found_emails

    def crawl_company_domain(self, domain: str) -> List[str]:
        """
        Explore les points d'entrée clés du site officiel de l'entreprise.
        """
        domain = domain.strip().lower()
        if not domain or domain == "gmail.com":
            return []

        endpoints = [
            f"https://www.{domain}",
            f"https://{domain}",
            f"https://www.{domain}/contact",
            f"https://www.{domain}/mentions-legales",
            f"https://www.{domain}/about",
            f"https://www.{domain}/equipe",
            f"https://www.{domain}/team"
        ]

        discovered_emails = set()
        for ep in endpoints:
            emails = self.fetch_page_emails(ep, domain)
            discovered_emails.update(emails)
            if len(discovered_emails) >= 10:
                break

        return list(discovered_emails)


web_email_crawler = WebEmailCrawler()
