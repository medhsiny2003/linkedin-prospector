import sqlite3
import os
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class DatabaseManager:
    """SQLite database manager in WAL mode for LinkedIn Prospector contacts."""

    def __init__(self, db_path: str = 'data/prospector.db'):
        self.db_path = db_path
        self.conn = None
        self._init_db()

    def _init_db(self) -> None:
        """Initializes tables, WAL mode, and indexes."""
        os.makedirs(os.path.dirname(self.db_path) or 'data', exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        
        # Contacts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                title TEXT DEFAULT '',
                company TEXT NOT NULL,
                email TEXT DEFAULT '',
                email_alt1 TEXT DEFAULT '',
                email_alt2 TEXT DEFAULT '',
                confidence_score INTEGER DEFAULT 0,
                mx_status TEXT DEFAULT 'unknown',
                mx_active TEXT DEFAULT '',
                linkedin_url TEXT DEFAULT '',
                extraction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                source TEXT DEFAULT 'xray',
                UNIQUE(first_name, last_name, company, linkedin_url)
            );
        """)
        
        # Indexes for fast querying & analytics
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_company ON contacts(company);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_status ON contacts(mx_status);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_score ON contacts(confidence_score);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contacts_date ON contacts(extraction_date);")
        
        self.conn.commit()

    def insert_contact(self, contact: Any) -> Optional[int]:
        """Inserts or updates a contact record."""
        try:
            cursor = self.conn.cursor()
            
            # Handle both Contact dataclass and dict
            if isinstance(contact, dict):
                first_name = contact.get('first_name', '')
                last_name = contact.get('last_name', '')
                title = contact.get('title', '')
                company = contact.get('company', '')
                email = contact.get('email', '')
                email_alt1 = contact.get('email_alt1', '')
                email_alt2 = contact.get('email_alt2', '')
                score = contact.get('confidence_score', 0)
                mx_status = contact.get('mx_status', 'unknown')
                mx_active = contact.get('mx_active', '')
                linkedin_url = contact.get('linkedin_url', '')
                extraction_date = contact.get('extraction_date', datetime.now().isoformat())
                source = contact.get('source', 'xray')
            else:
                first_name = getattr(contact, 'first_name', '')
                last_name = getattr(contact, 'last_name', '')
                title = getattr(contact, 'title', '')
                company = getattr(contact, 'company', '')
                email = getattr(contact, 'email', '')
                email_alt1 = getattr(contact, 'email_alt1', '')
                email_alt2 = getattr(contact, 'email_alt2', '')
                score = getattr(contact, 'confidence_score', 0)
                mx_status = getattr(contact, 'mx_status', 'unknown')
                mx_active = getattr(contact, 'mx_active', '')
                linkedin_url = getattr(contact, 'linkedin_url', '')
                extraction_date = getattr(contact, 'extraction_date', datetime.now().isoformat())
                source = getattr(contact, 'source', 'xray')

            cursor.execute("""
                INSERT OR REPLACE INTO contacts (
                    first_name, last_name, title, company, email, email_alt1, email_alt2,
                    confidence_score, mx_status, mx_active, linkedin_url, extraction_date, source
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                first_name, last_name, title, company,
                email, email_alt1, email_alt2, score,
                mx_status, str(mx_active), linkedin_url,
                extraction_date, source
            ))
            self.conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error inserting contact: {e}")
            return None

    def get_all_contacts(self) -> List[Dict[str, Any]]:
        """Retrieves all contacts sorted by company and last name."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contacts ORDER BY company, last_name")
        return [dict(row) for row in cursor.fetchall()]

    def get_contacts_by_company(self, company: str) -> List[Dict[str, Any]]:
        """Retrieves contacts for a specific company."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM contacts WHERE company = ? ORDER BY last_name", (company,))
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, Any]:
        """Calculates KPI statistics over stored contacts."""
        cursor = self.conn.cursor()
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        stats['total_contacts'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT company, COUNT(*) FROM contacts GROUP BY company")
        stats['by_company'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT mx_status, COUNT(*) FROM contacts GROUP BY mx_status")
        stats['by_mx_status'] = {row[0]: row[1] for row in cursor.fetchall()}
        
        cursor.execute("SELECT AVG(confidence_score) FROM contacts WHERE confidence_score > 0")
        avg = cursor.fetchone()[0]
        stats['avg_confidence'] = float(avg) if avg else 0.0
        
        return stats

    def search_contacts(self, query: str) -> List[Dict[str, Any]]:
        """Performs full-text search across contacts."""
        cursor = self.conn.cursor()
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT * FROM contacts 
            WHERE first_name LIKE ? OR last_name LIKE ? OR company LIKE ? OR title LIKE ?
            ORDER BY company, last_name
        """, (search_term, search_term, search_term, search_term))
        return [dict(row) for row in cursor.fetchall()]

    def export_to_dicts(self) -> List[Dict[str, Any]]:
        """Exports all records as list of dictionaries."""
        return self.get_all_contacts()

    def close(self) -> None:
        """Closes active database connection."""
        if self.conn:
            try:
                self.conn.close()
            except Exception:
                pass
            self.conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
