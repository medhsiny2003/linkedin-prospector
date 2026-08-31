"""
Tests unitaires pour les utilitaires de données et d'export de l'interface Streamlit.
"""

import os
import tempfile
from pathlib import Path
import pandas as pd
import pytest
from app.utils.data_processor import get_all_leads_df, get_kpi_metrics
from app.utils.export_helper import generate_csv_bytes, generate_excel_bytes
from storage.db_manager import DBManager


@pytest.fixture
def sample_leads_df():
    data = [
        {
            "id": 1,
            "first_name": "Jean",
            "last_name": "Dupont",
            "job_title": "Chef de projet Drones",
            "company": "Thales",
            "profile_url": "https://www.linkedin.com/in/jean-dupont",
            "proposed_email": "jean.dupont@thalesgroup.com",
            "alt_email_1": "jeandupont@thalesgroup.com",
            "alt_email_2": "j.dupont@thalesgroup.com",
            "confidence_score": 95,
            "status": "Validé",
            "mx_verified": "Oui",
            "matched_keywords": "Thales, Recruteur",
            "created_at": "2026-08-28T03:00:00+00:00",
            "updated_at": "2026-08-28T03:00:00+00:00"
        },
        {
            "id": 2,
            "first_name": "Alice",
            "last_name": "Martin",
            "job_title": "Talent Acquisition",
            "company": "Airbus",
            "profile_url": "https://www.linkedin.com/in/alice-martin",
            "proposed_email": "alice.martin@airbus.com",
            "alt_email_1": "alicemartin@airbus.com",
            "alt_email_2": "a.martin@airbus.com",
            "confidence_score": 90,
            "status": "À vérifier",
            "mx_verified": "Non",
            "matched_keywords": "Airbus, RH",
            "created_at": "2026-08-28T03:30:00+00:00",
            "updated_at": "2026-08-28T03:30:00+00:00"
        }
    ]
    return pd.DataFrame(data)


def test_generate_excel_bytes(sample_leads_df):
    excel_bytes = generate_excel_bytes(sample_leads_df)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 0


def test_generate_csv_bytes(sample_leads_df):
    csv_bytes = generate_csv_bytes(sample_leads_df)
    assert isinstance(csv_bytes, bytes)
    assert len(csv_bytes) > 0
    decoded = csv_bytes.decode("utf-8-sig")
    assert "jean.dupont@thalesgroup.com" in decoded
    assert ";" in decoded


def test_active_config_sync():
    from app.utils.state_manager import save_active_config, get_active_config
    test_data = {
        "selected_profile": "Mon Profil Test Personnalise",
        "companies": "OCP Group, UM6P",
        "job_titles": "Ingenieur R&D",
        "location": "Benguerir, Maroc",
        "max_contacts": 25
    }
    save_active_config(test_data)
    loaded = get_active_config()
    assert loaded["selected_profile"] == "Mon Profil Test Personnalise"
    assert loaded["companies"] == "OCP Group, UM6P"
    assert loaded["location"] == "Benguerir, Maroc"
    assert loaded["max_contacts"] == 25

