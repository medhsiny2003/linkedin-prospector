"""
Tests unitaires pour le validateur d'emails (Syntaxe + MX DNS + SMTP Handshake).
"""

from unittest.mock import MagicMock, patch
import pytest
from enricher.email_validator import EmailValidator


@pytest.fixture
def validator():
    return EmailValidator()


def test_syntax_valid(validator):
    assert validator.validate_syntax("contact@thalesgroup.com") is True
    assert validator.validate_syntax("jean.dupont-ext@airbus.com") is True
    assert validator.validate_syntax("invalid-email") is False
    assert validator.validate_syntax("missing@domain") is False


def test_mx_check_mocked(validator):
    with patch("dns.resolver.resolve") as mock_resolve:
        mock_resolve.return_value = [MagicMock(preference=10, exchange="mx.thalesgroup.com")]
        has_mx, is_ca, pmx, msg = validator.check_mx_record("thalesgroup.com")
        assert has_mx is True
        assert is_ca is False
        assert pmx == "mx.thalesgroup.com"
        assert "trouvé" in msg


def test_validation_pipeline_mocked(validator):
    with patch.object(validator, "check_mx_record", return_value=(True, False, "mx.thalesgroup.com", "MX OK")):
        with patch.object(validator, "verify_smtp_handshake", return_value=(None, "Port 25 inaccessible")):
            res = validator.validate("test@thalesgroup.com")
            assert "Validé" in res["status"]
            assert res["mx_verified"] == "Oui"

    with patch.object(validator, "check_mx_record", return_value=(False, False, "", "Aucun MX")):
        res = validator.validate("test@invalidfake12345.com")
        assert res["status"] == "Non vérifiable"
        assert res["mx_verified"] == "Non"
