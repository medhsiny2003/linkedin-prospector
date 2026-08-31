"""
Résolveur Intelligent de Métadonnées d'Entreprises (Slugs LinkedIn & Noms de Domaine avec Live MX Probing).
Identifie automatiquement les vrais domaines certifiés (.ai, .io, .aero, .tech, .fr, .com)
en sondant les serveurs DNS MX en temps réel et en rejetant strictement le Null MX (RFC 7505).
"""

import re
from typing import Dict, List, Optional, Tuple

try:
    import dns.resolver
    HAS_DNSPYTHON = True
except ImportError:
    HAS_DNSPYTHON = False


class CompanyResolver:
    def __init__(self):
        # Cache mémoire pour éviter les requêtes DNS répétées
        self._domain_cache: Dict[str, str] = {}

        # Registre des entreprises cibles certifiées du secteur Drones, Défense, Aéronautique, Robotique & IA
        self.registry: Dict[str, Dict[str, str]] = {
            "thales": {
                "name": "Thales",
                "slug": "thales",
                "domain": "thalesgroup.com",
                "pattern": "{first}.{last}@thalesgroup.com"
            },
            "airbus": {
                "name": "Airbus",
                "slug": "airbus",
                "domain": "airbus.com",
                "pattern": "{first}.{last}@airbus.com"
            },
            "safran": {
                "name": "Safran",
                "slug": "safran",
                "domain": "safrangroup.com",
                "pattern": "{first}.{last}@safrangroup.com"
            },
            "safran maroc": {
                "name": "Safran Maroc",
                "slug": "safran",
                "domain": "safrangroup.com",
                "pattern": "{first}.{last}@safrangroup.com"
            },
            "dassault": {
                "name": "Dassault Aviation",
                "slug": "dassault-aviation",
                "domain": "dassault-aviation.com",
                "pattern": "{first}.{last}@dassault-aviation.com"
            },
            "dassault aviation": {
                "name": "Dassault Aviation",
                "slug": "dassault-aviation",
                "domain": "dassault-aviation.com",
                "pattern": "{first}.{last}@dassault-aviation.com"
            },
            # --- ENTREPRISES & MULTINATIONALES AU MAROC (AÉRONAUTIQUE, TECH, ÉNERGIE, BANQUES) ---
            "ocp maintenance solutions": {
                "name": "OCP Maintenance Solutions",
                "slug": "ocp-maintenance-solutions",
                "domain": "ocpgroup.ma",
                "pattern": "{first}.{last}@ocpgroup.ma"
            },
            "ocp ms": {
                "name": "OCP Maintenance Solutions",
                "slug": "ocp-maintenance-solutions",
                "domain": "ocpgroup.ma",
                "pattern": "{first}.{last}@ocpgroup.ma"
            },
            "ocp solutions": {
                "name": "OCP Solutions",
                "slug": "ocp-solutions",
                "domain": "ocpgroup.ma",
                "pattern": "{first}.{last}@ocpgroup.ma"
            },
            "cegelec maroc": {
                "name": "Cegelec Maroc",
                "slug": "cegelec-maroc",
                "domain": "cegelec.com",
                "pattern": "{first}.{last}@cegelec.com"
            },
            "vinci energies maroc": {
                "name": "VINCI Energies Maroc",
                "slug": "vinci-energies-maroc",
                "domain": "vinci-energies.com",
                "pattern": "{first}.{last}@vinci-energies.com"
            },
            "artis facilities": {
                "name": "ARTIS FACILITIES",
                "slug": "artis-facilities",
                "domain": "artisfacilities.com",
                "pattern": "{first}.{last}@artisfacilities.com"
            },
            "artis facilities maroc": {
                "name": "ARTIS FACILITIES Maroc",
                "slug": "artis-facilities",
                "domain": "artisfacilities.com",
                "pattern": "{first}.{last}@artisfacilities.com"
            },
            "ocp": {
                "name": "OCP Group",
                "slug": "ocp-group",
                "domain": "ocpgroup.ma",
                "pattern": "{first}.{last}@ocpgroup.ma"
            },
            "ocp group": {
                "name": "OCP Group",
                "slug": "ocp-group",
                "domain": "ocpgroup.ma",
                "pattern": "{first}.{last}@ocpgroup.ma"
            },
            "um6p": {
                "name": "UM6P - Université Mohammed VI Polytechnique",
                "slug": "um6p",
                "domain": "um6p.ma",
                "pattern": "{first}.{last}@um6p.ma"
            },
            "mascir": {
                "name": "MAScIR",
                "slug": "mascir",
                "domain": "mascir.com",
                "pattern": "{first}.{last}@mascir.com"
            },
            "maroc telecom": {
                "name": "Maroc Telecom",
                "slug": "maroctelecom",
                "domain": "iam.ma",
                "pattern": "{first}.{last}@iam.ma"
            },
            "iam": {
                "name": "Maroc Telecom",
                "slug": "maroctelecom",
                "domain": "iam.ma",
                "pattern": "{first}.{last}@iam.ma"
            },
            "orange maroc": {
                "name": "Orange Maroc",
                "slug": "orange-maroc",
                "domain": "orange.ma",
                "pattern": "{first}.{last}@orange.ma"
            },
            "inwi": {
                "name": "inwi",
                "slug": "inwi",
                "domain": "inwi.ma",
                "pattern": "{first}.{last}@inwi.ma"
            },
            "onee": {
                "name": "ONEE",
                "slug": "onee",
                "domain": "onee.ma",
                "pattern": "{first}.{last}@onee.ma"
            },
            "attijariwafa bank": {
                "name": "Attijariwafa bank",
                "slug": "attijariwafa-bank",
                "domain": "attijariwafa.com",
                "pattern": "{first}.{last}@attijariwafa.com"
            },
            "attijariwafa": {
                "name": "Attijariwafa bank",
                "slug": "attijariwafa-bank",
                "domain": "attijariwafa.com",
                "pattern": "{first}.{last}@attijariwafa.com"
            },
            "banque populaire": {
                "name": "Groupe Banque Populaire (BCP)",
                "slug": "groupe-banque-populaire",
                "domain": "groupebcp.com",
                "pattern": "{first}.{last}@groupebcp.com"
            },
            "bcp": {
                "name": "Groupe Banque Populaire (BCP)",
                "slug": "groupe-banque-populaire",
                "domain": "groupebcp.com",
                "pattern": "{first}.{last}@groupebcp.com"
            },
            "bank of africa": {
                "name": "Bank of Africa (BMCE Group)",
                "slug": "bank-of-africa-bmce-group",
                "domain": "bankofafrica.ma",
                "pattern": "{first}.{last}@bankofafrica.ma"
            },
            "bmce": {
                "name": "Bank of Africa (BMCE Group)",
                "slug": "bank-of-africa-bmce-group",
                "domain": "bankofafrica.ma",
                "pattern": "{first}.{last}@bankofafrica.ma"
            },
            "alten maroc": {
                "name": "Alten Maroc",
                "slug": "alten-maroc",
                "domain": "alten.com",
                "pattern": "{first}.{last}@alten.com"
            },
            "capgemini maroc": {
                "name": "Capgemini Maroc",
                "slug": "capgemini",
                "domain": "capgemini.com",
                "pattern": "{first}.{last}@capgemini.com"
            },
            "capgemini engineering maroc": {
                "name": "Capgemini Engineering Maroc",
                "slug": "capgemini-engineering",
                "domain": "capgemini.com",
                "pattern": "{first}.{last}@capgemini.com"
            },
            "segula maroc": {
                "name": "SEGULA Technologies Maroc",
                "slug": "segula-technologies",
                "domain": "segulagrp.com",
                "pattern": "{first}.{last}@segulagrp.com"
            },
            "expleo maroc": {
                "name": "Expleo Maroc",
                "slug": "expleo-group",
                "domain": "expleogroup.com",
                "pattern": "{first}.{last}@expleogroup.com"
            },
            "atos maroc": {
                "name": "Atos Maroc",
                "slug": "atos",
                "domain": "atos.net",
                "pattern": "{first}.{last}@atos.net"
            },
            "sopra steria maroc": {
                "name": "Sopra Steria Maroc",
                "slug": "soprasteria",
                "domain": "soprasteria.com",
                "pattern": "{first}.{last}@soprasteria.com"
            },
            "cgi maroc": {
                "name": "CGI Maroc",
                "slug": "cgi",
                "domain": "cgi.com",
                "pattern": "{first}.{last}@cgi.com"
            },
            "dxc technology maroc": {
                "name": "DXC Technology Maroc",
                "slug": "dxc-technology",
                "domain": "dxc.com",
                "pattern": "{first}.{last}@dxc.com"
            },
            "dxc maroc": {
                "name": "DXC Technology Maroc",
                "slug": "dxc-technology",
                "domain": "dxc.com",
                "pattern": "{first}.{last}@dxc.com"
            },
            "intelcia": {
                "name": "Intelcia Group",
                "slug": "intelcia-group",
                "domain": "intelcia.com",
                "pattern": "{first}.{last}@intelcia.com"
            },
            "concentrix maroc": {
                "name": "Concentrix Maroc",
                "slug": "concentrix",
                "domain": "concentrix.com",
                "pattern": "{first}.{last}@concentrix.com"
            },
            "airbus atlantic maroc": {
                "name": "Airbus Atlantic Maroc",
                "slug": "airbus-atlantic",
                "domain": "airbus.com",
                "pattern": "{first}.{last}@airbus.com"
            },
            "stelia aerospace maroc": {
                "name": "Stelia Aerospace Maroc",
                "slug": "stelia-aerospace",
                "domain": "stelia-aerospace.com",
                "pattern": "{first}.{last}@stelia-aerospace.com"
            },
            "thales maroc": {
                "name": "Thales Maroc",
                "slug": "thales",
                "domain": "thalesgroup.com",
                "pattern": "{first}.{last}@thalesgroup.com"
            },
            "hexcel maroc": {
                "name": "Hexcel Maroc",
                "slug": "hexcel-corporation",
                "domain": "hexcel.com",
                "pattern": "{first}.{last}@hexcel.com"
            },
            "collins aerospace maroc": {
                "name": "Collins Aerospace Maroc",
                "slug": "collins-aerospace",
                "domain": "collins.com",
                "pattern": "{first}.{last}@collins.com"
            },
            "latecoere maroc": {
                "name": "Latecoere Maroc",
                "slug": "latecoere",
                "domain": "latecoere.com",
                "pattern": "{first}.{last}@latecoere.com"
            },
            "daher maroc": {
                "name": "Daher Maroc",
                "slug": "daher",
                "domain": "daher.com",
                "pattern": "{first}.{last}@daher.com"
            },
            "lpfm": {
                "name": "Le Piston Français Maroc (LPFM)",
                "slug": "groupe-lpf",
                "domain": "groupe-lpf.com",
                "pattern": "{first}.{last}@groupe-lpf.com"
            },
            "le piston francais maroc": {
                "name": "Le Piston Français Maroc (LPFM)",
                "slug": "groupe-lpf",
                "domain": "groupe-lpf.com",
                "pattern": "{first}.{last}@groupe-lpf.com"
            },
            "aerotechnic industries": {
                "name": "Aerotechnic Industries (ATI)",
                "slug": "aerotechnic-industries",
                "domain": "aerotechnicindustries.com",
                "pattern": "{first}.{last}@aerotechnicindustries.com"
            },
            "nexans maroc": {
                "name": "Nexans Maroc",
                "slug": "nexans",
                "domain": "nexans.com",
                "pattern": "{first}.{last}@nexans.com"
            },
            "eaton maroc": {
                "name": "Eaton Maroc",
                "slug": "eaton",
                "domain": "eaton.com",
                "pattern": "{first}.{last}@eaton.com"
            },
            "cdg": {
                "name": "Caisse de Dépôt et de Gestion (CDG)",
                "slug": "groupe-cdg",
                "domain": "cdg.ma",
                "pattern": "{first}.{last}@cdg.ma"
            },
            "renault maroc": {
                "name": "Renault Group Maroc",
                "slug": "renault-group",
                "domain": "renault.com",
                "pattern": "{first}.{last}@renault.com"
            },
            "stellantis maroc": {
                "name": "Stellantis Maroc",
                "slug": "stellantis",
                "domain": "stellantis.com",
                "pattern": "{first}.{last}@stellantis.com"
            },
            "valeo maroc": {
                "name": "Valeo Maroc",
                "slug": "valeo",
                "domain": "valeo.com",
                "pattern": "{first}.{last}@valeo.com"
            },
            "snop maroc": {
                "name": "Snop Maroc",
                "slug": "snop",
                "domain": "snop.eu",
                "pattern": "{first}.{last}@snop.eu"
            },
            "lear maroc": {
                "name": "Lear Corporation Maroc",
                "slug": "lear-corporation",
                "domain": "lear.com",
                "pattern": "{first}.{last}@lear.com"
            },
            "aptiv maroc": {
                "name": "Aptiv Maroc",
                "slug": "aptiv",
                "domain": "aptiv.com",
                "pattern": "{first}.{last}@aptiv.com"
            },
            "yazaki maroc": {
                "name": "Yazaki Maroc",
                "slug": "yazaki-europe-ltd",
                "domain": "yazaki-europe.com",
                "pattern": "{first}.{last}@yazaki-europe.com"
            },
            "leoni maroc": {
                "name": "Leoni Maroc",
                "slug": "leoni",
                "domain": "leoni.com",
                "pattern": "{first}.{last}@leoni.com"
            },
            "alstom maroc": {
                "name": "Alstom Maroc",
                "slug": "alstom",
                "domain": "alstomgroup.com",
                "pattern": "{first}.{last}@alstomgroup.com"
            },
            "totalenergies maroc": {
                "name": "TotalEnergies Marketing Maroc",
                "slug": "totalenergies",
                "domain": "totalenergies.com",
                "pattern": "{first}.{last}@totalenergies.com"
            },
            "siemens maroc": {
                "name": "Siemens Maroc",
                "slug": "siemens",
                "domain": "siemens.com",
                "pattern": "{first}.{last}@siemens.com"
            },
            "schneider electric maroc": {
                "name": "Schneider Electric Maroc",
                "slug": "schneider-electric",
                "domain": "se.com",
                "pattern": "{first}.{last}@se.com"
            },
            "aiac": {
                "name": "Académie Internationale Mohammed VI de l'Aviation Civile",
                "slug": "aiac-officiel",
                "domain": "aiac.ma",
                "pattern": "{first}.{last}@aiac.ma"
            },
            "mbda": {
                "name": "MBDA",
                "slug": "mbda",
                "domain": "mbda-systems.com",
                "pattern": "{first}.{last}@mbda-systems.com"
            },
            "naval group": {
                "name": "Naval Group",
                "slug": "naval-group",
                "domain": "naval-group.com",
                "pattern": "{first}.{last}@naval-group.com"
            },
            "parrot": {
                "name": "Parrot",
                "slug": "parrot",
                "domain": "parrot.com",
                "pattern": "{first}.{last}@parrot.com"
            },
            "delair": {
                "name": "Delair",
                "slug": "delair",
                "domain": "delair.aero",
                "pattern": "{first}.{last}@delair.aero"
            },
            "elistair": {
                "name": "Elistair",
                "slug": "elistair",
                "domain": "elistair.com",
                "pattern": "{first}.{last}@elistair.com"
            },
            "drone volt": {
                "name": "Drone Volt",
                "slug": "drone-volt",
                "domain": "dronevolt.com",
                "pattern": "{first}.{last}@dronevolt.com"
            },
            "harmattan ai": {
                "name": "Harmattan AI",
                "slug": "harmattan-ai",
                "domain": "harmattan.ai",
                "pattern": "{first}.{last}@harmattan.ai"
            },
            "harmattan": {
                "name": "Harmattan AI",
                "slug": "harmattan-ai",
                "domain": "harmattan.ai",
                "pattern": "{first}.{last}@harmattan.ai"
            },
            "hexadrone": {
                "name": "Hexadrone",
                "slug": "hexadrone",
                "domain": "hexadrone.fr",
                "pattern": "{first}.{last}@hexadrone.fr"
            },
            "sbg systems": {
                "name": "SBG Systems",
                "slug": "sbg-systems",
                "domain": "sbg-systems.com",
                "pattern": "{first}.{last}@sbg-systems.com"
            },
            "sbg-systems": {
                "name": "SBG Systems",
                "slug": "sbg-systems",
                "domain": "sbg-systems.com",
                "pattern": "{first}.{last}@sbg-systems.com"
            },
            "seaber": {
                "name": "Seaber",
                "slug": "seaber",
                "domain": "seaber.fr",
                "pattern": "{first}.{last}@seaber.fr"
            },
            "shark robotics": {
                "name": "Shark Robotics",
                "slug": "shark-robotics",
                "domain": "shark-robotics.fr",
                "pattern": "{first}.{last}@shark-robotics.fr"
            },
            "aerix systems": {
                "name": "Aerix Systems",
                "slug": "aerix-systems",
                "domain": "aerix-systems.com",
                "pattern": "{first}.{last}@aerix-systems.com"
            },
            "forssea robotics": {
                "name": "Forssea Robotics",
                "slug": "forssea-robotics",
                "domain": "forssea-robotics.com",
                "pattern": "{first}.{last}@forssea-robotics.com"
            },
            "forssea": {
                "name": "Forssea Robotics",
                "slug": "forssea-robotics",
                "domain": "forssea-robotics.com",
                "pattern": "{first}.{last}@forssea-robotics.com"
            },
            "flying eye": {
                "name": "Flying Eye",
                "slug": "flying-eye",
                "domain": "flyingeye.fr",
                "pattern": "{first}.{last}@flyingeye.fr"
            },
            "diodon drone technology": {
                "name": "Diodon Drone Technology",
                "slug": "diodon-drone-technology",
                "domain": "diodon-drone.com",
                "pattern": "{first}.{last}@diodon-drone.com"
            },
            "diodon drone": {
                "name": "Diodon Drone Technology",
                "slug": "diodon-drone-technology",
                "domain": "diodon-drone.com",
                "pattern": "{first}.{last}@diodon-drone.com"
            },
            "sherpa engineering": {
                "name": "Sherpa Engineering",
                "slug": "sherpa-engineering",
                "domain": "sherpa-eng.com",
                "pattern": "{first}.{last}@sherpa-eng.com"
            },
            "eos technologie": {
                "name": "EOS Technologie",
                "slug": "eos-technologie",
                "domain": "eostechnologie.com",
                "pattern": "{first}.{last}@eostechnologie.com"
            },
            "mc2 technologies": {
                "name": "MC2 Technologies",
                "slug": "mc2-technologies",
                "domain": "mc2-technologies.com",
                "pattern": "{first}.{last}@mc2-technologies.com"
            },
            "rtsys": {
                "name": "RTSYS",
                "slug": "rtsys",
                "domain": "rtsys.eu",
                "pattern": "{first}.{last}@rtsys.eu"
            },
            "skydrone robotics": {
                "name": "Skydrone Robotics",
                "slug": "skydrone-robotics",
                "domain": "skydrone.fr",
                "pattern": "{first}.{last}@skydrone.fr"
            },
            "skydrone": {
                "name": "Skydrone Robotics",
                "slug": "skydrone-robotics",
                "domain": "skydrone.fr",
                "pattern": "{first}.{last}@skydrone.fr"
            },
            "alseamar": {
                "name": "Alseamar",
                "slug": "alseamar",
                "domain": "alseamar-alcen.com",
                "pattern": "{first}.{last}@alseamar-alcen.com"
            },
            "novadem": {
                "name": "Novadem",
                "slug": "novadem",
                "domain": "novadem.com",
                "pattern": "{first}.{last}@novadem.com"
            },
            "atechsys": {
                "name": "Atechsys",
                "slug": "atechsys",
                "domain": "atechsys.fr",
                "pattern": "{first}.{last}@atechsys.fr"
            },
            "cerbair": {
                "name": "CerbAir",
                "slug": "cerbair",
                "domain": "cerbair.com",
                "pattern": "{first}.{last}@cerbair.com"
            },
            "m3 systems": {
                "name": "M3 Systems",
                "slug": "m3-systems",
                "domain": "m3systems.eu",
                "pattern": "{first}.{last}@m3systems.eu"
            },
            "exail technologies": {
                "name": "Exail Technologies",
                "slug": "exail-technologies",
                "domain": "exail.com",
                "pattern": "{first}.{last}@exail.com"
            },
            "exail": {
                "name": "Exail Technologies",
                "slug": "exail-technologies",
                "domain": "exail.com",
                "pattern": "{first}.{last}@exail.com"
            },
            "survey copter": {
                "name": "Survey Copter",
                "slug": "survey-copter",
                "domain": "survey-copter.com",
                "pattern": "{first}.{last}@survey-copter.com"
            },
            "mistral ai": {
                "name": "Mistral AI",
                "slug": "mistral-ai",
                "domain": "mistral.ai",
                "pattern": "{first}.{last}@mistral.ai"
            },
            "mistral": {
                "name": "Mistral AI",
                "slug": "mistral-ai",
                "domain": "mistral.ai",
                "pattern": "{first}.{last}@mistral.ai"
            }
        }

    def probe_domain_candidates(self, company_name: str) -> str:
        """
        Génère les candidats TLD (.ai, .io, .aero, .tech, .fr, .com) et sélectionne
        en direct le premier domaine dont les serveurs MX DNS répondent avec succès,
        en rejetant formellement les enregistrements Null MX (RFC 7505).
        """
        clean = re.sub(r'[^\w\s\-]', '', company_name).lower().strip()
        words = clean.split()
        if not words:
            return "entreprise.com"

        if clean in self._domain_cache:
            return self._domain_cache[clean]

        candidates: List[str] = []

        # 1. Startups & Entreprises IA (ex: Harmattan AI -> harmattan.ai)
        if 'ai' in words or clean.endswith(' ai') or 'ia' in words:
            brand = re.sub(r'\b(ai|ia)\b', '', clean).strip()
            brand_slug = re.sub(r'[^a-z0-9]+', '', brand)
            if brand_slug:
                candidates.append(f"{brand_slug}.ai")
                candidates.append(f"{brand_slug}.fr")
                candidates.append(f"{brand_slug}.com")
                candidates.append(f"{brand_slug}.io")
                candidates.append(f"{brand_slug}ai.com")
                candidates.append(f"{brand_slug}-ai.com")

        # 2. Startups Drones / Aéro / Tech / Robotique (ex: Delair -> delair.aero, Shark Robotics -> shark-robotics.fr)
        if any(k in clean for k in ['tech', 'drone', 'robot', 'aero', 'defense', 'space']):
            brand = re.sub(r'\b(technologies|technology|tech|robotics|robots|robot|drones|drone|aero|defense|systems|group|sas|sa)\b', '', clean).strip()
            brand_slug = re.sub(r'[^a-z0-9]+', '', brand)
            if brand_slug:
                candidates.append(f"{brand_slug}.fr")
                candidates.append(f"{brand_slug}.aero")
                candidates.append(f"{brand_slug}.tech")
                candidates.append(f"{brand_slug}.com")
                candidates.append(f"{brand_slug}.io")

        # 3. Candidats standards et variantes avec tirets (France, Maroc, International)
        slug_simple = re.sub(r'[^a-z0-9]+', '', clean)
        slug_hyphen = re.sub(r'[^a-z0-9]+', '-', clean).strip('-')

        candidates.append(f"{slug_simple}.ma")
        candidates.append(f"{slug_simple}.fr")
        candidates.append(f"{slug_hyphen}.com")
        candidates.append(f"{slug_hyphen}.ma")
        candidates.append(f"{slug_hyphen}.fr")
        candidates.append(f"{slug_simple}.com")
        candidates.append(f"{slug_simple}-maroc.com")
        candidates.append(f"{slug_simple}.co.ma")
        candidates.append(f"{slug_simple}.io")
        candidates.append(f"{slug_simple}.ai")

        # Déduplication en conservant l'ordre de priorité
        unique_candidates = list(dict.fromkeys(candidates))

        # Sondage DNS MX en direct avec rejet strict du Null MX (RFC 7505)
        if HAS_DNSPYTHON:
            for cand in unique_candidates:
                try:
                    answers = dns.resolver.resolve(cand, 'MX', lifetime=1.5)
                    # Rejet strict du Null MX (ex: '.' ou vide)
                    has_valid_mx = False
                    for r in answers:
                        mx_host = str(r.exchange).rstrip('.').strip()
                        if mx_host and mx_host != '.':
                            has_valid_mx = True
                            break
                    if has_valid_mx:
                        self._domain_cache[clean] = cand
                        return cand
                except Exception:
                    continue

        fallback = f"{slug_simple}.com"
        self._domain_cache[clean] = fallback
        return fallback

    def resolve(self, company_name: str) -> Tuple[str, str, str]:
        """
        Retourne (nom_officiel, linkedin_slug, domain).
        Préserve le nom exact de l'entreprise cible sans écrasement par la maison mère.
        """
        if not company_name:
            return "", "", "gmail.com"

        normalized = company_name.strip().lower()

        # 1. Recherche exacte dans le registre
        if normalized in self.registry:
            entry = self.registry[normalized]
            return entry["name"], entry["slug"], entry["domain"]

        # 2. Recherche par correspondance de clés les plus longues d'abord (Longest Match First)
        sorted_keys = sorted(self.registry.keys(), key=len, reverse=True)
        for key in sorted_keys:
            if key == normalized:
                entry = self.registry[key]
                return entry["name"], entry["slug"], entry["domain"]
            elif len(key) >= 4 and (f" {key} " in f" {normalized} " or normalized.startswith(key)):
                entry = self.registry[key]
                official_name = company_name.strip() if len(company_name.strip()) > len(entry["name"]) else entry["name"]
                return official_name, entry["slug"], entry["domain"]

        # 3. Résolution dynamique via Sondage DNS MX en direct (Anti-Null MX)
        slug = re.sub(r'[^a-z0-9]+', '-', normalized).strip('-')
        verified_domain = self.probe_domain_candidates(company_name)

        return company_name.strip(), slug, verified_domain


company_resolver = CompanyResolver()
