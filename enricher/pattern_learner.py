"""
Module d'Apprentissage Continu des Patterns d'Emails par Domaine (Couche 5 & Moteur 1).
Analyse les emails réels/validés pour déduire le pattern mathématique exact et
le mémoriser dans la base SQLite 'domain_patterns'.
"""

import re
import sqlite3
from pathlib import Path
from typing import Dict, Optional, Tuple
from config import config


class PatternLearner:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or config.DATABASE_PATH
        self._init_db()

    def _init_db(self):
        """Initialise la table 'domain_patterns' pour l'apprentissage continu."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS domain_patterns (
                    domain TEXT PRIMARY KEY,
                    company_name TEXT,
                    confirmed_pattern TEXT,
                    confidence REAL DEFAULT 1.0,
                    sample_email TEXT,
                    times_confirmed INTEGER DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()

    @staticmethod
    def extract_pattern(first_name: str, last_name: str, email: str) -> Optional[str]:
        """
        Déduit le pattern mathématique à partir d'un email réel et du nom/prénom.
        Ex: 'jean.dupont@thalesgroup.com', 'Jean', 'Dupont' -> '{first}.{last}@{domain}'
        """
        if not email or "@" not in email or not first_name or not last_name:
            return None

        local_part, domain = email.strip().lower().split("@", 1)
        f = first_name.strip().lower().replace("-", "")
        l = last_name.strip().lower().replace("-", "")
        f_init = f[0] if f else ""
        l_init = l[0] if l else ""

        # Mapping des patterns déterministes
        if local_part == f"{f}.{l}":
            return "{first}.{last}@{domain}"
        elif local_part == f"{f}{l}":
            return "{first}{last}@{domain}"
        elif local_part == f"{f_init}{l}":
            return "{f}{last}@{domain}"
        elif local_part == f"{f_init}.{l}":
            return "{f}.{last}@{domain}"
        elif local_part == f"{f}_{l}":
            return "{first}_{last}@{domain}"
        elif local_part == f"{f}-{l}":
            return "{first}-{last}@{domain}"
        elif local_part == f"{l}.{f}":
            return "{last}.{first}@{domain}"
        elif local_part == f"{f}{l_init}":
            return "{first}{l}@{domain}"
        elif local_part == f:
            return "{first}@{domain}"
        elif local_part == l:
            return "{last}@{domain}"

        return None

    def learn_pattern(self, first_name: str, last_name: str, email: str, company_name: str = "") -> Optional[str]:
        """
        Apprend et enregistre le pattern d'un domaine dès qu'un email est confirmé.
        """
        if not email or "@" not in email:
            return None

        domain = email.split("@")[1].strip().lower()
        pattern = self.extract_pattern(first_name, last_name, email)
        if not pattern:
            return None

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO domain_patterns (domain, company_name, confirmed_pattern, confidence, sample_email, times_confirmed, last_updated)
                VALUES (?, ?, ?, 1.0, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(domain) DO UPDATE SET
                    confirmed_pattern = excluded.confirmed_pattern,
                    confidence = MIN(domain_patterns.confidence + 0.1, 1.0),
                    times_confirmed = domain_patterns.times_confirmed + 1,
                    last_updated = CURRENT_TIMESTAMP;
            """, (domain, company_name, pattern, email))
            conn.commit()

        return pattern

    def get_learned_pattern(self, domain: str) -> Optional[Dict[str, any]]:
        """
        Récupère le pattern appris pour un domaine donné.
        """
        domain = domain.strip().lower()
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM domain_patterns WHERE domain = ?", (domain,))
            row = cursor.fetchone()
            if row:
                return dict(row)
        return None


pattern_learner = PatternLearner()
