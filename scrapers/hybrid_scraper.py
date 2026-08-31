"""
Scraper Hybride Avancé : Combine l'automatisation Microsoft Edge et le serveur MCP.
Orchestre l'extraction, l'enrichissement par l'Orchestrateur 5 Couches et la persistance SQLite.
Prend en charge le contrôle d'exécution en direct (Pause, Reprise, Arrêt d'urgence).
"""

import asyncio
import os
import re
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

        # 2. Lancement du navigateur Microsoft Edge
        report(0.10, "Lancement de Microsoft Edge...")
        context, page = await stealth_browser.launch()
        total_saved_leads = 0

        try:
            # 3. Authentification avec callback en direct
            def auth_status_cb(msg: str):
                report(0.15, msg)

            is_auth = await auth_manager.authenticate(context, page, status_callback=auth_status_cb)
            if not is_auth:
                audit_logger.log_event("PIPELINE_ABORT", "Échec d'authentification. Pipeline interrompu.")
                report(0.15, "❌ Échec d'authentification. Veuillez vérifier votre connexion.")
                return 0

            if stop_check and stop_check():
                report(0.15, "🛑 Prospection interrompue par l'utilisateur.")
                return 0

            # 4. Activité leurre (Decoy)
            report(0.20, "Simulation de navigation naturelle sur LinkedIn...")
            await linkedin_browser_scraper.perform_decoy_activity(page)

            # 5. Parcours des cibles
            total_combinations = max(len(target_companies) * len(target_titles), 1)
            comb_idx = 0
            seen_in_session = set()
            session_leads_list = []

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
                    
                    profiles = await linkedin_browser_scraper.search_and_scrape(
                        page=page,
                        company=company,
                        keywords=title,
                        location=location,
                        max_profiles=max_profiles_per_search,
                        stop_check=stop_check
                    )

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

                        # Déduplication en direct : ignorer immédiatement les personnes déjà traitées
                        if lead_key in seen_in_session:
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
