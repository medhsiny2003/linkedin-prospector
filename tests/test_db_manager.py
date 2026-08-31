"""
Tests unitaires pour la gestion de base de données SQLite (Mode WAL, UPSERT, Statistiques).
"""

import gc
import os
import tempfile
from pathlib import Path
import pytest
from storage.db_manager import DBManager


@pytest.fixture
def temp_db():
    fd, path_str = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db_path = Path(path_str)
    db = DBManager(db_path=db_path)
    yield db
    del db
    gc.collect()
    try:
        if db_path.exists():
            os.remove(db_path)
    except Exception:
        pass


def test_insert_and_get_lead(temp_db):
    lead = {
        "first_name": "Sophie",
        "last_name": "Martin",
        "job_title": "Responsable Recrutement Drones",
        "company": "Thales",
        "profile_url": "https://www.linkedin.com/in/sophie-martin-test",
        "proposed_email": "sophie.martin@thalesgroup.com",
        "alt_email_1": "sophiemartin@thalesgroup.com",
        "alt_email_2": "s.martin@thalesgroup.com",
        "confidence_score": 95,
        "status": "Validé",
        "mx_verified": "Oui",
        "matched_keywords": "Thales, Recruteur"
    }

    assert temp_db.save_lead(lead) is True

    leads = temp_db.get_all_leads()
    assert len(leads) == 1
    assert leads[0]["first_name"] == "Sophie"
    assert leads[0]["status"] == "Validé"


def test_lead_upsert_deduplication(temp_db):
    url = "https://www.linkedin.com/in/unique-profile"
    lead1 = {
        "first_name": "Marc",
        "last_name": "Dupont",
        "job_title": "Ingénieur R&D",
        "company": "Airbus",
        "profile_url": url,
        "status": "À vérifier"
    }
    temp_db.save_lead(lead1)

    lead2 = {
        "first_name": "Marc",
        "last_name": "Dupont",
        "job_title": "Chef de projet Drones",
        "company": "Airbus",
        "profile_url": url,
        "status": "Validé"
    }
    temp_db.save_lead(lead2)

    leads = temp_db.get_all_leads()
    assert len(leads) == 1
    assert leads[0]["job_title"] == "Chef de projet Drones"
    assert leads[0]["status"] == "Validé"


def test_stats(temp_db):
    stats = temp_db.get_stats()
    assert stats["total_leads"] == 0


def test_lead_exists_and_deduplicate(temp_db):
    lead1 = {
        "first_name": "Antonin",
        "last_name": "Parrot",
        "job_title": "Manager",
        "company": "Parrot",
        "profile_url": "https://www.linkedin.com/in/antonin-parrot"
    }
    assert temp_db.save_lead(lead1) is True
    assert temp_db.lead_exists("Antonin", "Parrot", "Parrot") is True
    assert temp_db.lead_exists("Inconnu", "Personne", "Parrot") is False

    # Deuxième sauvegarde avec variation d'URL
    lead2 = {
        "first_name": "Antonin",
        "last_name": "Parrot",
        "job_title": "Lead Manager",
        "company": "Parrot",
        "profile_url": "https://fr.linkedin.com/in/antonin-parrot?sub=1"
    }
    temp_db.save_lead(lead2)
    assert len(temp_db.get_all_leads()) == 1
    assert temp_db.get_all_leads()[0]["job_title"] == "Lead Manager"
