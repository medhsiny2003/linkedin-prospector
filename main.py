"""
Point d'entrée principal (CLI) pour l'Assistant de Prospection LinkedIn (V3.1).
Fournit une interface console interactive et des arguments en ligne de commande.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Configuration de l'encodage console Windows pour éviter UnicodeEncodeError sur les emojis
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from config import config
from core.monitoring.audit_logger import audit_logger
from core.monitoring.health_check import health_checker
from core.security.warmup_engine import warmup_engine
from scrapers.hybrid_scraper import hybrid_scraper
from storage.db_manager import db_manager
from storage.exporter import excel_exporter

BANNER = r"""
========================================================================================
   ___  ___ _____ ___  ___ ___  ___ ___  ___ _____ ___  ___ 
  | _ \/ _ \_   _/ _ \| _ ) _ \/ _ / __|/ _ \_   _/ _ \| _ \
  |  _/ (_) || || (_) | _ \   / (_) \__ \  _/ | || (_) |   /
  |_|  \___/ |_| \___/|___/_|_\\___/|___/_|   |_| \___/|_|_\
  --------------------------------------------------------------------------------------
  [*] Assistant de Prospection LinkedIn V3.1 - Stages Drones & Systemes Embarques (France)
========================================================================================
  [!] AVERTISSEMENT DE SECURITE (RECOMMANDATION CRITIQUE) :
  * Utilisez imperativement un COMPTE LINKEDIN DEDIE (secondaire).
  * Ne lancez jamais d'automatisation agressive sur votre profil personnel principal.
  * Le taux de restriction LinkedIn est eleve (~40% en 2026 en cas de comportement anormal).
  * Limite maximale configuree : 20 invitations/jour (Warm-up 14 jours actif).
========================================================================================
"""


def print_banner():
    print(BANNER)


def show_config_summary():
    """Affiche un résumé de la configuration courante."""
    start_date = db_manager.get_or_create_campaign_start_date()
    daily_limit = warmup_engine.calculate_daily_limit(start_date)
    stats = db_manager.get_stats()

    print("\n--- [i] ETAT DU SYSTEME & CONFIGURATION ---")
    print(f"* Mode Navigateur      : Visible (Headless={config.HEADLESS})")
    print(f"* Quota journalier     : {daily_limit} max (Campagne démarree le {start_date})")
    print(f"* Proxy Residentiel    : {'Active (' + config.PROXY_URL + ')' if config.PROXY_URL else 'Desactive (Connexion directe)'}")
    print(f"* Serveur MCP          : {'Active (' + config.MCP_SERVER_URL + ')' if config.USE_MCP_SERVER else 'Desactive'}")
    print(f"* Base de donnees      : {config.DATABASE_PATH} ({stats['total_leads']} contacts stockes)")
    print(f"* Validation Emails    : Syntaxe RFC + Enregistrements MX DNS (Sans SMTP)")
    print("------------------------------------------\n")


async def run_prospecting_interactive():
    """Menu interactif pour personnaliser la recherche avant lancement."""
    print("\n[1] Lancement avec la configuration par defaut (Drones & Systemes Embarques France)")
    print("[2] Personnaliser les entreprises et mots-cles")
    choice = input("Votre choix (1/2) [defaut: 1] : ").strip()

    companies = config.DEFAULT_COMPANIES
    titles = config.DEFAULT_JOB_TITLES
    location = config.DEFAULT_LOCATION

    if choice == "2":
        comp_input = input(f"Entreprises separees par des virgules [defaut: {', '.join(companies[:4])}...] : ").strip()
        if comp_input:
            companies = [c.strip() for c in comp_input.split(",") if c.strip()]

        titles_input = input(f"Postes cibles separes par des virgules [defaut: {', '.join(titles[:3])}...] : ").strip()
        if titles_input:
            titles = [t.strip() for t in titles_input.split(",") if t.strip()]

        loc_input = input(f"Localisation [defaut: {location}] : ").strip()
        if loc_input:
            location = loc_input

    print(f"\n[*] Demarrage du pipeline pour :")
    print(f"   * Entreprises : {', '.join(companies)}")
    print(f"   * Postes      : {', '.join(titles)}")
    print(f"   * Lieu        : {location}")
    print("   Appuyez sur Ctrl+C a tout moment pour arreter en securite.\n")

    await hybrid_scraper.run_prospecting_pipeline(
        companies=companies,
        job_titles=titles,
        location=location
    )


def run_health_check():
    """Affiche le bilan de santé du système."""
    print("\n[+] Execution des Health Checks...")
    report = health_checker.run_all_checks()
    for check_name, res in report.items():
        if isinstance(res, dict):
            status_icon = "[OK]" if res.get("status") == "OK" else ("[INFO]" if res.get("status") == "INFO" else "[ERR]")
            print(f"  {status_icon:<7} {check_name.upper():<18} : {res.get('details')}")
    print(f"\nResultat global : {'[OK] SYSTEME PRET' if report['overall_health'] == 'HEALTHY' else '[WARN] ATTENTION REQUISE'}\n")


def verify_audit_logs():
    """Contrôle l'intégrité de la chaîne cryptographique."""
    print("\n[*] Verification de l'integrite du journal d'audit (Tamper-Evident SHA-256)...")
    valid = audit_logger.verify_integrity()
    if valid:
        print("[OK] SUCCES : La chaine de hachage SHA-256 est 100% integre. Aucun journal altere.")
    else:
        print("[ERR] ALERTE : Rupture de chaine detectee ! Le fichier audit.json a ete modifie.")


async def main_menu():
    """Boucle principale du menu CLI."""
    while True:
        print_banner()
        show_config_summary()
        print("Menu Principal :")
        print("  1. Lancer la recherche et prospection de contacts")
        print("  2. Exporter la base SQLite vers Excel (contacts_stage.xlsx)")
        print("  3. Executer le diagnostic de sante (Health Check)")
        print("  4. Verifier l'integrite des logs d'audit (SHA-256)")
        print("  5. Quitter")
        
        choice = input("\nChoisissez une option (1-5) : ").strip()
        if choice == "1":
            await run_prospecting_interactive()
        elif choice == "2":
            excel_path = excel_exporter.export_from_db()
            print(f"\n[OK] Export Excel termine : {excel_path}\n")
        elif choice == "3":
            run_health_check()
        elif choice == "4":
            verify_audit_logs()
        elif choice == "5":
            print("\nFermeture de l'assistant de prospection. Bonnes recherches de stage !\n")
            break
        else:
            print("\n[!] Option invalide, veuillez reessayer.")

        input("\nAppuyez sur Entree pour revenir au menu...")


def parse_arguments():
    parser = argparse.ArgumentParser(description="Assistant de Prospection LinkedIn (V3.1)")
    parser.add_argument("--run", action="store_true", help="Execute directement la prospection sans menu")
    parser.add_argument("--export", action="store_true", help="Genere l'export Excel depuis la base de donnees")
    parser.add_argument("--check", action="store_true", help="Lance les verifications d'etat (Health Checks)")
    parser.add_argument("--verify-audit", action="store_true", help="Verifie la chaine cryptographique des logs")
    parser.add_argument("--companies", type=str, help="Liste d'entreprises separees par virgules")
    parser.add_argument("--titles", type=str, help="Liste de postes separes par virgules")
    parser.add_argument("--location", type=str, default="France", help="Localisation geographique")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    if args.check:
        run_health_check()
    elif args.verify_audit:
        verify_audit_logs()
    elif args.export:
        p = excel_exporter.export_from_db()
        print(f"[OK] Export genere : {p}")
    elif args.run:
        comps = [c.strip() for c in args.companies.split(",")] if args.companies else None
        titles = [t.strip() for t in args.titles.split(",")] if args.titles else None
        asyncio.run(hybrid_scraper.run_prospecting_pipeline(companies=comps, job_titles=titles, location=args.location))
    else:
        try:
            asyncio.run(main_menu())
        except KeyboardInterrupt:
            print("\n\n[!] Arret utilisateur detecte. Fermeture securisee.")
            sys.exit(0)
