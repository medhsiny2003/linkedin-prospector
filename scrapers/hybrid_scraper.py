"""
Scraper Hybride Avancé : Combine l'automatisation Microsoft Edge et le serveur MCP.
Orchestre l'extraction, l'enrichissement par l'Orchestrateur 5 Couches et la persistance SQLite.
Prend en charge le contrôle d'exécution en direct (Pause, Reprise, Arrêt d'urgence).
"""

import asyncio
import os
import re
import sys
from typing import Callable, List, Optional
from config import config
from core.auth.auth_manager import auth_manager
from core.browser.stealth_browser import stealth_browser
from scrapers.mcp_client import mcp_client
from core.monitoring.audit_logger import audit_logger
from core.security.rate_limiter import rate_limiter
from scrapers.linkedin_browser import linkedin_browser_scraper
from storage.db_manager import db_manager
from storage.exporter import excel_exporter


class HybridScraper:
    def __init__(self):
        self.use_mcp_only = config.USE_MCP_SERVER

    async def run_prospecting_pipeline(
        self,
        companies: Optional[List[str]] = None,
        job_titles: Optional[List[str]] = None,
        location: str = "France",
        max_profiles_per_search: int = 10,
        progress_callback: Optional[Callable[[float, str, Optional[dict]], None]] = None,
        stop_check: Optional[Callable[[], bool]] = None,
        pause_check: Optional[Callable[[], bool]] = None
    ) -> int:
        """
        Exécute le pipeline complet de prospection avec support du contrôle d'exécution en direct.
        """
        def report(pct: float, msg: str, lead: Optional[dict] = None):
            if progress_callback:
                progress_callback(pct, msg, lead)

        target_companies = companies or config.TARGET_COMPANIES
        target_titles = job_titles or config.TARGET_JOB_TITLES

        audit_logger.log_event(
            "PIPELINE_START",
            f"Démarrage du pipeline hybride pour {len(target_companies)} entreprises et {len(target_titles)} postes."
        )

        # 0. Rotation automatique : archivage de la session précédente vers contacts_historique.xlsx
        excel_exporter.archive_current_session_file()

        # 1. Mode MCP exclusif (si activé)
        if self.use_mcp_only:
            audit_logger.log_event("PIPELINE_MCP", "Utilisation exclusive du serveur MCP configuré.")
            report(0.10, "Connexion au serveur MCP LinkedIn...")
            total_mcp_leads = 0
            for comp in target_companies:
                if stop_check and stop_check():
                    break
                for title in target_titles:
                    if stop_check and stop_check():
                        break
                    profiles = await mcp_client.search_profiles(title, company=comp, location=location)
                    for prof in profiles:
                        saved = self._enrich_and_save_profile(prof, comp, title)
                        if saved:
                            total_mcp_leads += 1
                            report(0.5, f"Lead MCP extrait : {prof.get('first_name')} ({comp})", prof)
            excel_exporter.export_from_db()
            return total_mcp_leads

        # 2. Gestion du moteur d'exécution (Browser ou LinkedinSpider Direct)
        exec_mode = os.getenv("EXECUTION_MODE", "cloud" if sys.platform != "win32" else "local").lower()
        report(0.10, f"Démarrage du moteur en mode {exec_mode.upper()}...")
        context = None
        page = None
        is_auth = False

        if exec_mode != "cloud":
            try:
                context, page = await stealth_browser.launch()
            except Exception as e:
                audit_logger.log_event("BROWSER_WARN", f"Navigateur indisponible, basculement sur LinkedinSpider : {str(e)}")
                context = None
                page = None
        else:
            audit_logger.log_event("MODE_CLOUD_DIRECT", "Mode Cloud actif : Agent-Reach MCP + LinkedinSpider sans navigateur.")
            report(0.15, "🌐 Mode Cloud Activé : Agent-Reach MCP + LinkedinSpider 24/7...")

        total_saved_leads = 0

        try:
            # 3. Stratégie d'authentification selon le mode
            if exec_mode == "cloud":
                # En Cloud (GitHub Actions Ubuntu), X-Ray OSINT sans session est le moteur principal
                audit_logger.log_event("MODE_CLOUD_INIT", "Mode Cloud actif (Linux Ubuntu) : Moteur X-Ray OSINT sans session.")
                report(0.18, "🌐 Mode Cloud Activé : Prospection OSINT via Google & Bing...")
                is_auth = False
            else:
                # En Local (Windows), authentification Playwright Edge avec profil persistant
                def auth_status_cb(msg: str):
                    report(0.15, msg)

                is_auth = await auth_manager.authenticate(context, page, status_callback=auth_status_cb)
                if not is_auth:
                    audit_logger.log_event("XRAY_MODE_FALLBACK", "Session locale non active. Basculement sur X-Ray OSINT.")
                    report(0.18, "🌐 Mode X-Ray Activé : Prospection OSINT via Google & Bing...")
                else:
                    report(0.20, "Simulation de navigation naturelle sur LinkedIn...")
                    await linkedin_browser_scraper.perform_decoy_activity(page)

                # CRITICAL: Transmettre l'état d'authentification au scraper navigateur
                linkedin_browser_scraper.is_authenticated = is_auth

            if stop_check and stop_check():
                report(0.20, "🛑 Prospection interrompue par l'utilisateur.")
                return 0

            # 5. Parcours des cibles
            total_combinations = max(len(target_companies) * len(target_titles), 1)
            comb_idx = 0
            seen_in_session = set()
            session_leads_list = []

            # Charger les contacts déjà connus pour ne chercher que des NOUVEAUX
            existing_leads = db_manager.get_all_leads()
            known_urls = set()
            known_names = set()
            for el in existing_leads:
                if el.get("profile_url"):
                    known_urls.add(el["profile_url"].rstrip("/").lower())
                fn_k = (el.get("first_name", "").strip().lower(), el.get("last_name", "").strip().lower(), el.get("company", "").strip().lower())
                if fn_k[0] and fn_k[1]:
                    known_names.add(fn_k)
            audit_logger.log_event("DEDUP_INIT", f"{len(known_urls)} profils déjà connus chargés — seuls les NOUVEAUX contacts seront ajoutés.")

            for comp_idx, company in enumerate(target_companies):
                if stop_check and stop_check():
                    report(0.5, "🛑 Arrêt demandé par l'utilisateur.")
                    break

                for title_idx, title in enumerate(target_titles):
                    # Gestion de l'arrêt
                    if stop_check and stop_check():
                        report(0.5, "🛑 Arrêt demandé par l'utilisateur.")
                        break

                    # Gestion de la pause
                    while pause_check and pause_check():
                        if stop_check and stop_check():
                            break
                        report(current_pct if 'current_pct' in locals() else 0.25, "⏸️ Prospection en pause... Cliquez sur 'Reprendre' pour continuer.")
                        await asyncio.sleep(0.8)

                    if stop_check and stop_check():
                        break

                    comb_idx += 1
                    current_pct = 0.25 + (0.70 * (comb_idx / total_combinations))
                    
                    report(
                        current_pct,
                        f"Recherche en cours : {company} — '{title}' ({comb_idx}/{total_combinations})..."
                    )
                    audit_logger.log_event("SEARCH_TARGET", f"Prospection : {company} - {title}")
                    
                    # Vérification du Cache TTL 7 jours (réduction de 50-70% des requêtes répétées)
                    from core.cache.cache_manager import cache_manager
                    cached_profiles = cache_manager.get(company, title, location)
                    if cached_profiles:
                        profiles = cached_profiles
                    else:
                        profiles = await linkedin_browser_scraper.search_and_scrape(
                            page=page,
                            company=company,
                            keywords=title,
                            location=location,
                            max_profiles=max_profiles_per_search,
                            stop_check=stop_check
                        )
                        if profiles:
                            cache_manager.set(company, title, location, profiles)

                    # Filtrage sémantique intelligent par IA (Gemini Flash / Fallback sémantique)
                    from enricher.ai_filter import ai_filter
                    filtered_profiles = ai_filter.filter_profiles_batch(
                        profiles,
                        target_keywords=[title],
                        target_location=location,
                        min_score=3
                    )

                    for raw_profile in filtered_profiles:
                        if stop_check and stop_check():
                            break

                        fn = raw_profile.get("first_name", "").strip()
                        ln = raw_profile.get("last_name", "").strip()
                        lead_key = f"{fn.lower()}_{ln.lower()}_{company.lower()}"

                        # Déduplication en direct : ignorer les personnes déjà traitées dans cette session
                        if lead_key in seen_in_session:
                            continue

                        # Ignorer les contacts DÉJÀ CONNUS en base (session précédente)
                        profile_url = raw_profile.get("profile_url", "").rstrip("/").lower()
                        name_key = (fn.lower(), ln.lower(), company.lower())
                        if profile_url and profile_url in known_urls:
                            continue
                        if name_key in known_names:
                            continue

                        seen_in_session.add(lead_key)

                        lead_info = self._enrich_and_save_profile(raw_profile, company, title)
                        if lead_info:
                            total_saved_leads += 1
                            session_leads_list.append(lead_info)
                            # Écriture immédiate sur disque pour chaque contact trouvé (résistance coupure)
                            try:
                                excel_exporter.export_leads(session_leads_list)
                            except Exception:
                                pass

                            report(
                                current_pct,
                                f"Contact qualifié : {lead_info.get('first_name')} {lead_info.get('last_name')} ({company}) — {lead_info.get('proposed_email')}",
                                lead_info
                            )

                    # Délais humains fluides entre cibles avec surveillance d'arrêt
                    for _ in range(3):
                        if stop_check and stop_check():
                            break
                        await asyncio.sleep(0.5)

                    await rate_limiter.check_and_apply_batch_pause()

        finally:
            if context:
                await stealth_browser.close()

        # 6. Génération finale du rapport Excel
        report(0.98, "Génération et mise à jour du fichier Excel...")
        excel_path = excel_exporter.export_leads(session_leads_list)
        audit_logger.log_event(
            "PIPELINE_COMPLETE",
            f"Pipeline terminé. {total_saved_leads} nouveaux leads enrichis.",
            {"excel_path": str(excel_path)}
        )
        report(1.0, f"Prospection terminée ! {total_saved_leads} contact(s) qualifié(s).")
        return total_saved_leads

    def _enrich_and_save_profile(self, profile: dict, company: str, keywords: str) -> Optional[dict]:
        """Enrichit un profil via l'Orchestrateur 5 Couches (Base interne, Permutations déterministes, MX)."""
        first_name = profile.get("first_name", "")
        last_name = profile.get("last_name", "")
        target_company = profile.get("company") or company

        from enricher.email_orchestrator import email_orchestrator
        res = email_orchestrator.discover_and_validate(first_name, last_name, target_company, fast_mode=True)

        lead_data = {
            "first_name": first_name,
            "last_name": last_name,
            "job_title": profile.get("job_title", ""),
            "company": target_company,
            "profile_url": profile.get("profile_url", ""),
            "proposed_email": res.get("proposed_email", ""),
            "alt_email_1": res.get("alt_email_1", ""),
            "alt_email_2": res.get("alt_email_2", ""),
            "confidence_score": res.get("confidence_score", 0),
            "status": res.get("status", "À vérifier"),
            "mx_verified": res.get("mx_verified", "Non"),
            "matched_keywords": profile.get("matched_keywords") or f"{company}, {keywords}"
        }

        saved = db_manager.save_lead(lead_data)
        return lead_data if saved else None


hybrid_scraper = HybridScraper()
