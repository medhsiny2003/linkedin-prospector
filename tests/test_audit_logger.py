"""
Tests unitaires pour le système de journalisation tamper-evident (SHA-256).
"""

import json
import os
import tempfile
from pathlib import Path
import pytest
from core.monitoring.audit_logger import AuditLogger


@pytest.fixture
def temp_logger():
    fd, log_path_str = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    log_path = Path(log_path_str)
    # Vider le fichier temporaire
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("")

    audit = AuditLogger(log_path=log_path)
    yield audit

    if log_path.exists():
        os.remove(log_path)


def test_genesis_block_and_chain(temp_logger):
    # Doit avoir créé le bloc genesis
    assert temp_logger.verify_integrity() is True

    # Ajouter 2 événements
    temp_logger.log_event("TEST_EVENT_1", "Premier test", {"val": 100})
    temp_logger.log_event("TEST_EVENT_2", "Second test", {"val": 200})

    assert temp_logger.verify_integrity() is True

    # Vérifier le contenu
    with open(temp_logger.log_path, "r", encoding="utf-8") as f:
        chain = json.load(f)
    assert len(chain) == 3
    assert chain[0]["event_type"] == "GENESIS"
    assert chain[1]["event_type"] == "TEST_EVENT_1"
    assert chain[2]["event_type"] == "TEST_EVENT_2"


def test_tampering_detection(temp_logger):
    temp_logger.log_event("NORMAL_EVENT", "Message d'origine")
    assert temp_logger.verify_integrity() is True

    # Falsification intentionnelle du fichier
    with open(temp_logger.log_path, "r", encoding="utf-8") as f:
        chain = json.load(f)

    # Modifier le message du bloc 1 sans recalculer le hash
    chain[1]["message"] = "Message falsifié par un attaquant"
    with open(temp_logger.log_path, "w", encoding="utf-8") as f:
        json.dump(chain, f)

    # L'intégrité doit échouer immédiatement
    assert temp_logger.verify_integrity() is False
