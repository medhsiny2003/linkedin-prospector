"""
Execute le pipeline de prospection en mode Cloud Autonome (GitHub Actions / Serveur 24/7).
Tourne entierement en arriere-plan, enrichit les contacts et met a jour le fichier Excel.
"""

import asyncio
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
APP_DIR = PROJECT_ROOT / "app"

for p in [str(PROJECT_ROOT), str(APP_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from config import config
from storage.db_manager import db_manager
from storage.exporter import excel_exporter
from scrapers.hybrid_scraper import hybrid_scraper
from app.utils.state_manager import get_active_config, get_saved_profiles


async def main():
    print("==================================================================")
    print("      LINKEDIN PROSPECTOR V3.1 - MOTEUR CLOUD AUTONOME 24/7       ")
    print("==================================================================")
    
    # 1. Initialisation de la base SQLite
    db_manager.init_db()
    
    # 2. Chargement de la configuration active ou du profil cible demandé
    saved_profiles = get_saved_profiles()
    requested_profile = os.getenv("TARGET_PROFILE", "").strip() or (sys.argv[1] if len(sys.argv) > 1 else "")
    
    if requested_profile and requested_profile in saved_profiles:
        print(f"[*] Utilisation du profil sélectionné : {requested_profile}")
        cfg = saved_profiles[requested_profile]
    else:
        # Recherche par mot-clé dans les profils sauvegardés (ex: 'Ingénierie', 'Tech', 'Aéronautique')
        matched = next((p for name, p in saved_profiles.items() if requested_profile and requested_profile.lower() in name.lower()), None)
        if matched:
            print(f"[*] Profil sélectionné par correspondance : {requested_profile}")
            cfg = matched
        else:
            cfg = get_active_config()
    
    raw_companies = cfg.get("companies") or getattr(config, "TARGET_COMPANIES", ["Capgemini Maroc", "Alten Maroc", "SEGULA Maroc", "Thales", "Safran", "Airbus"])
    if isinstance(raw_companies, str):
        companies = [c.strip() for c in raw_companies.split(",") if c.strip()]
    else:
        companies = list(raw_companies)

    raw_titles = cfg.get("job_titles") or getattr(config, "TARGET_JOB_TITLES", ["Responsable Recrutement", "Talent Acquisition", "Ingénieur", "Lead Tech"])
    if isinstance(raw_titles, str):
        job_titles = [t.strip() for t in raw_titles.split(",") if t.strip()]
    else:
        job_titles = list(raw_titles)

    location = str(cfg.get("location", "Maroc") or "Maroc")
    max_per_search = int(cfg.get("max_contacts", cfg.get("max_profiles", 20)) or 20)
    
    print(f"\n[*] Cibles : {len(companies)} entreprises, {len(job_titles)} postes ciblés.")
    print(f"[*] Zone géographique : {location}")
    print(f"[*] Limite par recherche : {max_per_search} profils\n")
    
    # 3. Callback d'avancement avec synchronisation Cloud incrémentale
    found_in_cloud = 0
    def progress_callback(pct, msg, lead_data=None):
        nonlocal found_in_cloud
        pct_int = int(pct * 100)
        lead_info = f" -> Nouveau contact : {lead_data.get('first_name')} {lead_data.get('last_name')} ({lead_data.get('company')})" if lead_data else ""
        print(f"[{pct_int}%] {msg}{lead_info}")
        
        if lead_data:
            found_in_cloud += 1
            # Synchronisation automatique vers Streamlit Cloud tous les 5 contacts
            if found_in_cloud % 5 == 0:
                os.system('git config user.name "Prospector Bot" && git config user.email "bot@local" && git add data/ 2>/dev/null && git commit -m "chore(auto): synchronisation 5 nouveaux leads [skip ci]" 2>/dev/null && git push origin main 2>/dev/null || true')
    
    # 4. Lancement du scraping et enrichissement
    try:
        total_found = await hybrid_scraper.run_prospecting_pipeline(
            companies=companies,
            job_titles=job_titles,
            location=location,
            max_profiles_per_search=max_per_search,
            progress_callback=progress_callback
        )
        print(f"\n[SUCCESS] Prospection Cloud terminée avec succès ! {total_found} contacts qualifiés.")
    except Exception as e:
        print(f"\n[ERROR] Erreur durant la prospection Cloud : {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Exportation du fichier Excel final
    excel_path = excel_exporter.export_from_db()
    print(f"[EXPORT] Fichier Excel généré : {excel_path}")


if __name__ == "__main__":
    asyncio.run(main())