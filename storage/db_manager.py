"""
Gestionnaire de persistance SQLite avec mode WAL (Write-Ahead Logging).
Prend en charge la déduplication stricte des profils, le nettoyage des doublons
et le suivi des campagnes.
"""

import concurrent.futures
import re
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from config import config
from core.monitoring.audit_logger import audit_logger


class DBManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Crée une connexion SQLite avec le mode WAL activé."""
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def init_db(self) -> None:
        """Initialise le schéma de base de données s'il n'existe pas."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS leads (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    job_title TEXT,
                    company TEXT,
                    profile_url TEXT UNIQUE,
                    proposed_email TEXT,
                    alt_email_1 TEXT,
                    alt_email_2 TEXT,
                    confidence_score INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'À vérifier',
                    mx_verified TEXT DEFAULT 'Non',
                    matched_keywords TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS campaign_state (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    campaign_name TEXT UNIQUE,
                    start_date TEXT NOT NULL,
                    actions_today INTEGER DEFAULT 0,
                    last_action_date TEXT
                );
            """)

            # Nettoyage automatique des anciennes URLs corrompues non-LinkedIn
            cursor.execute("""
                UPDATE leads 
                SET profile_url = NULL 
                WHERE profile_url IS NOT NULL 
                  AND (profile_url LIKE '%bing.com/ck/a%' OR profile_url NOT LIKE '%linkedin.com/in/%');
            """)
            conn.commit()

    @staticmethod
    def normalize_profile_url(url: str) -> str:
        """Normalise l'URL LinkedIn pour garantir une déduplication parfaite et décoder les redirections Bing."""
        if not url:
            return ""

        # Décodage des liens de redirection Bing (/ck/a?u=...)
        if "bing.com/ck/a" in url and "u=" in url:
            try:
                import base64
                import urllib.parse
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                if "u" in params and params["u"]:
                    u_val = params["u"][0]
                    if u_val.startswith("a1"):
                        b64 = u_val[2:]
                        b64 += "=" * ((4 - len(b64) % 4) % 4)
                        decoded = base64.b64decode(b64).decode("utf-8", errors="ignore")
                        if "linkedin.com/in/" in decoded:
                            url = decoded
            except Exception:
                pass

        clean = url.split("?")[0].rstrip("/")
        clean = re.sub(r"^https?:\/\/(?:[a-z]{2}\.)?linkedin\.com", "https://www.linkedin.com", clean)

        # Validation stricte : doit être un vrai profil LinkedIn (contient /in/identifiant)
        if not re.search(r"linkedin\.com\/in\/[a-zA-Z0-9_\-\%]{2,}", clean):
            return ""

        return clean

    def lead_exists(self, first_name: str, last_name: str, company: str, profile_url: str = "") -> bool:
        """Vérifie si un contact identique existe déjà dans la base."""
        norm_url = self.normalize_profile_url(profile_url)
        fn = first_name.strip().lower()
        ln = last_name.strip().lower()
        comp = company.strip().lower()

        if not fn or not ln:
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            if norm_url:
                cursor.execute("SELECT id FROM leads WHERE profile_url = ?;", (norm_url,))
                if cursor.fetchone():
                    return True

            cursor.execute(
                "SELECT id FROM leads WHERE LOWER(first_name) = ? AND LOWER(last_name) = ? AND LOWER(company) = ?;",
                (fn, ln, comp)
            )
            return cursor.fetchone() is not None

    def save_lead(self, lead: Dict[str, Any]) -> bool:
        """
        Enregistre ou met à jour un lead avec déduplication intelligente
        sur l'URL de profil ET sur le triplet (Prénom, Nom, Entreprise).
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        norm_url = self.normalize_profile_url(lead.get("profile_url", ""))
        fn = lead.get("first_name", "").strip()
        ln = lead.get("last_name", "").strip()
        comp = lead.get("company", "").strip()

        if not fn or not ln:
            return False

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Recherche d'un doublon existant (par URL ou par Nom+Prénom+Entreprise)
                existing_id = None
                if norm_url:
                    cursor.execute("SELECT id FROM leads WHERE profile_url = ?;", (norm_url,))
                    row = cursor.fetchone()
                    if row:
                        existing_id = row["id"]

                if not existing_id:
                    cursor.execute(
                        "SELECT id FROM leads WHERE LOWER(first_name) = ? AND LOWER(last_name) = ? AND LOWER(company) = ?;",
                        (fn.lower(), ln.lower(), comp.lower())
                    )
                    row = cursor.fetchone()
                    if row:
                        existing_id = row["id"]

                if existing_id:
                    # Mise à jour du lead existant
                    cursor.execute("""
                        UPDATE leads SET
                            job_title = :job_title,
                            company = :company,
                            profile_url = COALESCE(NULLIF(:profile_url, ''), profile_url),
                            proposed_email = :proposed_email,
                            alt_email_1 = :alt_email_1,
                            alt_email_2 = :alt_email_2,
                            confidence_score = :confidence_score,
                            status = :status,
                            mx_verified = :mx_verified,
                            matched_keywords = :matched_keywords,
                            updated_at = :updated_at
                        WHERE id = :id;
                    """, {
                        "id": existing_id,
                        "job_title": lead.get("job_title", ""),
                        "company": comp,
                        "profile_url": norm_url,
                        "proposed_email": lead.get("proposed_email", ""),
                        "alt_email_1": lead.get("alt_email_1", ""),
                        "alt_email_2": lead.get("alt_email_2", ""),
                        "confidence_score": lead.get("confidence_score", 0),
                        "status": lead.get("status", "À vérifier"),
                        "mx_verified": lead.get("mx_verified", "Non"),
                        "matched_keywords": lead.get("matched_keywords", ""),
                        "updated_at": now_iso
                    })
                else:
                    # Insertion d'un nouveau lead
                    cursor.execute("""
                        INSERT INTO leads (
                            first_name, last_name, job_title, company, profile_url,
                            proposed_email, alt_email_1, alt_email_2,
                            confidence_score, status, mx_verified, matched_keywords,
                            created_at, updated_at
                        ) VALUES (
                            :first_name, :last_name, :job_title, :company, :profile_url,
                            :proposed_email, :alt_email_1, :alt_email_2,
                            :confidence_score, :status, :mx_verified, :matched_keywords,
                            :created_at, :updated_at
                        );
                    """, {
                        "first_name": fn,
                        "last_name": ln,
                        "job_title": lead.get("job_title", ""),
                        "company": comp,
                        "profile_url": norm_url or None,
                        "proposed_email": lead.get("proposed_email", ""),
                        "alt_email_1": lead.get("alt_email_1", ""),
                        "alt_email_2": lead.get("alt_email_2", ""),
                        "confidence_score": lead.get("confidence_score", 0),
                        "status": lead.get("status", "À vérifier"),
                        "mx_verified": lead.get("mx_verified", "Non"),
                        "matched_keywords": lead.get("matched_keywords", ""),
                        "created_at": now_iso,
                        "updated_at": now_iso
                    })
                conn.commit()
                return True
        except Exception as e:
            audit_logger.log_event("DB_ERROR", f"Erreur lors de la sauvegarde du lead : {e}")
            return False

    def deduplicate_and_clean_db(self) -> int:
        """
        Nettoie la base de données en profondeur :
        1. Valide et reformate tous les prénoms et noms selon les standards français stricts.
        2. Supprime les profils corrompus ou sans nom valide (< 2 lettres, 'Utilisateur', etc.).
        3. Supprime les doublons en ne conservant que la version la plus complète.
        """
        from scrapers.parsers.dom_parser import dom_parser

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, first_name, last_name, company FROM leads;")
            rows = cursor.fetchall()

            deleted_ids = []
            for row in rows:
                row_id = row["id"]
                fn_raw = row["first_name"] or ""
                ln_raw = row["last_name"] or ""

                fn_clean, ln_clean = dom_parser.parse_full_name(f"{fn_raw} {ln_raw}")

                if not fn_clean or not ln_clean or len(fn_clean) < 2 or len(ln_clean) < 2:
                    deleted_ids.append(row_id)
                else:
                    if fn_clean != fn_raw or ln_clean != ln_raw:
                        cursor.execute(
                            "UPDATE leads SET first_name = ?, last_name = ? WHERE id = ?;",
                            (fn_clean, ln_clean, row_id)
                        )

            if deleted_ids:
                placeholders = ",".join("?" for _ in deleted_ids)
                cursor.execute(f"DELETE FROM leads WHERE id IN ({placeholders});", deleted_ids)

            # Suppression des doublons sur (first_name, last_name, company) en gardant le MAX(id)
            cursor.execute("""
                DELETE FROM leads
                WHERE id NOT IN (
                    SELECT MAX(id)
                    FROM leads
                    GROUP BY LOWER(first_name), LOWER(last_name), LOWER(company)
                );
            """)
            deleted_count = cursor.rowcount + len(deleted_ids)
            conn.commit()
            return deleted_count

    def deep_verify_and_clean_db(self) -> Dict[str, int]:
        """
        Audit et re-vérification approfondie :
        1. Nettoyage personne par personne (noms français stricts, suppression des profils invalides).
        2. Déduplication intégrale sur (first_name, last_name, company).
        3. Re-vérification email par email via l'Orchestrateur 5 Couches (probing MX, scoring, patterns).
        Retourne {'total': int, 'deleted_or_duplicates': int, 'verified': int}.
        """
        from enricher.email_orchestrator import EmailOrchestrator
        orchestrator = EmailOrchestrator()

        # 1. Nettoyage des noms et suppression des profils corrompus / doublons
        deleted_count = self.deduplicate_and_clean_db()

        # 2. Récupération des leads hors transaction pour éviter tout verrouillage
        leads = self.get_all_leads()

        updates = []
        now_iso = datetime.now().isoformat()

        def _verify_single_lead(lead_item):
            lid = lead_item["id"]
            fn_l = lead_item.get("first_name", "") or ""
            ln_l = lead_item.get("last_name", "") or ""
            comp_l = lead_item.get("company", "") or ""
            try:
                res_l = orchestrator.discover_and_validate(fn_l, ln_l, comp_l, fast_mode=True)
                return {
                    "id": lid,
                    "proposed_email": res_l.get("proposed_email", ""),
                    "alt_email_1": res_l.get("alt_email_1", ""),
                    "alt_email_2": res_l.get("alt_email_2", ""),
                    "confidence_score": res_l.get("confidence_score", 0),
                    "status": res_l.get("status", "À vérifier"),
                    "mx_verified": res_l.get("mx_verified", "Non"),
                    "updated_at": now_iso
                }
            except Exception:
                return None

        # Exécution ultra-rapide en multi-threads (10 workers)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            results = executor.map(_verify_single_lead, leads)
            for r in results:
                if r:
                    updates.append(r)

        # 3. Écriture atomique en batch
        if updates:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.executemany("""
                    UPDATE leads SET
                        proposed_email = :proposed_email,
                        alt_email_1 = :alt_email_1,
                        alt_email_2 = :alt_email_2,
                        confidence_score = :confidence_score,
                        status = :status,
                        mx_verified = :mx_verified,
                        updated_at = :updated_at
                    WHERE id = :id;
                """, updates)
                conn.commit()

        return {
            "total": len(leads),
            "deleted_or_duplicates": deleted_count,
            "verified": len(updates)
        }

    def get_all_leads(self) -> List[Dict[str, Any]]:
        """Récupère l'intégralité des leads enregistrés (les plus récents en premier)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM leads ORDER BY COALESCE(updated_at, created_at) DESC, id DESC;")
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_or_create_campaign_start_date(self, campaign_name: str = "default_campaign") -> date:
        """Récupère la date de début d'une campagne ou la crée à aujourd'hui."""
        today_str = date.today().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT start_date FROM campaign_state WHERE campaign_name = ?", (campaign_name,))
            row = cursor.fetchone()
            if row:
                return date.fromisoformat(row["start_date"])
            else:
                cursor.execute(
                    "INSERT INTO campaign_state (campaign_name, start_date, last_action_date) VALUES (?, ?, ?)",
                    (campaign_name, today_str, today_str)
                )
                conn.commit()
                return date.today()

    def get_stats(self) -> Dict[str, Any]:
        """Retourne des métriques clés sur la base de données."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM leads;")
            total = cursor.fetchone()["total"]

            cursor.execute("SELECT COUNT(*) as validated FROM leads WHERE status LIKE 'Validé%' OR mx_verified = 'Oui';")
            validated = cursor.fetchone()["validated"]

            cursor.execute("SELECT COUNT(*) as mx_yes FROM leads WHERE mx_verified = 'Oui';")
            mx_yes = cursor.fetchone()["mx_yes"]

            return {
                "total_leads": total,
                "validated_leads": validated,
                "mx_verified_leads": mx_yes
            }


db_manager = DBManager()
