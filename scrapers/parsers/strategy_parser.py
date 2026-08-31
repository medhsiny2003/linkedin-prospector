"""
Parseur multi-stratégies pour l'extraction des profils dans les résultats de recherche LinkedIn.
Résistant aux changements de classes CSS et aux profils masqués.
"""

from typing import Any, Dict, List, Optional
from scrapers.parsers.dom_parser import dom_parser


class StrategyParser:
    def __init__(self):
        self.card_selectors = [
            "li.org-people-profile-card__profile-card-spacing",
            ".org-people-profiles-module__profile-list > li",
            "div.org-people-profile-card",
            "div[data-test-id='profile-card']",
            "div.artdeco-entity-lockup",
            "li.reusable-search__result-container",
            "div.entity-result",
            "li[data-view-name*='search-entity-result']",
            "li.artdeco-card",
            "div.search-results-container li",
            "div[data-chameleon-result-urn]"
        ]

        self.title_selectors = [
            "h1[data-test-id='profile-name']",
            ".org-people-profile-card__profile-title",
            "div.artdeco-entity-lockup__title a",
            "div.artdeco-entity-lockup__title",
            "span.entity-result__title-text a.app-aware-link",
            "span.entity-result__title-text a",
            "a[data-test-app-aware-link]",
            "a.app-aware-link[href*='/in/']",
            "a[href*='/in/']"
        ]

        self.subtitle_selectors = [
            "div[data-test-id='profile-title']",
            ".org-people-profile-card__profile-subtitle",
            ".lt-line-clamp--multi-line",
            "div.artdeco-entity-lockup__subtitle",
            "div.entity-result__primary-subtitle",
            "div.text-body-medium",
            "div.t-14.t-black.t-normal",
            ".entity-result__summary",
            ".org-people-profile-card__profile-info p",
            ".artdeco-entity-lockup__caption"
        ]

    async def parse_cards_from_page(self, page: Any, target_company: str = "") -> List[Dict[str, str]]:
        """
        Extrait les informations des cartes de profils visibles sur la page active.
        """
        results: List[Dict[str, str]] = []

        # Recherche des cartes
        cards = []
        for sel in self.card_selectors:
            cards = await page.query_selector_all(sel)
            if cards:
                break

        if not cards:
            # Fallback direct sur les liens /in/ avec extraction contextuelle du poste
            links = await page.query_selector_all("a[href*='/in/']")
            seen_urls = set()
            for link in links:
                href = await link.get_attribute("href")
                if not href or "miniProfileUrn" in href:
                    continue
                clean_url = href.split("?")[0].rstrip("/")
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                text = await link.inner_text()
                first_name, last_name = dom_parser.parse_full_name(text)
                if first_name and last_name:
                    # Tentative de récupération du poste depuis les éléments frères/parents
                    extracted_job = ""
                    try:
                        parent_text = await page.evaluate("(el) => el.closest('li, div.artdeco-entity-lockup, div.entity-result')?.innerText || ''", link)
                        if parent_text:
                            lines = [l.strip() for l in parent_text.splitlines() if l.strip()]
                            for line in lines:
                                if line != text and len(line) > 3 and not any(w in line.lower() for w in ["suivre", "connecter", "relation", "vue", "message"]):
                                    extracted_job = line
                                    break
                    except Exception:
                        pass

                    results.append({
                        "first_name": first_name,
                        "last_name": last_name,
                        "job_title": extracted_job or "",
                        "company": target_company,
                        "location": "",
                        "profile_url": clean_url
                    })
            return results

        # Extraction structurée depuis les cartes
        for card in cards:
            try:
                title_elem = None
                for t_sel in self.title_selectors:
                    title_elem = await card.query_selector(t_sel)
                    if title_elem:
                        break

                if not title_elem:
                    continue

                raw_name = await title_elem.inner_text()
                raw_href = await title_elem.get_attribute("href")
                if not raw_href or "/in/" not in raw_href:
                    continue

                clean_url = raw_href.split("?")[0].rstrip("/")
                first_name, last_name = dom_parser.parse_full_name(raw_name)

                # Rejette immédiatement les profils masqués ou noms invalides
                if not first_name or not last_name:
                    continue

                # Extraction du sous-titre (intitulé de poste)
                subtitle_elem = None
                for s_sel in self.subtitle_selectors:
                    subtitle_elem = await card.query_selector(s_sel)
                    if subtitle_elem:
                        break

                raw_subtitle = ""
                if subtitle_elem:
                    raw_subtitle = await subtitle_elem.inner_text()

                job_title = raw_subtitle.splitlines()[0].strip() if raw_subtitle else ""

                # Extraction du lieu / localisation géographique
                loc_elem = await card.query_selector("div.entity-result__secondary-subtitle, div.t-12.t-black--light, .search-nec__location")
                raw_loc = await loc_elem.inner_text() if loc_elem else ""

                results.append({
                    "first_name": first_name,
                    "last_name": last_name,
                    "job_title": job_title or "Collaborateur",
                    "company": target_company,
                    "location": raw_loc.strip(),
                    "profile_url": clean_url
                })
            except Exception:
                continue

        return results


strategy_parser = StrategyParser()
