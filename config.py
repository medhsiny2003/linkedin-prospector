"""
Configuration centrale pour l'Assistant de Prospection LinkedIn (V3.1).
Gère le chargement des variables d'environnement, les règles anti-détection,
les dictionnaires de domaines connus et les patterns d'emails.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field
    HAS_PYDANTIC_SETTINGS = True
except ImportError:
    HAS_PYDANTIC_SETTINGS = False
    from pydantic import BaseModel as BaseSettings, Field
    SettingsConfigDict = dict


class AppConfig(BaseSettings):
    if HAS_PYDANTIC_SETTINGS:
        model_config = SettingsConfigDict(
            env_file=str(BASE_DIR / ".env"),
            env_file_encoding="utf-8",
            extra="ignore"
        )

    # --- Authentification LinkedIn ---
    LINKEDIN_COOKIE: Optional[str] = Field(default_factory=lambda: os.getenv("LINKEDIN_COOKIE"))
    LINKEDIN_EMAIL: Optional[str] = Field(default_factory=lambda: os.getenv("LINKEDIN_EMAIL"))
    LINKEDIN_PASSWORD: Optional[str] = Field(default_factory=lambda: os.getenv("LINKEDIN_PASSWORD"))

    # --- Proxy Résidentiel ---
    PROXY_URL: Optional[str] = Field(default_factory=lambda: os.getenv("PROXY_URL"))

    # --- Intégration MCP & IA Gemini ---
    USE_MCP_SERVER: bool = Field(
        default_factory=lambda: os.getenv("USE_MCP_SERVER", "false").lower() in ("true", "1", "yes")
    )
    MCP_SERVER_URL: str = Field(
        default_factory=lambda: os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
    )
    GOOGLE_API_KEY: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))
    AI_FILTER_ENABLED: bool = Field(
        default_factory=lambda: os.getenv("AI_FILTER_ENABLED", "true").lower() in ("true", "1", "yes")
    )

    # --- Moteur de Warm-Up & Plages Horaires ---
    # --- Cibles et Filtres par Défaut ---
    TARGET_COMPANIES: List[str] = [
        "Thales", "Airbus", "Safran", "Dassault Aviation", "Delair", "Parrot", "Survey Copter", "Seaber", "Eos Technologie", "Diodon Drone Technology"
    ]
    TARGET_JOB_TITLES: List[str] = [
        "Ingénieur GNC", "Ingénieur Systèmes Embarqués", "Ingénieur Drones", "Ingénieur Électronique", "Talent Acquisition", "Responsable RH"
    ]
    TARGET_LOCATIONS: List[str] = ["France", "Maroc"]
    DEFAULT_COMPANIES: List[str] = [
        "Thales", "Airbus", "Safran", "Dassault Aviation", "Delair", "Parrot", "Survey Copter", "Seaber", "Eos Technologie", "Diodon Drone Technology"
    ]
    DEFAULT_JOB_TITLES: List[str] = [
        "Ingénieur GNC", "Ingénieur Systèmes Embarqués", "Ingénieur Drones", "Ingénieur Électronique", "Talent Acquisition", "Responsable RH"
    ]
    DEFAULT_LOCATIONS: List[str] = ["France", "Maroc"]
    MAX_PROFILES_PER_SEARCH: int = 15

    WARMUP_DAYS: int = 14
    WARMUP_START_LIMIT: int = 2
    WARMUP_END_LIMIT: int = 18
    WARMUP_HOURS_START: int = 0    # 00h00 (Prospection 24/7)
    WARMUP_HOURS_END: int = 24      # 24h00 (Prospection 24/7)
    RESTRICT_WORKING_HOURS: bool = False # Désactivé pour fonctionnement 24/7
    RESTRICT_WEEKENDS: bool = False      # Autorisé tous les jours

    # --- Rate Limiting & Sécurité Réaliste ---
    # Limite journalière stricte (20 invitations max)
    DAILY_CONNECT_LIMIT: int = Field(default_factory=lambda: int(os.getenv("DAILY_CONNECT_LIMIT", "20")))
    
    # Délais aléatoires entre chaque requête (en secondes)
    REQUEST_DELAY_MIN: float = Field(default_factory=lambda: float(os.getenv("REQUEST_DELAY_MIN", "2.0")))
    REQUEST_DELAY_MAX: float = Field(default_factory=lambda: float(os.getenv("REQUEST_DELAY_MAX", "6.0")))

    # Pauses naturelles entre lots de requêtes (secondes)
    ACTION_BATCH_SIZE_MIN: int = 15
    ACTION_BATCH_SIZE_MAX: int = 30
    LONG_PAUSE_MIN_SECONDS: int = 5    # Pause douce de 5 à 15 secondes
    LONG_PAUSE_MAX_SECONDS: int = 15

    # --- Navigateur (Microsoft Edge / Chromium) ---
    BROWSER_CHANNEL: str = Field(default_factory=lambda: os.getenv("BROWSER_CHANNEL", "msedge"))
    HEADLESS: bool = Field(
        default_factory=lambda: os.getenv("HEADLESS", "true" if sys.platform != "win32" else "false").lower() in ("true", "1", "yes")
    )
    VIEWPORT_WIDTH: int = 1920
    VIEWPORT_HEIGHT: int = 1080
    TIMEZONE: str = "Europe/Paris"
    LOCALE: str = "fr-FR"
    USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0"
    )

    # --- Chemins de stockage ---
    SESSION_PATH: Path = Field(default_factory=lambda: BASE_DIR / "data" / "sessions" / "linkedin_profile")
    DATABASE_PATH: Path = Field(default_factory=lambda: BASE_DIR / "data" / "leads.db")
    OUTPUT_EXCEL_PATH: Path = Field(default_factory=lambda: BASE_DIR / "data" / "contacts_stage.xlsx")
    EXPORTS_DIR: Path = Field(default_factory=lambda: BASE_DIR / "data" / "exports")
    AUDIT_LOG_PATH: Path = Field(default_factory=lambda: BASE_DIR / "logs" / "audit.json")

    # --- Recherche par Défaut (Drones & Systèmes Embarqués en France) ---
    DEFAULT_COMPANIES: List[str] = [
        "Thales",
        "Airbus",
        "Safran",
        "Dassault Aviation",
        "MBDA",
        "Naval Group",
        "Parrot",
        "Delair",
        "Elistair",
        "Drone Volt"
    ]
    DEFAULT_JOB_TITLES: List[str] = [
        "Responsable RH",
        "Recruteur",
        "Talent Acquisition",
        "Chef de projet Drones",
        "Responsable Systèmes Embarqués",
        "Ingénieur R&D Robotique"
    ]
    DEFAULT_LOCATION: str = "France"

    # --- Domaines Entreprises Françaises (Mapping de Résolution) ---
    KNOWN_COMPANY_DOMAINS: Dict[str, str] = {
        "thales": "thalesgroup.com",
        "thales group": "thalesgroup.com",
        "airbus": "airbus.com",
        "airbus defence and space": "airbus.com",
        "airbus helicopters": "airbus.com",
        "safran": "safrangroup.com",
        "safran group": "safrangroup.com",
        "safran electronics & defense": "safrangroup.com",
        "safran maroc": "safrangroup.com",
        "dassault aviation": "dassault-aviation.com",
        "dassault systemes": "3ds.com",
        "ocp": "ocpgroup.ma",
        "ocp group": "ocpgroup.ma",
        "um6p": "um6p.ma",
        "mascir": "mascir.com",
        "maroc telecom": "iam.ma",
        "iam": "iam.ma",
        "orange maroc": "orange.ma",
        "inwi": "inwi.ma",
        "onee": "onee.ma",
        "attijariwafa": "attijariwafa.com",
        "attijariwafa bank": "attijariwafa.com",
        "banque populaire": "groupebcp.com",
        "bcp": "groupebcp.com",
        "bank of africa": "bankofafrica.ma",
        "bmce": "bankofafrica.ma",
        "alten maroc": "alten.com",
        "capgemini maroc": "capgemini.com",
        "segula maroc": "segulagrp.com",
        "expleo maroc": "expleogroup.com",
        "atos maroc": "atos.net",
        "sopra steria maroc": "soprasteria.com",
        "cgi maroc": "cgi.com",
        "dxc maroc": "dxc.com",
        "intelcia": "intelcia.com",
        "concentrix maroc": "concentrix.com",
        "airbus atlantic maroc": "airbus.com",
        "stelia aerospace maroc": "stelia-aerospace.com",
        "thales maroc": "thalesgroup.com",
        "hexcel maroc": "hexcel.com",
        "collins aerospace maroc": "collins.com",
        "latecoere maroc": "latecoere.com",
        "daher maroc": "daher.com",
        "lpfm": "groupe-lpf.com",
        "aerotechnic industries": "aerotechnicindustries.com",
        "nexans maroc": "nexans.com",
        "eaton maroc": "eaton.com",
        "cdg": "cdg.ma",
        "renault maroc": "renault.com",
        "stellantis maroc": "stellantis.com",
        "valeo maroc": "valeo.com",
        "snop maroc": "snop.eu",
        "lear maroc": "lear.com",
        "aptiv maroc": "aptiv.com",
        "yazaki maroc": "yazaki-europe.com",
        "leoni maroc": "leoni.com",
        "alstom maroc": "alstomgroup.com",
        "totalenergies maroc": "totalenergies.com",
        "siemens maroc": "siemens.com",
        "schneider electric maroc": "se.com",
        "aiac": "aiac.ma",
        "mbda": "mbda-systems.com",
        "mbda missile systems": "mbda-systems.com",
        "naval group": "naval-group.com",
        "parrot": "parrot.com",
        "delair": "delair.aero",
        "elistair": "elistair.com",
        "drone volt": "dronevolt.com",
        "harmattan ai": "harmattan.ai",
        "harmattan": "harmattan.ai",
        "hexadrone": "hexadrone.fr",
        "sbg systems": "sbg-systems.com",
        "sbg-systems": "sbg-systems.com",
        "seaber": "seaber.fr",
        "shark robotics": "shark-robotics.fr",
        "aerix systems": "aerix-systems.com",
        "forssea robotics": "forssea-robotics.com",
        "forssea": "forssea-robotics.com",
        "flying eye": "flyingeye.fr",
        "diodon drone technology": "diodon-drone.com",
        "diodon drone": "diodon-drone.com",
        "sherpa engineering": "sherpa-eng.com",
        "eos technologie": "eostechnologie.com",
        "mc2 technologies": "mc2-technologies.com",
        "rtsys": "rtsys.eu",
        "skydrone robotics": "skydrone.fr",
        "skydrone": "skydrone.fr",
        "alseamar": "alseamar-alcen.com",
        "novadem": "novadem.com",
        "atechsys": "atechsys.fr",
        "cerbair": "cerbair.com",
        "m3 systems": "m3systems.eu",
        "exail technologies": "exail.com",
        "exail": "exail.com",
        "survey copter": "survey-copter.com",
        "mistral ai": "mistral.ai",
        "expleo": "expleogroup.com",
        "capgemini": "capgemini.com",
        "altran": "capgemini.com",
        "alten": "alten.com",
        "akka technologies": "adecco.com",
        "segula technologies": "segulagrp.com",
        "bertin technologies": "bertin-technologies.com",
        "steria": "soprasteria.com",
        "sopra steria": "soprasteria.com",
        "cnes": "cnes.fr",
        "onera": "onera.fr",
        "cea": "cea.fr",
        "inria": "inria.fr"
    }

    # --- Patterns d'Emails Déterministes (22 Patterns Exhaustifs) ---
    EMAIL_PATTERNS: List[Dict[str, Any]] = [
        {"id": "p1", "priority": 1, "pattern": "{first}.{last}@{domain}", "confidence": 95, "desc": "prenom.nom@domaine.com (Standard)"},
        {"id": "p2", "priority": 2, "pattern": "{f}{last}@{domain}", "confidence": 90, "desc": "pnom@domaine.com (Grands Groupes / Thales)"},
        {"id": "p3", "priority": 3, "pattern": "{first}{last}@{domain}", "confidence": 88, "desc": "prenomnom@domaine.com"},
        {"id": "p4", "priority": 4, "pattern": "{f}.{last}@{domain}", "confidence": 85, "desc": "p.nom@domaine.com (Aéronautique / Safran)"},
        {"id": "p5", "priority": 5, "pattern": "{first}_{last}@{domain}", "confidence": 80, "desc": "prenom_nom@domaine.com"},
        {"id": "p6", "priority": 6, "pattern": "{first}-{last}@{domain}", "confidence": 78, "desc": "prenom-nom@domaine.com"},
        {"id": "p7", "priority": 7, "pattern": "{last}.{first}@{domain}", "confidence": 75, "desc": "nom.prenom@domaine.com"},
        {"id": "p8", "priority": 8, "pattern": "{last}{first}@{domain}", "confidence": 70, "desc": "nomprenom@domaine.com"},
        {"id": "p9", "priority": 9, "pattern": "{first}@{domain}", "confidence": 68, "desc": "prenom@domaine.com (Startups / Dirigeants)"},
        {"id": "p10", "priority": 10, "pattern": "{last}@{domain}", "confidence": 65, "desc": "nom@domaine.com"},
        {"id": "p11", "priority": 11, "pattern": "{first}.{l}@{domain}", "confidence": 62, "desc": "prenom.n@domaine.com"},
        {"id": "p12", "priority": 12, "pattern": "{first}{l}@{domain}", "confidence": 60, "desc": "prenomn@domaine.com"},
        {"id": "p13", "priority": 13, "pattern": "{f}_{last}@{domain}", "confidence": 58, "desc": "p_nom@domaine.com"},
        {"id": "p14", "priority": 14, "pattern": "{f}-{last}@{domain}", "confidence": 55, "desc": "p-nom@domaine.com"},
        {"id": "p15", "priority": 15, "pattern": "{last}.{f}@{domain}", "confidence": 52, "desc": "nom.p@domaine.com"},
        {"id": "p16", "priority": 16, "pattern": "{last}_{first}@{domain}", "confidence": 50, "desc": "nom_prenom@domaine.com"},
        {"id": "p17", "priority": 17, "pattern": "{last}-{first}@{domain}", "confidence": 48, "desc": "nom-prenom@domaine.com"},
        {"id": "p18", "priority": 18, "pattern": "{f}{l}@{domain}", "confidence": 45, "desc": "pn@domaine.com"},
        {"id": "p19", "priority": 19, "pattern": "{compound_init}.{last}@{domain}", "confidence": 42, "desc": "jm.dupont@domaine.com (Prénoms Composés)"},
        {"id": "p20", "priority": 20, "pattern": "{compound_init}{last}@{domain}", "confidence": 40, "desc": "jmdupont@domaine.com (Prénoms Composés)"},
        {"id": "p21", "priority": 21, "pattern": "{first_part}.{last}@{domain}", "confidence": 38, "desc": "jean.dupont@ (Premier prénom seul)"},
        {"id": "p22", "priority": 22, "pattern": "{first}{last}1@{domain}", "confidence": 35, "desc": "prenomnom1@domaine.com (Homonymes)"}
    ]


config = AppConfig()
