"""
Tests unitaires pour le module de filtrage IA sémantique (ai_filter.py).
Vérifie le traitement par lot, le fallback local et la détection des profils pertinents.
"""

import pytest
from enricher.ai_filter import AIFilter, ai_filter


def test_ai_filter_fallback_empty():
    """Vérifie le comportement avec une liste vide."""
    assert ai_filter.filter_profiles_batch([], ["drone"]) == []
    assert ai_filter.filter_profiles_batch([{"name": "Test"}], []) == [{"name": "Test"}]


def test_ai_filter_semantic_matching():
    """Vérifie les correspondances sémantiques françaises et anglaises."""
    profiles = [
        {"first_name": "Jean", "last_name": "Dupont", "job_title": "Electrical Engineer chez Safran"},
        {"first_name": "Sophie", "last_name": "Martin", "job_title": "Responsable Recrutement / RH"},
        {"first_name": "Paul", "last_name": "Durand", "job_title": "Embedded Systems & Firmware Developer"},
        {"first_name": "Marc", "last_name": "Lefebvre", "job_title": "Comptable Fournisseurs"}
    ]

    # Test avec "électrotechnique" -> Doit retenir Electrical Engineer et RH
    results_elec = ai_filter._local_semantic_fallback(profiles, ["électrotechnique"], min_score=4)
    titles_elec = [p["job_title"] for p in results_elec]
    assert any("Electrical Engineer" in t for t in titles_elec)
    assert any("Recrutement" in t for t in titles_elec)
    assert not any("Comptable" in t for t in titles_elec)

    # Test avec "drone" -> Doit retenir Embedded Systems et RH
    results_drone = ai_filter._local_semantic_fallback(profiles, ["drone"], min_score=4)
    titles_drone = [p["job_title"] for p in results_drone]
    assert any("Embedded Systems" in t for t in titles_drone)
    assert any("Recrutement" in t for t in titles_drone)
    assert not any("Comptable" in t for t in titles_drone)


def test_ai_filter_scoring_attributes():
    """Vérifie que les métadonnées ai_score et ai_reason sont bien ajoutées aux profils retenus."""
    profiles = [
        {"first_name": "Alice", "last_name": "Tech", "job_title": "Directeur Technique & Systèmes Embarqués"}
    ]
    results = ai_filter.filter_profiles_batch(profiles, ["drone", "systèmes embarqués"])
    assert len(results) == 1
    assert "ai_score" in results[0]
    assert results[0]["ai_score"] >= 4
    assert "ai_reason" in results[0]


def test_ai_filter_location_guard():
    """Vérifie que les profils en France sont rejetés lorsque la zone demandée est le Maroc."""
    profiles = [
        {"first_name": "Yassine", "last_name": "Alaoui", "job_title": "Ingénieur Maintenance", "location": "Casablanca, Maroc"},
        {"first_name": "Anthony", "last_name": "Morel", "job_title": "Responsable Technique", "location": "Région de Paris, France"}
    ]

    # Filtrage avec Maroc demandé
    results_maroc = ai_filter._local_semantic_fallback(profiles, ["maintenance"], target_location="Maroc", min_score=4)
    assert len(results_maroc) == 1
    assert results_maroc[0]["first_name"] == "Yassine"
    assert not any(p["first_name"] == "Anthony" for p in results_maroc)


def test_ai_filter_engineering_acronyms_gnc():
    """Vérifie que les sigles techniques d'ingénierie (GNC, GMAO, PLC) sont reconnus."""
    profiles = [
        {"first_name": "Hamza", "last_name": "Idrissi", "job_title": "Ingénieur GNC & Guidage Autonome", "location": "Rabat, Maroc"},
        {"first_name": "Amina", "last_name": "Bennani", "job_title": "Responsable GMAO & Fiabilité", "location": "Casablanca, Maroc"},
        {"first_name": "Rachid", "last_name": "Tazi", "job_title": "Agent de sécurité", "location": "Tanger, Maroc"}
    ]

    # Recherche avec drone / guidage -> doit trouver Hamza (GNC)
    res_gnc = ai_filter._local_semantic_fallback(profiles, ["drone"], target_location="Maroc", min_score=3)
    assert any(p["first_name"] == "Hamza" for p in res_gnc)

    # Recherche avec maintenance -> doit trouver Amina (GMAO)
    res_gmao = ai_filter._local_semantic_fallback(profiles, ["maintenance"], target_location="Maroc", min_score=3)
    assert any(p["first_name"] == "Amina" for p in res_gmao)
    assert not any(p["first_name"] == "Rachid" for p in res_gmao)


def test_ai_filter_rh_synonym_expansion():
    """Vérifie que la recherche avec le mot-clé 'RH' retient Recruteur, Talent Acquisition, DRH, etc."""
    profiles = [
        {"first_name": "Sara", "last_name": "Chraibi", "job_title": "Chargée de recrutement & développement", "location": "Casablanca, Maroc"},
        {"first_name": "Nabil", "last_name": "Mansouri", "job_title": "Talent Acquisition Specialist", "location": "Rabat, Maroc"},
        {"first_name": "Khadija", "last_name": "Alami", "job_title": "Directrice des Ressources Humaines (DRH)", "location": "Tanger, Maroc"},
        {"first_name": "Tariq", "last_name": "Berrada", "job_title": "Recruteur Tech & IT", "location": "Casablanca, Maroc"},
        {"first_name": "Younes", "last_name": "Fassi", "job_title": "Chauffeur de direction", "location": "Casablanca, Maroc"}
    ]

    # Recherche avec le mot-clé exact "RH"
    res_rh = ai_filter._local_semantic_fallback(profiles, ["RH"], target_location="Maroc", min_score=3)
    
    first_names = [p["first_name"] for p in res_rh]
    assert "Sara" in first_names       # Chargée de recrutement
    assert "Nabil" in first_names      # Talent Acquisition
    assert "Khadija" in first_names    # DRH
    assert "Tariq" in first_names      # Recruteur Tech
    assert "Younes" not in first_names # Chauffeur exclu


def test_name_company_disambiguation_saber_vs_seaber():
    """Vérifie la dissociation stricte entre nom de personne et nom d'entreprise."""
    raw_title_homonym = "Karim Saber - Ingénieur chez OCP Group | LinkedIn"
    raw_snippet_homonym = "Ingénieur procédés chez OCP à Jorf Lasfar."
    name_candidate = "Karim Saber"
    first_name, last_name = "Karim", "Saber"
    company = "Seaber"

    # Vérification de l'isolation du texte
    full_text = f"{raw_title_homonym} {raw_snippet_homonym}".lower()
    text_without_person = full_text.replace(name_candidate.lower(), "").replace(first_name.lower(), "").replace(last_name.lower(), "")
    
    # "seaber" ne doit PAS être trouvé dans le texte sans le nom
    assert "seaber" not in text_without_person
    assert f"chez {company.lower()}" not in full_text