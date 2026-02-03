"""Tests unitaires pour le parser Infracost."""
import json

import pytest

from src.parser import EcoArchParser


@pytest.fixture
def mock_infracost_json(tmp_path):
    """Crée un fichier JSON factice pour tester le parser."""
    json_file = tmp_path / "test.json"
    content = {
        "totalMonthlyCost": "150.50",
        "pastTotalMonthlyCost": "100.00",
        "diffTotalMonthlyCost": "50.50",
        "currency": "USD",
        "projects": [{"breakdown": {"resources": []}}],
    }
    json_file.write_text(json.dumps(content))
    return str(json_file)


def test_extract_metrics(mock_infracost_json):
    """Test de l'extraction des métriques principales."""
    parser = EcoArchParser(mock_infracost_json)
    metrics = parser.extract_metrics()
    
    assert metrics["total_monthly_cost"] == 150.50
    assert metrics["currency"] == "USD"
    assert metrics["diff_monthly_cost"] == 50.50


def test_file_not_found():
    """Test avec un fichier inexistant."""
    parser = EcoArchParser("nonexistent.json")
    
    assert parser.data == {}
    assert parser.resources == []


def test_safe_float():
    """Test de la conversion sécurisée en float."""
    assert EcoArchParser._safe_float(None) == 0.0
    assert EcoArchParser._safe_float("42.5") == 42.5
    assert EcoArchParser._safe_float("invalid") == 0.0
    assert EcoArchParser._safe_float(100) == 100.0