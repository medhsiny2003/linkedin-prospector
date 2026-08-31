"""
Gestionnaire d'état de session Streamlit et persistance des profils de recherche.
"""

import json
from pathlib import Path
from typing import Any, Dict
import streamlit as st

# Résolution universelle du chemin de stockage des profils et de la configuration active
BASE_DIR = Path(__file__).resolve().parent.parent.parent
PROFILES_PATH = BASE_DIR / "data" / "search_profiles.json"
ACTIVE_CONFIG_PATH = BASE_DIR / "data" / "active_config.json"


def get_active_config() -> Dict[str, Any]:
    """Récupère la configuration active persistée."""
    if ACTIVE_CONFIG_PATH.exists():
        try:
            with open(ACTIVE_CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    
    # Valeurs par défaut si aucun fichier actif
    return {
        "selected_profile": "🇲🇦 Maroc - Aéronautique, Drones & Industrie (Casablanca / Nouaceur / Tanger)",
        "companies": "Airbus Atlantic Maroc, Safran Maroc, Thales Maroc, Hexcel Maroc, Collins Aerospace Maroc, Latecoere Maroc, Daher Maroc, LPFM, Aerotechnic Industries, MAScIR, AIAC, Eaton Maroc",
        "job_titles": "Responsable RH, Recruteur, Talent Acquisition, Ingénieur Aéronautique, Ingénieur Systèmes Embarqués, Chef de projet R&D, Responsable Production",
        "location": "Casablanca, Nouaceur, Tanger, Maroc",
        "max_contacts": 20,
        "enable_mx": True,
        "safe_mode": True
    }


def save_active_config(config_data: Dict[str, Any]) -> None:
    """Persiste la configuration active pour qu'elle soit partagée instantanément entre toutes les pages."""
    ACTIVE_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = get_active_config()
        current.update(config_data)
        with open(ACTIVE_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(current, f, indent=2, ensure_ascii=False)
    except Exception:
        pass


def init_session_state() -> None:
    """Initialise l'ensemble des variables d'état globales Streamlit depuis la configuration persistée."""
    active_cfg = get_active_config()
    
    defaults = {
        "companies": active_cfg.get("companies", ""),
        "job_titles": active_cfg.get("job_titles", ""),
        "location": active_cfg.get("location", "Maroc"),
        "max_contacts": active_cfg.get("max_contacts", 20),
        "enable_mx": active_cfg.get("enable_mx", True),
        "safe_mode": active_cfg.get("safe_mode", True),
        "selected_profile": active_cfg.get("selected_profile", "Personnalisé"),
        "is_running": False,
        "logs_buffer": [],
        "prospecting_progress": 0.0,
        "prospecting_status": "En attente de lancement",
        "active_leads_filter": {},
        "refresh_counter": 0
    }

    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val



def get_saved_profiles() -> Dict[str, Dict[str, Any]]:
    """Charge les profils de recherche sauvegardés depuis le fichier JSON."""
    default_profiles = {
        "🇲🇦 Maroc - Aéronautique, Drones & Industrie (Casablanca / Nouaceur / Tanger)": {
            "companies": "Airbus Atlantic Maroc, Safran Maroc, Thales Maroc, Hexcel Maroc, Collins Aerospace Maroc, Latecoere Maroc, Daher Maroc, LPFM, Aerotechnic Industries, MAScIR, AIAC, Eaton Maroc",
            "job_titles": "Responsable RH, Recruteur, Talent Acquisition, Ingénieur Aéronautique, Ingénieur Systèmes Embarqués, Chef de projet R&D, Responsable Production",
            "location": "Casablanca, Nouaceur, Tanger, Maroc",
            "max_contacts": 20
        },
        "🇲🇦 Maroc - Ingénierie, Tech, IA & ESN (Casablanca / Rabat / Fès)": {
            "companies": "Capgemini Maroc, Alten Maroc, SEGULA Maroc, Expleo Maroc, Atos Maroc, Sopra Steria Maroc, CGI Maroc, DXC Technology Maroc, Intelcia, Concentrix Maroc",
            "job_titles": "Talent Acquisition Specialist, Responsable Recrutement, Lead Tech, Ingénieur Logiciel Embarqué, Data Scientist, Chef de projet IT",
            "location": "Casablanca, Rabat, Fès, Maroc",
            "max_contacts": 20
        },
        "🇲🇦 Maroc - Grands Groupes Nationaux & R&D (OCP, UM6P, Télécoms, Banques)": {
            "companies": "OCP Group, UM6P, MAScIR, Maroc Telecom, Orange Maroc, inwi, ONEE, CDG, Attijariwafa bank, Banque Populaire, Bank of Africa",
            "job_titles": "Responsable Recrutement, HR Business Partner, Directeur R&D, Chef de projet Innovation, Ingénieur Systèmes & Réseaux",
            "location": "Casablanca, Rabat, Benguerir, Maroc",
            "max_contacts": 20
        },
        "🇫🇷 France - Drones & Systèmes Embarqués": {
            "companies": "Thales, Airbus, Safran, Dassault Aviation, MBDA, Naval Group, Parrot, Delair, Elistair, Drone Volt, Hexadrone, SBG Systems, Shark Robotics, Aerix Systems",
            "job_titles": "Responsable RH, Recruteur, Talent Acquisition, Chef de projet Drones, Responsable Systèmes Embarqués, Ingénieur R&D Robotique",
            "location": "France",
            "max_contacts": 15
        },
        "🇫🇷 France - Aéronautique & Défense (Toulouse / Paris)": {
            "companies": "Airbus, Thales, Safran, Dassault Aviation, MBDA, Naval Group, Latecoere, Daher",
            "job_titles": "Responsable Recrutement, Talent Acquisition, Chef de projet, Ingénieur R&D",
            "location": "Toulouse, Paris, France",
            "max_contacts": 20
        },
        "🇫🇷 France - Start-ups Drones & Robotique": {
            "companies": "Delair, Parrot, Elistair, Drone Volt, Hexadrone, Seaber, Shark Robotics, Forssea Robotics, Flying Eye, EOS Technologie",
            "job_titles": "Ingénieur R&D, Responsable Systèmes, CEO, Fondateur, Recruteur",
            "location": "France",
            "max_contacts": 15
        },
        "🌍 International - Drones & Robotique Embarquée": {
            "companies": "TEKEVER, Spin.Works, GhostySky, Connect Robotics, DTM Diversity Technology Minho, Trisolaris Advanced Technologies, Bellator Oss Portugal, Exail Robotics Belgium, ALX Systems, Naval Group Belgium, Safran Aero Boosters",
            "job_titles": "Embedded Software Engineer, Robotics Engineer, Drone Systems Engineer, Computer Vision Engineer, Firmware Engineer, Talent Acquisition, CTO, Lead Embedded Engineer",
            "location": "International",
            "max_contacts": 20
        }
    }

    if not PROFILES_PATH.exists():
        PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(PROFILES_PATH, "w", encoding="utf-8") as f:
                json.dump(default_profiles, f, indent=2, ensure_ascii=False)
        except Exception:
            pass
        return default_profiles

    try:
        with open(PROFILES_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_profiles


def save_profile(name: str, profile_data: Dict[str, Any]) -> bool:
    """Enregistre un nouveau profil de recherche."""
    profiles = get_saved_profiles()
    profiles[name] = profile_data
    try:
        PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PROFILES_PATH, "w", encoding="utf-8") as f:
            json.dump(profiles, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def delete_profile(name: str) -> bool:
    """Supprime un profil de recherche sauvegardé."""
    profiles = get_saved_profiles()
    if name in profiles and name != "Défaut (Drones & Embarqué)":
        del profiles[name]
        try:
            with open(PROFILES_PATH, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
            return True
        except Exception:
            return False
    return False
