"""
Scraper de navigation Playwright haute fidélité (Company People & X-Ray Engine).
Extrait les profils de décideurs directement depuis les pages Entreprises officielles
et utilise le moteur X-Ray pour garantir 100% de vrais noms sans limitation LinkedIn.
"""

import asyncio
import re
import urllib.parse
from typing import Any, Callable, Dict, List, Optional
from playwright.async_api import Page
from config import config
from core.monitoring.audit_logger import audit_logger
from core.security.rate_limiter import rate_limiter
from core.security.risk_detector import risk_detector
from enricher.company_resolver import company_resolver
from scrapers.parsers.dom_parser import dom_parser
from scrapers.parsers.strategy_parser import strategy_parser


class LinkedInBrowserScraper:
    def __init__(self):
        self.xray_failures = 0
        self.xray_cooldown = False

    async def safe_goto(self, page: Page, url: str, timeout: int = 25000) -> bool:
        """Navigue de manière tolérante et sécurisée."""
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            await asyncio.sleep(1.5)
            return True
        except Exception as e:
            audit_logger.log_event("NAV_SEARCH_WARN", f"Avertissement navigation : {e}")
            try:
                await page.goto(url, timeout=timeout)
                await asyncio.sleep(1.5)
                return True
            except Exception:
                return False

    async def perform_decoy_activity(self, page: Page) -> None:
        """Consultation naturelle du fil d'actualité pour simuler une session humaine."""
        try:
            audit_logger.log_event("DECOY_START", "Consultation naturelle du fil d'actualité...")
            await self.safe_goto(page, "https://www.linkedin.com/feed/", timeout=20000)
            await asyncio.sleep(2)
            await rate_limiter.simulate_human_scroll(page, min_scrolls=2, max_scrolls=3)
            await rate_limiter.wait_human_delay(median_sec=3.0)
        except Exception as e:
            audit_logger.log_event("DECOY_WARN", f"Activité decoy partielle : {e}")

    async def search_and_scrape(
        self,
        page: Page,
        company: str,
        keywords: str,
        location: str = "France",
        max_profiles: int = 10,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> List[Dict[str, str]]:
        """
        Architecture d'extraction ciblée :
        1. Section 'Personnes' de la page Entreprise officielle (/company/{slug}/people/)
        2. Moteur X-Ray Public Search (Bing) pour garantir 100% de vrais noms de décideurs.
        """
        if stop_check and stop_check():
            return []

        official_name, slug, domain = company_resolver.resolve(company)
        extracted_profiles: List[Dict[str, str]] = []

        # --- 1. Extraction sur la Section Personnes de la Page Entreprise ---
        if slug:
            loc_clean = location.strip()
            if "maroc" in loc_clean.lower():
                loc_keyword = "Maroc"
            elif "france" in loc_clean.lower():
                loc_keyword = "France"
            elif loc_clean.lower() in ["international", "monde", "tous", "all"]:
                loc_keyword = ""
            else:
                loc_keyword = loc_clean.split(",")[0].strip()

            search_query = f"{keywords} {loc_keyword}".strip() if loc_keyword else keywords
            company_people_url = f"https://www.linkedin.com/company/{slug}/people/?keywords={urllib.parse.quote(search_query)}"
            audit_logger.log_event("COMPANY_PEOPLE_NAV", f"Navigation vers la page Entreprise : {official_name} (/company/{slug}/people/?keywords={search_query})")
            
            nav_ok = await self.safe_goto(page, company_people_url, timeout=25000)
            if stop_check and stop_check():
                return []
            await asyncio.sleep(1.5)

            if nav_ok:
                page_title = (await page.title() or "").lower()
                current_url = page.url.lower()

                # Détection d'une fausse page entreprise ou page 404 introuvable
                if "page introuvable" in page_title or "404" in page_title or "/404/" in current_url or "page not found" in page_title or "cette page n'existe pas" in page_title:
                    audit_logger.log_event("COMPANY_PAGE_404", f"Page LinkedIn Entreprise introuvable pour '{official_name}'. Basculement immédiat vers le moteur X-Ray haute fidélité...")
                    cards_data = []
                else:
                    # Défilement adaptatif exhaustif pour charger un maximum de cartes d'employés
                    last_card_count = 0
                    consecutive_same_count = 0
                    for _ in range(12):
                        if stop_check and stop_check():
                            break
                        await rate_limiter.simulate_human_scroll(page, min_scrolls=1, max_scrolls=2)
                        await asyncio.sleep(0.8)
                        current_cards = await strategy_parser.parse_cards_from_page(page, target_company=official_name)
                        if len(current_cards) >= max_profiles * 2:
                            break
                        if len(current_cards) == last_card_count:
                            consecutive_same_count += 1
                            if consecutive_same_count >= 2:
                                break
                        else:
                            consecutive_same_count = 0
                        last_card_count = len(current_cards)

                    cards_data = await strategy_parser.parse_cards_from_page(page, target_company=official_name)

                loc_clean_check = location.strip().lower()
                for card in cards_data:
                    if stop_check and stop_check():
                        break

                    card_loc = card.get("location", "").lower()
                    if "maroc" in loc_clean_check:
                        is_maroc = any(m in card_loc for m in ["maroc", "morocco", "casablanca", "rabat", "tanger", "kenitra", "marrakech", "benguerir", "agadir", "fès", "fes", "oujda", "salé", "el jadida", "tétouan", "laayoune", "dakhla", "nador", "meknès", "meknes"])
                        is_foreign = any(c in card_loc for c in ["france", "paris", "lyon", "toulouse", "bordeaux", "nantes", "marseille", "lille", "rennes", "belgique", "suisse", "canada", "espagne"])
                        if is_foreign or (card_loc and not is_maroc):
                            continue
                    elif "france" in loc_clean_check:
                        if any(m in card_loc for m in ["maroc", "morocco", "casablanca", "rabat", "algerie", "tunisie"]) and not any(f in card_loc for f in ["france", "paris", "lyon"]):
                            continue

                    if not any(p["profile_url"] == card["profile_url"] for p in extracted_profiles):
                        card["matched_keywords"] = f"{official_name}, {keywords} (Page Entreprise)"
                        card["company"] = official_name
                        card["domain"] = domain
                        extracted_profiles.append(card)
                        if len(extracted_profiles) >= max_profiles:
                            break

        # --- 2. Moteur X-Ray Search Multi-Moteurs (Bing + Google) pour compléter ---
        if len(extracted_profiles) < max_profiles and not (stop_check and stop_check()):
            needed = max_profiles - len(extracted_profiles)
            audit_logger.log_event("XRAY_START", f"Activation X-Ray pour {official_name} ({needed} profils requis)...")
            
            xray_leads = await self.scrape_xray(page, official_name, keywords, location, max_profiles=needed, stop_check=stop_check)
            for xl in xray_leads:
                if stop_check and stop_check():
                    break
                if not any(p["profile_url"] == xl["profile_url"] for p in extracted_profiles):
                    xl["domain"] = domain
                    extracted_profiles.append(xl)
                    if len(extracted_profiles) >= max_profiles:
                        break

        audit_logger.log_event(
            "SEARCH_COMPLETED",
            f"{len(extracted_profiles)} profils réels extraits pour {official_name} ({keywords})."
        )
        return extracted_profiles

    async def scrape_xray(
        self,
        page: Page,
        company: str,
        keywords: str,
        location: str = "France",
        max_profiles: int = 10,
        stop_check: Optional[Callable[[], bool]] = None
    ) -> List[Dict[str, str]]:
        """
        Recherche X-Ray sur profils publics indexés via Bing et Google avec Pagination Multi-Pages et Circuit Breaker.
        Garantit 100% de vrais noms de décideurs sans limitation LinkedIn.
        """
        if self.xray_failures >= 3:
            audit_logger.log_event("CIRCUIT_BREAKER", "Circuit Breaker X-Ray actif : pause de 15s...")
            await asyncio.sleep(15)
            self.xray_failures = 0

        # Construction optimisée de la requête multi-mots-clés en OR et géolocalisation forte
        # Les mots-clés configurés par l'utilisateur sont prioritaires à 100%
        kw_list = [k.strip() for k in re.split(r'[,;]+', keywords) if k.strip()]
        kw_terms = [f'"{k}"' for k in kw_list] if kw_list else []
        standard_terms = ['"RH"', '"Recruteur"', '"Manager"', '"Directeur"', '"Responsable"', '"Chef de projet"', '"Ingénieur"', '"Technicien"']
        all_terms = list(dict.fromkeys(kw_terms + standard_terms))
        or_clause = " OR ".join(all_terms[:8])

        loc_clean = location.strip().lower()
        if "maroc" in loc_clean or "morocco" in loc_clean:
            loc_term = '("Maroc" OR "Morocco" OR "Casablanca" OR "Rabat" OR "Tanger" OR "Kenitra" OR "Marrakech" OR "Fès" OR "Benguerir" OR "Agadir")'
            comp_search = f'("{company}" OR "{company} Maroc")'
            query = f'site:linkedin.com/in/ {comp_search} ({or_clause}) {loc_term} -site:fr.linkedin.com/in/'.strip()
        elif "france" in loc_clean:
            loc_term = '("France" OR "Paris" OR "Lyon" OR "Toulouse" OR "Bordeaux" OR "Nantes" OR "Marseille" OR "Lille")'
            query = f'site:linkedin.com/in/ "{company}" ({or_clause}) {loc_term}'.strip()
        elif loc_clean in ["international", "monde", "tous", "all"]:
            query = f'site:linkedin.com/in/ "{company}" ({or_clause})'.strip()
        else:
            query = f'site:linkedin.com/in/ "{company}" ({or_clause}) "{location}"'.strip()

        bing_base_url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        xray_leads: List[Dict[str, str]] = []

        # 1. Pagination X-Ray sur Bing (jusqu'à 4 pages = 40 résultats)
        for page_idx in range(4):
            if len(xray_leads) >= max_profiles or (stop_check and stop_check()):
                break

            offset = page_idx * 10 + 1
            bing_page_url = f"{bing_base_url}&first={offset}" if page_idx > 0 else bing_base_url

            nav_ok = await self.safe_goto(page, bing_page_url, timeout=15000)
            await rate_limiter.wait_human_delay(median_sec=2.0)

            if not nav_ok:
                self.xray_failures += 1
                break

            items = await page.query_selector_all("li.b_algo")
            if not items:
                if page_idx == 0:
                    self.xray_failures += 1
                break
            else:
                self.xray_failures = 0

            for item in items:
                if len(xray_leads) >= max_profiles or (stop_check and stop_check()):
                    break
                try:
                    h2 = await item.query_selector("h2 a")
                    snip = await item.query_selector(".b_caption p")
                    if not h2:
                        continue

                    raw_title = await h2.inner_text()
                    raw_href = await h2.get_attribute("href")
                    raw_snippet = await snip.inner_text() if snip else ""

                    # Extraction propre du nom
                    name_candidate = raw_title.split(" - ")[0].split(" | ")[0].strip()
                    first_name, last_name = dom_parser.parse_full_name(name_candidate)

                    if first_name and last_name:
                        full_text = f"{raw_title} {raw_snippet}".lower()

                        # 1. Contrôle géographique strict
                        if "maroc" in loc_clean:
                            has_maroc = any(city in full_text for city in ["maroc", "morocco", "casablanca", "rabat", "tanger", "kenitra", "marrakech", "benguerir", "agadir", "fès", "fes", "oujda", "salé", "el jadida", "tétouan", "laayoune", "dakhla", "nador", "meknès", "meknes"]) or "ma.linkedin.com" in raw_href
                            has_foreign_only = any(city in full_text for city in ["région de paris", "lyon, france", "paris, france", "toulouse, france", "bordeaux, france", "nantes, france", "marseille, france", "lille, france", "île-de-france", "ile-de-france", "hauts-de-france", "auvergne-rhône-alpes", "nouvelle-aquitaine", "occitanie", "grand est", "pays de la loire", "bretagne, france", "normandie, france"]) or "fr.linkedin.com" in raw_href
                            if has_foreign_only and not has_maroc:
                                continue
                            if not has_maroc and not ("maroc" in company.lower()):
                                continue
                        elif "france" in loc_clean:
                            has_france = any(city in full_text for city in ["france", "paris", "lyon", "toulouse", "bordeaux", "nantes", "marseille", "lille", "strasbourg", "rennes"]) or "fr.linkedin.com" in raw_href
                            has_foreign_only = any(city in full_text for city in ["casablanca", "rabat", "tanger", "maroc", "morocco", "algerie", "tunisie"])
                            if has_foreign_only and not has_france:
                                continue

                        # 2. Dissociation stricte Nom de la personne vs Nom de l'entreprise
                        text_without_person = full_text.replace(name_candidate.lower(), "").replace(first_name.lower(), "").replace(last_name.lower(), "")
                        comp_clean = company.lower().strip()
                        comp_base = re.sub(r'\b(maroc|france|group|groupe|technologies|systems|corporation|international|sa|sas|bank|banque|solutions|facilities)\b', '', comp_clean).strip()

                        is_company_mentioned = (
                            comp_clean in text_without_person or
                            (comp_base and len(comp_base) >= 3 and comp_base in text_without_person) or
                            f"chez {comp_clean}" in full_text or
                            f"at {comp_clean}" in full_text or
                            f"@{comp_clean}" in full_text or
                            (comp_base and f"chez {comp_base}" in full_text)
                        )

                        if not is_company_mentioned:
                            continue  # Rejette les homonymies de nom/prénom (ex: personne nommée Saber alors que l'entreprise est Seaber)

                        # 3. Filtrage des métiers non pertinents
                        unrelated_keywords = ["caissier", "magasinier", "agent de securite", "plombier", "infirmier", "chauffeur"]
                        if any(uk in full_text for uk in unrelated_keywords):
                            continue

                        job = ""
                        if " - " in raw_title:
                            job = raw_title.split(" - ")[1].split(" | ")[0].strip()
                        elif raw_snippet:
                            job = raw_snippet[:80].strip()

                        clean_profile_url = raw_href.split("?")[0].rstrip("/")
                        if not any(xl["profile_url"] == clean_profile_url for xl in xray_leads):
                            xray_leads.append({
                                "first_name": first_name,
                                "last_name": last_name,
                                "job_title": job or keywords,
                                "company": company,
                                "profile_url": clean_profile_url,
                                "matched_keywords": f"{company}, {keywords} (Bing X-Ray)"
                            })
                except Exception:
                    continue

        # 2. Recherche complémentaire sur Google Search si le quota n'est pas atteint
        if len(xray_leads) < max_profiles and not (stop_check and stop_check()):
            google_base_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=fr"
            for g_page in range(2):
                if len(xray_leads) >= max_profiles or (stop_check and stop_check()):
                    break

                g_offset = g_page * 10
                g_url = f"{google_base_url}&start={g_offset}" if g_page > 0 else google_base_url
                nav_ok = await self.safe_goto(page, g_url, timeout=15000)
                await rate_limiter.wait_human_delay(median_sec=2.0)

                if not nav_ok:
                    break

                g_items = await page.query_selector_all("div.g, div.tF2Cxc, div.MjjYud")
                for item in g_items:
                    if len(xray_leads) >= max_profiles or (stop_check and stop_check()):
                        break
                    try:
                        h3 = await item.query_selector("h3")
                        link = await item.query_selector("a[href*='linkedin.com/in/']")
                        snip = await item.query_selector("div.VwiC3b, span.aCOpRe, div[style*='-webkit-line-clamp']")
                        if not h3 or not link:
                            continue

                        raw_title = await h3.inner_text()
                        raw_href = await link.get_attribute("href")
                        raw_snippet = await snip.inner_text() if snip else ""

                        name_candidate = raw_title.split(" - ")[0].split(" | ")[0].strip()
                        first_name, last_name = dom_parser.parse_full_name(name_candidate)

                        if first_name and last_name:
                            full_text = f"{raw_title} {raw_snippet}".lower()

                            # 1. Contrôle géographique
                            if "maroc" in loc_clean:
                                has_maroc = any(city in full_text for city in ["maroc", "morocco", "casablanca", "rabat", "tanger", "kenitra", "marrakech", "benguerir", "agadir", "fès", "fes", "oujda", "salé", "el jadida", "tétouan", "laayoune", "dakhla", "nador", "meknès", "meknes"]) or "ma.linkedin.com" in raw_href
                                has_foreign_only = any(city in full_text for city in ["région de paris", "lyon, france", "paris, france", "toulouse, france", "bordeaux, france", "nantes, france", "marseille, france", "lille, france", "île-de-france", "ile-de-france"]) or "fr.linkedin.com" in raw_href
                                if has_foreign_only and not has_maroc:
                                    continue
                                if not has_maroc and not ("maroc" in company.lower()):
                                    continue

                            # 2. Dissociation Nom vs Entreprise
                            text_without_person = full_text.replace(name_candidate.lower(), "").replace(first_name.lower(), "").replace(last_name.lower(), "")
                            comp_clean = company.lower().strip()
                            comp_base = re.sub(r'\b(maroc|france|group|groupe|technologies|systems|corporation|international|sa|sas|bank|banque|solutions|facilities)\b', '', comp_clean).strip()

                            is_company_mentioned = (
                                comp_clean in text_without_person or
                                (comp_base and len(comp_base) >= 3 and comp_base in text_without_person) or
                                f"chez {comp_clean}" in full_text or
                                f"at {comp_clean}" in full_text or
                                f"@{comp_clean}" in full_text or
                                (comp_base and f"chez {comp_base}" in full_text)
                            )

                            if not is_company_mentioned:
                                continue

                            job = ""
                            if " - " in raw_title:
                                job = raw_title.split(" - ")[1].split(" | ")[0].strip()
                            elif raw_snippet:
                                job = raw_snippet[:80].strip()

                            clean_profile_url = raw_href.split("?")[0].rstrip("/")
                            if not any(xl["profile_url"] == clean_profile_url for xl in xray_leads):
                                xray_leads.append({
                                    "first_name": first_name,
                                    "last_name": last_name,
                                    "job_title": job or keywords,
                                    "company": company,
                                    "profile_url": clean_profile_url,
                                    "matched_keywords": f"{company}, {keywords} (Google X-Ray)"
                                })
                    except Exception:
                        continue

        return xray_leads


linkedin_browser_scraper = LinkedInBrowserScraper()
