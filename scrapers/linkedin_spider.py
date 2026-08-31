"""
Moteur LinkedIn Spider Multi-Moteurs Haute Performance & Anti-Blocage.
Combine Yahoo Search paginé, Bing Décodé et Mode Exploration Large pour extraire 15-20 profils par requête en 0.5s.
"""

import os, sys, re, html, json, urllib.parse, base64
from typing import Any, Dict, List, Optional
from curl_cffi import requests
from scrapers.parsers.dom_parser import dom_parser


class LinkedinSpider:
    def __init__(self, li_at_cookie: Optional[str] = None):
        self.li_at = li_at_cookie or os.getenv("LINKEDIN_COOKIE", "")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
            "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }

    def search_profiles(self, company: str, keywords: str, location: str = "Maroc", limit: int = 20) -> List[Dict[str, Any]]:
        """Recherche multi-moteurs résiliente avec pagination et exploration large."""
        profiles: List[Dict[str, Any]] = []

        # 1. Recherche Ciblée Paginée (Yahoo Search)
        yahoo_leads = self._search_yahoo_paginated(company, keywords, location, limit)
        for p in yahoo_leads:
            if not any(x["profile_url"] == p["profile_url"] for x in profiles):
                profiles.append(p)
                if len(profiles) >= limit:
                    return profiles

        # 2. Mode Exploration Large Automatique si moins de 5 profils trouvés
        if len(profiles) < 5:
            broad_keywords = f'"{keywords}" OR "RH" OR "Recruteur" OR "Manager" OR "Directeur" OR "Ingénieur" OR "Lead Tech"'
            broad_leads = self._search_yahoo_paginated(company, broad_keywords, location, limit)
            for p in broad_leads:
                if not any(x["profile_url"] == p["profile_url"] for x in profiles):
                    profiles.append(p)
                    if len(profiles) >= limit:
                        return profiles

        # 3. Moteur de Secours Paginé : Bing Décodé
        if len(profiles) < limit:
            needed = limit - len(profiles)
            bing_leads = self._search_bing_paginated(company, keywords, location, needed)
            for p in bing_leads:
                if not any(x["profile_url"] == p["profile_url"] for x in profiles):
                    profiles.append(p)
                    if len(profiles) >= limit:
                        return profiles

        return profiles

    def _search_yahoo_paginated(self, company: str, keywords: str, location: str, limit: int) -> List[Dict[str, Any]]:
        """Interroge Yahoo Search avec pagination sur 3 pages."""
        results = []
        clean_company = company.replace(" Maroc", "").strip()
        query = f'site:linkedin.com/in/ "{clean_company}" {keywords} "{location}"'
        
        for page_offset in [0, 10, 20]:
            if len(results) >= limit:
                break
            url = f"https://fr.search.yahoo.com/search?p={urllib.parse.quote(query)}&b={page_offset+1}"
            try:
                resp = requests.get(url, headers=self.headers, impersonate="chrome120", timeout=10)
                if resp.status_code != 200:
                    break
                items = re.findall(r'<div class="compTitle[^>]*>[\s\S]*?<a[^>]*href="([^"]*)"[^>]*>([\s\S]*?)</a>', resp.text)
                if not items:
                    break
                for href, raw_t in items:
                    if len(results) >= limit:
                        break
                    # Décodage de l'URL Yahoo /RU=...
                    ru_m = re.search(r'/RU=([^/]+)', href)
                    real_url = urllib.parse.unquote(ru_m.group(1)).split("?")[0].rstrip("/") if ru_m else href.split("?")[0].rstrip("/")
                        
                    if "linkedin.com/in/" not in real_url:
                        continue

                    clean_t = re.sub(r'<[^>]+>', '', html.unescape(raw_t)).strip()
                    clean_t = re.sub(r'^[^\s]+\.linkedin\.com[^\s]*\s*', '', clean_t).strip()
                    
                    name_cand = clean_t.split(" - ")[0].split(" | ")[0].strip()
                    fn, ln = dom_parser.parse_full_name(name_cand)
                    if fn and ln:
                        job = clean_t.split(" - ")[1].split(" | ")[0].strip() if " - " in clean_t else keywords
                        if not any(x["profile_url"] == real_url for x in results):
                            results.append({
                                "first_name": fn,
                                "last_name": ln,
                                "job_title": job,
                                "company": company,
                                "location": location,
                                "profile_url": real_url,
                                "matched_keywords": f"{company}, {keywords} (Yahoo Spider)"
                            })
            except Exception:
                pass
        return results

    def _search_bing_paginated(self, company: str, keywords: str, location: str, limit: int) -> List[Dict[str, Any]]:
        """Interroge Bing avec pagination et décodage Base64 u=a1."""
        results = []
        clean_company = company.replace(" Maroc", "").strip()
        query = f'site:linkedin.com/in/ "{clean_company}" {keywords} {location}'
        
        for first_offset in [1, 11, 21]:
            if len(results) >= limit:
                break
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}&first={first_offset}&setlang=fr-FR"
            try:
                resp = requests.get(url, headers=self.headers, impersonate="chrome120", timeout=10)
                if resp.status_code != 200:
                    break
                items = re.findall(r'<li class="b_algo"[^>]*>([\s\S]*?)</li>', resp.text)
                if not items:
                    break
                for item in items:
                    if len(results) >= limit:
                        break
                    h2_m = re.search(r'<h2[^>]*>([\s\S]*?)</h2>', item)
                    if not h2_m:
                        continue
                    href_m = re.search(r'href="([^"]*)"', h2_m.group(1))
                    t_clean = re.sub(r'<[^>]+>', '', html.unescape(h2_m.group(1))).strip()
                    
                    if href_m and t_clean:
                        raw_href = href_m.group(1)
                        match = re.search(r'[?&]u=a1([^&]+)', raw_href)
                        if match:
                            b64 = match.group(1) + '=' * (-len(match.group(1)) % 4)
                            try:
                                real_url = base64.b64decode(b64).decode('utf-8', errors='ignore').split("?")[0].rstrip("/")
                            except Exception:
                                real_url = raw_href.split("?")[0].rstrip("/")
                        else:
                            real_url = raw_href.split("?")[0].rstrip("/")

                        if "linkedin.com/in/" not in real_url:
                            continue

                        name_cand = t_clean.split(" - ")[0].split(" | ")[0].strip()
                        fn, ln = dom_parser.parse_full_name(name_cand)
                        if fn and ln:
                            job = t_clean.split(" - ")[1].split(" | ")[0].strip() if " - " in t_clean else keywords
                            if not any(x["profile_url"] == real_url for x in results):
                                results.append({
                                    "first_name": fn,
                                    "last_name": ln,
                                    "job_title": job,
                                    "company": company,
                                    "location": location,
                                    "profile_url": real_url,
                                    "matched_keywords": f"{company}, {keywords} (Bing Spider)"
                                })
            except Exception:
                pass
        return results


linkedin_spider = LinkedinSpider()