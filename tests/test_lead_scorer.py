"""
Tests unitaires pour le moteur de scoring et de priorisation des leads.
"""

import pytest
from enricher.lead_scorer import LeadScorer


@pytest.fixture
def scorer():
    return LeadScorer()


def test_score_hr_decision_maker(scorer):
    lead = {
        "job_title": "Responsable Ressources Humaines",
        "mx_verified": "Oui",
        "confidence_score": 90,
        "status": "Validé"
    }
    score, stars, badge = scorer.calculate_score(lead)
    assert score >= 80
    assert stars == "★★★"
    assert "Haute" in badge


def test_score_tech_lead_drone(scorer):
    lead = {
        "job_title": "Ingénieur R&D Systèmes Embarqués Drones",
        "mx_verified": "Oui",
        "confidence_score": 85,
        "status": "Validé"
    }
    score, stars, badge = scorer.calculate_score(lead)
    assert score >= 80
    assert stars == "★★★"


def test_score_standard_lead(scorer):
    lead = {
        "job_title": "Comptable",
        "mx_verified": "Non",
        "confidence_score": 50,
        "status": "Non vérifiable"
    }
    score, stars, badge = scorer.calculate_score(lead)
    assert score < 50
    assert stars == "★☆☆"
