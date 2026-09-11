"""
Générateur d'adresses emails basé sur 11 patterns et scoring probabiliste.
Inclut la normalisation des noms français (accents, traits d'union) et
la résolution automatique des domaines d'entreprises cibles (drones / aéronautique / robotique).
"""

import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from config import config


class EmailGenerator:
    def __init__(self):
        self.known_domains = config.KNOWN_COMPANY_DOMAINS
        self.patterns = config.EMAIL_PATTERNS

    @staticmethod
    def strip_accents(text: str) -> str:
        """Supprime les accents et caractères diacritiques (ex: 'Éléonore' -> 'Eleonore')."""
        nfkd_form = unicodedata.normalize('NFKD', text)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    @classmethod
    def clean_name_part(cls, name_part: str) -> str:
        """Nettoie et normalise un élément de nom (retrait des titres, caractères spéciaux)."""
        cleaned = cls.strip_accents(name_part).lower().strip()
        # Suppression des titres et civilités
        cleaned = re.sub(r'^(dr|ing|mr|mme|mlle|prof|phd|msc)\.?\s+', '', cleaned)
        # Ne garder que les caractères alphabétiques
        cleaned = re.sub(r'[^a-z0-9\-]', '', cleaned)
        return cleaned

    def resolve_domain(self, company_name: str) -> str:
        """
        Détermine le nom de domaine internet le plus probable pour une entreprise donnée.
        Vérifie d'abord le catalogue des domaines d'entreprises françaises connues.
        """
        clean_company = self.strip_accents(company_name).lower().strip()
        # Retrait des formes juridiques et suffixes courants
        clean_company_simple = re.sub(r'\b(sas|sa|sarl|group|groupe|france|defense|aerospace|robotics)\b', '', clean_company).strip()

        from enricher.company_resolver import company_resolver
        _, _, domain = company_resolver.resolve(company_name)
        if domain and domain != "gmail.com":
            return domain

        # 1. Correspondance directe dans le dictionnaire des entreprises connues
        for key, dom in self.known_domains.items():
            if key in clean_company or clean_company in key or (clean_company_simple and key in clean_company_simple):
                return dom

        # 2. Heuristique de génération de domaine par défaut
        # Remplace les espaces par rien ou tiret
        slug = re.sub(r'[^a-z0-9]', '', clean_company_simple or clean_company)
        if not slug:
            slug = "entreprise"
        return f"{slug}.com"

    def generate_candidates(
        self,
        first_name: str,
        last_name: str,
        company_name: str
    ) -> List[Dict[str, any]]:
        """
        Génère les 11 déclinaisons d'emails classées par priorité et score de confiance.
        """
        f_clean = self.clean_name_part(first_name)
        l_clean = self.clean_name_part(last_name)
        domain = self.resolve_domain(company_name)

        if not f_clean or not l_clean:
            return []

        f_single = f_clean.replace('-', '').replace(' ', '')
        l_single = l_clean.replace('-', '').replace(' ', '')

        f_initial = f_clean[0]
        l_initial = l_clean[0]

        # Variantes composées (ex: Jean-Marc -> jm, jean)
        f_parts = [p for p in re.split(r'[\s\-]+', f_clean) if p]
        compound_init = "".join([p[0] for p in f_parts]) if f_parts else f_initial
        first_part = f_parts[0] if f_parts else f_single

        candidates = []
        for p in self.patterns:
            template = p["pattern"]
            email_str = template.format(
                first=f_single,
                last=l_single,
                f=f_initial,
                l=l_initial,
                compound_init=compound_init,
                first_part=first_part,
                domain=domain,
                num="1"
            )
            candidates.append({
                "email": email_str,
                "confidence": p["confidence"],
                "priority": p.get("priority", 1),
                "pattern": template,
                "domain": domain
            })

        return candidates

    def get_top_propositions(
        self,
        first_name: str,
        last_name: str,
        company_name: str
    ) -> Dict[str, any]:
        """
        Retourne l'email principal (Top 1) et deux alternatives (Top 2 et Top 3).
        """
        candidates = self.generate_candidates(first_name, last_name, company_name)
        if not candidates:
            return {
                "proposed_email": "",
                "alt_email_1": "",
                "alt_email_2": "",
                "confidence_score": 0,
                "domain": ""
            }

        return {
            "proposed_email": candidates[0]["email"],
            "alt_email_1": candidates[1]["email"] if len(candidates) > 1 else "",
            "alt_email_2": candidates[2]["email"] if len(candidates) > 2 else "",
            "confidence_score": candidates[0]["confidence"],
            "domain": candidates[0]["domain"]
        }


email_generator = EmailGenerator()
