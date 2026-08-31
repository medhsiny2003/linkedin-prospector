"""
Orchestrateur Central d'Intelligence d'Emails (Architecture 5 Couches).
Coordonne l'exécution parallèle des 4 Moteurs d'Acquisition (Base Interne, Crawling Web, OSINT, Permutation),
l'Agrégation pondérée, la Validation MX/Catch-All et l'Auto-Apprentissage continu.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional
from config import config
from enricher.company_resolver import company_resolver
from enricher.email_generator import email_generator
from enricher.email_validator import email_validator
from enricher.osint_searcher import osint_searcher
from enricher.pattern_learner import pattern_learner
from enricher.web_crawler import web_email_crawler


class EmailOrchestrator:
    def __init__(self, max_workers: int = 4, timeout: float = 1.5):
        self.max_workers = max_workers
        self.timeout = timeout

    def discover_and_validate(
        self,
        first_name: str,
        last_name: str,
        company_name: str,
        fast_mode: bool = False
    ) -> Dict[str, any]:
        """
        Pipeline complet d'intelligence d'emails (5 Couches) :
        1. Input & Résolution de domaine
        2. Acquisition parallèle (4 Moteurs ou Mode Rapide)
        3. Agrégation & Scoring pondéré
        4. Validation MX / Catch-All
        5. Auto-Apprentissage et mise à jour de la base interne
        """
        if not first_name or not last_name:
            return {
                "proposed_email": "",
                "alt_email_1": "",
                "alt_email_2": "",
                "confidence_score": 0,
                "domain": "",
                "status": "Non vérifiable",
                "mx_verified": "Non",
                "source": "Aucune"
            }

        official_company, _, domain = company_resolver.resolve(company_name)
        if not domain:
            domain = email_generator.resolve_domain(company_name)

        # Structure de collecte des résultats pondérés
        candidates_scores: Dict[str, Dict[str, any]] = {}

        # --- COUCHE 2 : EXÉCUTION DES MOTEURS D'ACQUISITION ---
        if fast_mode:
            # Mode rapide (Base interne + 22 Permutations Déterministes)
            learned = pattern_learner.get_learned_pattern(domain)
            if learned and "confirmed_pattern" in learned:
                pat = learned["confirmed_pattern"]
                f_clean = email_generator.clean_name_part(first_name).replace('-', '')
                l_clean = email_generator.clean_name_part(last_name).replace('-', '')
                m1_email = pat.format(first=f_clean, last=l_clean, f=f_clean[0], l=l_clean[0], domain=domain)
                candidates_scores[m1_email] = {
                    "email": m1_email,
                    "confidence": 98,
                    "source": "Base Interne (Pattern Appris)"
                }

            perm_candidates = email_generator.generate_candidates(first_name, last_name, official_company)
            for pc in perm_candidates:
                em = pc["email"]
                if em not in candidates_scores:
                    candidates_scores[em] = {
                        "email": em,
                        "confidence": pc["confidence"],
                        "source": "Permutation Déterministe"
                    }
        else:
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Moteur 1 : Base Interne Apprenante (Priorité Absolue)
                future_m1 = executor.submit(pattern_learner.get_learned_pattern, domain)
                # Moteur 2 : Crawling Web
                future_m2 = executor.submit(web_email_crawler.crawl_company_domain, domain)
                # Moteur 3 : OSINT & Dorks Search
                future_m3 = executor.submit(osint_searcher.search_person_email_dork, first_name, last_name, domain)
                # Moteur 4 : Permutations Intelligentes
                future_m4 = executor.submit(email_generator.generate_candidates, first_name, last_name, official_company)

                # Collecte Moteur 1 (Base Interne)
                try:
                    learned = future_m1.result(timeout=self.timeout)
                    if learned and "confirmed_pattern" in learned:
                        pat = learned["confirmed_pattern"]
                        f_clean = email_generator.clean_name_part(first_name).replace('-', '')
                        l_clean = email_generator.clean_name_part(last_name).replace('-', '')
                        m1_email = pat.format(first=f_clean, last=l_clean, f=f_clean[0], l=l_clean[0], domain=domain)
                        candidates_scores[m1_email] = {
                            "email": m1_email,
                            "confidence": 98,
                            "source": "Base Interne (Pattern Appris)"
                        }
                except Exception:
                    pass

                # Collecte Moteur 2 (Crawling Web)
                try:
                    web_emails = future_m2.result(timeout=self.timeout)
                    f_low = first_name.lower().strip()
                    l_low = last_name.lower().strip()
                    for we in web_emails:
                        if f_low in we or l_low in we:
                            candidates_scores[we] = {
                                "email": we,
                                "confidence": 95,
                                "source": "Crawling Site Officiel"
                            }
                except Exception:
                    pass

                # Collecte Moteur 3 (OSINT Dorks)
                try:
                    osint_emails = future_m3.result(timeout=self.timeout)
                    for oe in osint_emails:
                        candidates_scores[oe] = {
                            "email": oe,
                            "confidence": 92,
                            "source": "OSINT & Dorks Publics"
                        }
                except Exception:
                    pass

                # Collecte Moteur 4 (Permutation)
                try:
                    perm_candidates = future_m4.result(timeout=self.timeout)
                    for pc in perm_candidates:
                        em = pc["email"]
                        if em not in candidates_scores:
                            candidates_scores[em] = {
                                "email": em,
                                "confidence": pc["confidence"],
                                "source": "Permutation Déterministe"
                            }
                except Exception:
                    pass

        # --- COUCHE 3 : AGRÉGATION & SCORING ---
        if not candidates_scores:
            return {
                "proposed_email": "",
                "alt_email_1": "",
                "alt_email_2": "",
                "confidence_score": 0,
                "domain": domain,
                "status": "Non vérifiable",
                "mx_verified": "Non",
                "source": "Aucune"
            }

        # Tri des candidats par score de confiance décroissant
        sorted_candidates = sorted(candidates_scores.values(), key=lambda x: x["confidence"], reverse=True)
        top_email = sorted_candidates[0]["email"]
        top_score = sorted_candidates[0]["confidence"]
        top_source = sorted_candidates[0]["source"]

        alt_1 = sorted_candidates[1]["email"] if len(sorted_candidates) > 1 else ""
        alt_2 = sorted_candidates[2]["email"] if len(sorted_candidates) > 2 else ""

        # --- COUCHE 4 : VALIDATION MX & CATCH-ALL ---
        val_result = email_validator.validate(top_email)

        # --- COUCHE 5 : AUTO-APPRENTISSAGE ---
        if val_result.get("mx_verified") == "Oui" and top_score >= 80:
            pattern_learner.learn_pattern(first_name, last_name, top_email, official_company)

        return {
            "proposed_email": top_email,
            "alt_email_1": alt_1,
            "alt_email_2": alt_2,
            "confidence_score": top_score,
            "domain": domain,
            "status": val_result.get("status", "Validé"),
            "mx_verified": val_result.get("mx_verified", "Oui"),
            "reason": val_result.get("reason", ""),
            "source": top_source
        }


email_orchestrator = EmailOrchestrator()
