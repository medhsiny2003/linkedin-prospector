"""
Worker d'arrière-plan découplé pour l'exécution de la prospection LinkedIn.
Permet d'exécuter le scraping dans un thread indépendant avec contrôle d'exécution :
- Démarrage (start_job)
- Pause (pause_job)
- Reprise (resume_job)
- Arrêt d'urgence immédiat (stop_job)
- Réinitialisation (reset_job)
"""

import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional
from core.browser.stealth_browser import stealth_browser
from core.monitoring.audit_logger import audit_logger
from scrapers.hybrid_scraper import hybrid_scraper


class PipelineWorker:
    def __init__(self):
        self._lock = threading.Lock()
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._current_task: Optional[asyncio.Task] = None
        self._is_running: bool = False
        self._is_paused: bool = False
        self._should_stop: bool = False
        self._progress: float = 0.0
        self._current_status: str = "Prêt"
        self._logs: List[str] = []
        self._recent_leads: List[dict] = []
        self._total_saved: int = 0
        self._error: Optional[str] = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    @property
    def is_paused(self) -> bool:
        with self._lock:
            return self._is_paused

    def get_status(self) -> Dict[str, Any]:
        """Retourne un instantané thread-safe de l'état d'exécution du worker."""
        with self._lock:
            return {
                "is_running": self._is_running,
                "is_paused": self._is_paused,
                "progress": self._progress,
                "current_status": self._current_status,
                "logs": list(self._logs),
                "recent_leads": list(self._recent_leads),
                "total_saved": self._total_saved,
                "error": self._error
            }

    def start_job(
        self,
        companies: List[str],
        job_titles: List[str],
        location: str = "France",
        max_profiles_per_search: int = 10
    ) -> bool:
        """Démarre le job de prospection en arrière-plan."""
        with self._lock:
            if self._is_running:
                return False

            # Archivage automatique de la session précédente vers l'archive unique
            try:
                from storage.exporter import excel_exporter
                excel_exporter.archive_current_session_file()
                excel_exporter.export_leads([])  # Initialise le fichier de session à 0
            except Exception:
                pass

            self._is_running = True
            self._is_paused = False
            self._should_stop = False
            self._progress = 0.05
            self._current_status = "Initialisation de Microsoft Edge..."
            self._logs = [f"[{datetime.now().strftime('%H:%M:%S')}] 🚀 Démarrage du job de prospection..."]
            self._recent_leads = []
            self._total_saved = 0
            self._error = None

        self._thread = threading.Thread(
            target=self._run_async_pipeline,
            args=(companies, job_titles, location, max_profiles_per_search),
            daemon=True
        )
        self._thread.start()
        return True

    def pause_job(self) -> None:
        """Met le job en pause."""
        with self._lock:
            if self._is_running and not self._is_paused:
                self._is_paused = True
                self._current_status = "⏸️ Prospection en pause..."
                self._logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ⏸️ Prospection mise en pause par l'utilisateur.")

    def resume_job(self) -> None:
        """Reprend le job mis en pause."""
        with self._lock:
            if self._is_running and self._is_paused:
                self._is_paused = False
                self._current_status = "▶️ Reprise de la prospection..."
                self._logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ▶️ Reprise de la prospection.")

    def stop_job(self) -> None:
        """Demande l'arrêt d'urgence immédiat du job en cours et coupe le navigateur."""
        loop_to_cancel = None
        task_to_cancel = None
        with self._lock:
            self._should_stop = True
            self._is_running = False
            self._is_paused = False
            self._current_status = "🛑 Prospection arrêtée par l'utilisateur."
            self._logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Prospection arrêtée immédiatement.")
            loop_to_cancel = self._loop
            task_to_cancel = self._current_task
            leads_snapshot = list(self._recent_leads)

        # Sauvegarde d'urgence immédiate de tous les leads qualifiés dans SQLite et Excel
        try:
            from storage.db_manager import db_manager
            from storage.exporter import excel_exporter
            for lead in leads_snapshot:
                db_manager.save_lead(lead)
            excel_exporter.export_leads(leads_snapshot)
        except Exception:
            pass

        # Annulation immédiate de la tâche asynchrone Playwright
        if loop_to_cancel and loop_to_cancel.is_running() and task_to_cancel and not task_to_cancel.done():
            loop_to_cancel.call_soon_threadsafe(task_to_cancel.cancel)

    def reset_job(self) -> None:
        """Réinitialise l'état pour une nouvelle session propre."""
        with self._lock:
            if not self._is_running:
                self._progress = 0.0
                self._current_status = "Prêt"
                self._logs = []
                self._recent_leads = []
                self._total_saved = 0
                self._error = None

    def _update_progress(self, pct: float, msg: str, lead_data: Optional[dict] = None):
        """Callback interne thread-safe pour la progression."""
        with self._lock:
            self._progress = min(max(pct, 0.0), 1.0)
            self._current_status = msg
            ts = datetime.now().strftime("%H:%M:%S")
            self._logs.append(f"[{ts}] {msg}")
            if len(self._logs) > 200:
                self._logs.pop(0)

            if lead_data:
                self._recent_leads.append(lead_data)
                self._total_saved += 1
                # Synchronisation immédiate du fichier Excel sur disque pour chaque contact trouvé (résistance coupure)
                try:
                    from storage.exporter import excel_exporter
                    excel_exporter.export_leads(list(self._recent_leads))
                except Exception:
                    pass

    def _run_async_pipeline(
        self,
        companies: List[str],
        job_titles: List[str],
        location: str,
        max_profiles_per_search: int
    ):
        """Exécute la boucle asyncio dans le thread dédié."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self._lock:
            self._loop = loop

        try:
            task = loop.create_task(
                hybrid_scraper.run_prospecting_pipeline(
                    companies=companies,
                    job_titles=job_titles,
                    location=location,
                    max_profiles_per_search=max_profiles_per_search,
                    progress_callback=self._update_progress,
                    stop_check=lambda: self._should_stop,
                    pause_check=lambda: self._is_paused
                )
            )
            with self._lock:
                self._current_task = task

            total = loop.run_until_complete(task)
            with self._lock:
                if not self._should_stop:
                    self._progress = 1.0
                    self._total_saved = total
                    self._current_status = f"✅ Prospection terminée avec succès ({total} contacts enrichis)."
                    self._logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Job terminé.")
        except asyncio.CancelledError:
            with self._lock:
                self._current_status = "🛑 Prospection interrompue immédiatement."
                self._logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] 🛑 Arrêt immédiat effectué.")
        except Exception as e:
            with self._lock:
                self._error = str(e)
                self._current_status = f"Erreur : {e}"
                self._logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Erreur : {e}")
                audit_logger.log_event("WORKER_ERROR", f"Exception dans le scraping : {e}")
        finally:
            try:
                loop.run_until_complete(stealth_browser.close())
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            try:
                loop.close()
            except Exception:
                pass
            with self._lock:
                self._is_running = False
                self._is_paused = False
                self._current_task = None
                self._loop = None


# Instance unique (Singleton global)
pipeline_worker = PipelineWorker()
