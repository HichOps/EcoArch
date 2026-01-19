import pytest
import json
from src.parser import EcoArchParser

@pytest.fixture
def mock_infracost_json(tmp_path):
    """Crée un fichier JSON factice pour tester le parser."""
    d = tmp_path / "test.json"
    content = {
        "totalMonthlyCost": "150.50",
        "pastTotalMonthlyCost": "100.00",
        "diffTotalMonthlyCost": "50.50",
        "currency": "USD",
        "projects": [{"breakdown": {"resources": []}}]
    }
    d.write_text(json.dumps(content))
    return str(d)

def test_extract_metrics(mock_infracost_json):
    parser = EcoArchParser(mock_infracost_json)
    metrics = parser.extract_metrics()
    
    assert metrics["total_monthly_cost"] == 150.50
    assert metrics["currency"] == "USD"
    assert metrics["diff_monthly_cost"] == 50.50