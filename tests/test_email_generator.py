"""
Tests unitaires pour le générateur d'emails (22 patterns déterministes et résolution de domaine).
"""

import pytest
from enricher.email_generator import EmailGenerator


@pytest.fixture
def generator():
    return EmailGenerator()


def test_strip_accents(generator):
    assert generator.strip_accents("Éléonore François Stéphane") == "Eleonore Francois Stephane"
    assert generator.strip_accents("Gaëtan Cédric") == "Gaetan Cedric"


def test_clean_name_part(generator):
    assert generator.clean_name_part("Dr. Jean-Pierre") == "jean-pierre"
    assert generator.clean_name_part("Ing. Marie") == "marie"
    assert generator.clean_name_part("DUPONT") == "dupont"


def test_resolve_known_domains(generator):
    assert generator.resolve_domain("Thales") == "thalesgroup.com"
    assert generator.resolve_domain("Airbus Helicopters") == "airbus.com"
    assert generator.resolve_domain("Safran Electronics & Defense") == "safrangroup.com"
    assert generator.resolve_domain("Dassault Aviation") == "dassault-aviation.com"
    assert generator.resolve_domain("Delair") == "delair.aero"
    assert generator.resolve_domain("Harmattan AI") == "harmattan.ai"
    assert generator.resolve_domain("OCP Group") == "ocpgroup.ma"
    assert generator.resolve_domain("UM6P") == "um6p.ma"



def test_resolve_unknown_domain(generator):
    assert generator.resolve_domain("StartUp Drone XYZ") == "startupdronexyz.com"


def test_generate_22_patterns(generator):
    candidates = generator.generate_candidates("Jean", "Dupont", "Thales")
    assert len(candidates) == 22
    
    # Vérification des formats clés
    emails = [c["email"] for c in candidates]
    assert "jean.dupont@thalesgroup.com" in emails
    assert "jeandupont@thalesgroup.com" in emails
    assert "j.dupont@thalesgroup.com" in emails
    assert "jeand@thalesgroup.com" in emails
    assert "dupont.jean@thalesgroup.com" in emails
    assert "jean_dupont@thalesgroup.com" in emails
    assert "jean-dupont@thalesgroup.com" in emails
    assert "jdupont@thalesgroup.com" in emails
    assert "jean@thalesgroup.com" in emails
    assert "dupont@thalesgroup.com" in emails
    assert "jeandupont1@thalesgroup.com" in emails

    # Vérification du top 1 (score 95%)
    top = generator.get_top_propositions("Jean", "Dupont", "Thales")
    assert top["proposed_email"] == "jean.dupont@thalesgroup.com"
    assert top["confidence_score"] == 95


def test_compound_names(generator):
    candidates = generator.generate_candidates("Jean-Marc", "Dupont", "Thales")
    emails = [c["email"] for c in candidates]
    assert "jm.dupont@thalesgroup.com" in emails
    assert "jmdupont@thalesgroup.com" in emails
    assert "jean.dupont@thalesgroup.com" in emails
