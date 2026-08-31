"""
Tests unitaires pour les parseurs de données DOM et de chaînes.
"""

from scrapers.parsers.dom_parser import dom_parser


def test_parse_french_full_names():
    # Cas avec titres et diplômes
    f, l = dom_parser.parse_full_name("Dr. Jean-Baptiste Poquelin, PhD")
    assert f == "Jean-Baptiste"
    assert l == "Poquelin"

    # Cas avec mentions de niveau de connexion LinkedIn
    f, l = dom_parser.parse_full_name("Marie Curie • 1er")
    assert f == "Marie"
    assert l == "Curie"

    # Cas standard
    f, l = dom_parser.parse_full_name("Alexandre Dumas")
    assert f == "Alexandre"
    assert l == "Dumas"


def test_parse_moroccan_full_names():
    # Cas nom avec particule El
    f, l = dom_parser.parse_full_name("Amine El Amrani")
    assert f == "Amine"
    assert l == "El Amrani"

    # Cas nom avec particule Ben
    f, l = dom_parser.parse_full_name("Mehdi Benjelloun")
    assert f == "Mehdi"
    assert l == "Benjelloun"

    # Cas nom avec particule Ait
    f, l = dom_parser.parse_full_name("Youssef Ait Ali")
    assert f == "Youssef"
    assert l == "Ait Ali"

    # Cas prénom composé et particule
    f, l = dom_parser.parse_full_name("Fatima Zahra Bennani")
    assert f == "Fatima Zahra"
    assert l == "Bennani"

    # Cas rejet ville / région marocaine
    f, l = dom_parser.parse_full_name("Casablanca Maroc")
    assert f == ""
    assert l == ""

    f, l = dom_parser.parse_full_name("Nouaceur Midparc • 3e")
    assert f == ""
    assert l == ""


def test_clean_job_and_company():
    job, comp = dom_parser.clean_job_and_company("Responsable Recrutement chez Thales")
    assert job == "Responsable Recrutement"
    assert comp == "Thales"

    job, comp = dom_parser.clean_job_and_company("Chef de projet Drones | Airbus")
    assert job == "Chef de projet Drones"
    assert comp == "Airbus"

    job, comp = dom_parser.clean_job_and_company("Ingénieur R&D Systèmes Embarqués chez Safran Maroc")
    assert job == "Ingénieur R&D Systèmes Embarqués"
    assert comp == "Safran Maroc"

