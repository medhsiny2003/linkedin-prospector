"""
Parseur DOM et nettoyeur de chaînes de caractères de haute précision.
Normalise les noms, prénoms, intitulés de poste et noms d'entreprises extraits de LinkedIn.
Garantit un filtre anti-bruit et anti-faux profils (rejet des villes, titres et suggestions fantômes).
"""

import re
from typing import Tuple


class DOMParser:
    # Mots géographiques ou pays à rejeter catégoriquement
    GEO_BLACKLIST = {
        "brest", "bretagne", "france", "paris", "toulouse", "bordeaux", "lyon",
        "marseille", "nantes", "rennes", "nice", "strasbourg", "lille", "montpellier",
        "europe", "european", "space", "agency", "lorient", "grenoble", "french",
        # Villes & Régions du Maroc
        "maroc", "morocco", "casablanca", "rabat", "tanger", "tangier", "marrakech",
        "fes", "fès", "agadir", "kenitra", "kénitra", "nouaceur", "oujda", "meknes",
        "meknès", "tetouan", "tétouan", "sale", "salé", "mohammedia", "nador",
        "benguerir", "midparc", "dakhla", "laayoune", "berrechid", "eljadida", "el jadida"
    }

    # Titres ou mots fonctionnels à rejeter s'ils sont parsés comme nom/prénom
    TITLE_BLACKLIST = {
        "president", "président", "directeur", "directrice", "fondateur", "co-fondateur",
        "cofondateur", "implementing", "matching", "program", "programm", "programmeur",
        "msp", "head", "lead", "manager", "recruteur", "consultant", "officer",
        "specialist", "talent", "acquisition", "engineer", "ingenieur", "ingénieur",
        "charge", "chargé", "ressources", "stagiaire", "intern", "apprenant", "alternant",
        "utilisateur", "linkedin", "membre", "member", "compte", "profil", "anonymous", "null"
    }

    # Particules et préfixes patronymiques (Français, Marocains, Arabes et Européens)
    NAME_PARTICLES = {
        "de", "du", "des", "d'", "l'", "van", "von", "saint", "sainte",
        "el", "al", "ben", "ait", "aït", "bou", "bel", "sidi", "moulay", "lalla", "ouled", "ibn"
    }

    # Prénoms composés fréquents (Français & Marocains)
    COMPOUND_FIRST_NAMES_PREFIXES = {
        "jean", "pierre", "marie", "anne", "paul", "marc", "louis", "charles",
        "mohamed", "mohammed", "fatima", "ahmed", "sidi", "moulay", "ali", "reda", "amine"
    }

    @staticmethod
    def clean_text(text: str) -> str:
        """Supprime les espaces multiples, retours à la ligne et caractères indésirables."""
        if not text:
            return ""
        cleaned = re.sub(r'[\r\n\t]+', ' ', text)
        cleaned = re.sub(r'\s{2,}', ' ', cleaned)
        return cleaned.strip()

    @classmethod
    def format_french_name(cls, name_str: str) -> str:
        """Formate correctement les noms et prénoms français et marocains avec gestion des tirets et particules."""
        if not name_str:
            return ""
        # Retrait des chiffres et caractères parasites
        name_str = re.sub(r'[0-9_\(\)\[\]\{\}\<\>\!\?\@\#\$\%\^\&\*\+\=\~\`]', '', name_str).strip()

        # Retrait des suffixes de titre ou bruit résiduel
        name_str = re.sub(r'\b(?:French|Moroccan|Pre|Ph\.d\.|PhD|Msc|MBA|PMP|Msp|Programm)\b', '', name_str, flags=re.IGNORECASE).strip()

        # Traitement des tirets (ex: Jean-Marc, Fatima-Zahra)
        hyphen_parts = name_str.split('-')
        capitalized_hyphens = []
        for hp in hyphen_parts:
            # Traitement des espaces (ex: de la roche, el amrani, ben jelloun)
            space_parts = hp.split()
            cap_spaces = []
            for sp in space_parts:
                sp_lower = sp.lower().strip()
                if not sp_lower:
                    continue
                if sp_lower in ['de', 'du', 'des', "d'", "l'"]:
                    cap_spaces.append(sp_lower)
                elif sp_lower in ['el', 'al', 'ben', 'ait', 'aït', 'bou', 'bel']:
                    cap_spaces.append(sp_lower.capitalize())
                elif sp_lower.startswith("d'") or sp_lower.startswith("l'"):
                    prefix = sp_lower[:2]
                    rest = sp[2:].capitalize()
                    cap_spaces.append(f"{prefix}{rest}")
                elif sp_lower.startswith("el-") or sp_lower.startswith("al-"):
                    prefix = sp_lower[:3].capitalize()
                    rest = sp[3:].capitalize()
                    cap_spaces.append(f"{prefix}{rest}")
                else:
                    cap_spaces.append(sp.capitalize())
            if cap_spaces:
                capitalized_hyphens.append(" ".join(cap_spaces))

        return "-".join(capitalized_hyphens).strip()

    @classmethod
    def parse_full_name(cls, full_name_raw: str) -> Tuple[str, str]:
        """
        Découpe un nom complet en (Prénom, Nom) avec élimination stricte des faux profils
        et des chaînes polluées par les sous-titres, niveaux de connexion ou termes géographiques.
        """
        if not full_name_raw:
            return "", ""

        # 1. Traitement prioritaire de la première ligne
        lines = [l.strip() for l in full_name_raw.splitlines() if l.strip()]
        candidate = lines[0] if lines else full_name_raw

        # 2. Retrait des mentions de degrés de réseau (3e et +, 3e, 2e, 1er, 3rd, 2nd, 1st)
        candidate = re.sub(r'\b(?:•|\-)?\s*(?:1er|2e|3e(?:\s*et\s*\+)?|3e\+|1st|2nd|3rd(?:\s*and\s*\+)?|3rd\+)\b.*$', '', candidate, flags=re.IGNORECASE)

        # 3. Retrait des boutons d'actions LinkedIn collés au nom
        candidate = re.sub(r'\b(?:Se connecter|Voir le profil|Suivre|Message|Envoyer un message|Connect|Follow)\b.*$', '', candidate, flags=re.IGNORECASE)

        # 4. Retrait des fonctions professionnelles et diplômes collés par erreur
        candidate = re.sub(r'\b(?:chez|at|Responsable|Directeur|Directrice|Manager|Ingénieur|Recruteur|HR|RH|Lead|Specialist|Consultant|Head|Officer|Talent|President|CEO|CTO|COO|Founder|Co-founder|Matching|Director)\b.*$', '', candidate, flags=re.IGNORECASE)
        candidate = re.sub(r',\s*(?:PhD|Ph\.d\.|MSc|MBA|PMP|Ingénieur|Ing\.|Dr\.)\b.*$', '', candidate, flags=re.IGNORECASE)
        candidate = re.sub(r'^(?:Dr\.|Dr|Ing\.|Ing|Prof\.|Prof|Mr\.|Mr|Mme\.|Mme|Mlle\.|Mlle)\s+', '', candidate, flags=re.IGNORECASE)

        # 5. Nettoyage des caractères non-alphabétiques (en préservant tirets, apostrophes et accents)
        candidate = re.sub(r'[^\w\s\-\'\.]', '', candidate)
        cleaned = cls.clean_text(candidate)

        parts = [p.strip() for p in cleaned.split() if p.strip()]
        if not parts:
            return "", ""

        # 6. Filtrage anti-bruit sur le premier mot
        first_name_raw = parts[0]
        if first_name_raw.lower() in cls.TITLE_BLACKLIST or first_name_raw.lower() in cls.GEO_BLACKLIST:
            return "", ""

        if len(parts) == 1:
            fn = cls.format_french_name(first_name_raw)
            return (fn, "") if len(fn) >= 2 else ("", "")

        # 7. Gestion des prénoms composés (ex: Mohamed Amine, Fatima Zahra, Jean Marc)
        first_name_idx = 1
        if len(parts) >= 3 and parts[0].lower() in cls.COMPOUND_FIRST_NAMES_PREFIXES and parts[1].lower() not in cls.NAME_PARTICLES:
            first_name_raw = f"{parts[0]} {parts[1]}"
            first_name_idx = 2

        # 8. Limitation intelligente du nom de famille (particules et noms composés)
        remaining_parts = parts[first_name_idx:]
        if not remaining_parts:
            remaining_parts = parts[1:]
            first_name_raw = parts[0]

        if len(remaining_parts) > 1 and remaining_parts[0].lower() in cls.NAME_PARTICLES:
            last_name_parts = remaining_parts[:3]
        else:
            last_name_parts = remaining_parts[:2]
        
        # Vérification si un des mots du nom est dans la blacklist
        for lp in last_name_parts:
            if lp.lower() in cls.TITLE_BLACKLIST or lp.lower() in cls.GEO_BLACKLIST:
                return "", ""

        last_name_raw = " ".join(last_name_parts)

        fn = cls.format_french_name(first_name_raw)
        ln = cls.format_french_name(last_name_raw)

        # 9. Vérification de cohérence (longueur minimale)
        if len(fn) < 2 or len(ln) < 2:
            return "", ""

        return fn, ln

    @classmethod
    def clean_job_and_company(cls, subtitle_raw: str) -> Tuple[str, str]:
        """
        Extrait proprement le poste et l'entreprise depuis un sous-titre.
        """
        cleaned = cls.clean_text(subtitle_raw)

        # Nettoyage des degrés
        cleaned = re.sub(r'\b(?:1er|2e|3e(?:\s*et\s*\+)?|3e\+|1st|2nd|3rd\+)\b', '', cleaned, flags=re.IGNORECASE)

        # Cas 'chez', 'at', '@'
        match = re.search(r'^(.*?)\s+(?:chez|at|@)\s+(.*?)$', cleaned, flags=re.IGNORECASE)
        if match:
            job = match.group(1).strip()
            company = match.group(2).strip()
            return job, company

        # Cas avec séparateur '|' ou '-'
        if " | " in cleaned:
            parts = cleaned.split(" | ")
            return parts[0].strip(), parts[1].strip()

        return cleaned, ""


dom_parser = DOMParser()
