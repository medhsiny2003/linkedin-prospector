"""
Tests unitaires pour l'Architecture d'Emails 5 Couches (Apprentissage, Crawling, OSINT, Permutation, Agrégation).
"""

import pytest
from enricher.pattern_learner import PatternLearner
from enricher.email_orchestrator import EmailOrchestrator


@pytest.fixture
def learner(tmp_path):
    db_file = tmp_path / "test_patterns.db"
    return PatternLearner(db_path=db_file)


def test_extract_pattern_standard(learner):
    pat = learner.extract_pattern("Jean", "Dupont", "jean.dupont@thalesgroup.com")
    assert pat == "{first}.{last}@{domain}"


def test_extract_pattern_initial(learner):
    pat = learner.extract_pattern("Guilhem", "Marliave", "gmarliave@elistair.com")
    assert pat == "{f}{last}@{domain}"


def test_learn_and_retrieve_pattern(learner):
    # Apprendre un pattern pour dronevolt.com
    learner.learn_pattern("Marc", "Bernard", "m.bernard@dronevolt.com", "Drone Volt")
    
    # Vérifier la récupération
    learned = learner.get_learned_pattern("dronevolt.com")
    assert learned is not None
    assert learned["confirmed_pattern"] == "{f}.{last}@{domain}"
    assert learned["confidence"] == 1.0


def test_email_orchestrator_discovery():
    orchestrator = EmailOrchestrator()
    res = orchestrator.discover_and_validate("Sébastien", "Munsch", "Elistair")
    assert res["proposed_email"] != ""
    assert "@" in res["proposed_email"]
    assert res["domain"] == "elistair.com"
    assert res["confidence_score"] >= 70


def test_email_orchestrator_morocco_companies():
    orchestrator = EmailOrchestrator()
    
    # 1. OCP Group
    res_ocp = orchestrator.discover_and_validate("Amine", "El Amrani", "OCP Group")
    assert res_ocp["domain"] == "ocpgroup.ma"
    assert res_ocp["proposed_email"] == "amine.elamrani@ocpgroup.ma"

    # 2. UM6P
    res_um6p = orchestrator.discover_and_validate("Mehdi", "Benjelloun", "UM6P")
    assert res_um6p["domain"] == "um6p.ma"
    assert res_um6p["proposed_email"] == "mehdi.benjelloun@um6p.ma"

    # 3. MAScIR
    res_mascir = orchestrator.discover_and_validate("Fatima Zahra", "Bennani", "MAScIR")
    assert res_mascir["domain"] == "mascir.com"
    assert "@mascir.com" in res_mascir["proposed_email"]

    # 4. Safran Maroc
    res_safran = orchestrator.discover_and_validate("Youssef", "Ait Ali", "Safran Maroc")
    assert res_safran["domain"] == "safrangroup.com"
    assert res_safran["proposed_email"] == "youssef.aitali@safrangroup.com"

