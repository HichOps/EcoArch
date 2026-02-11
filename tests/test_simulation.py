"""Tests unitaires pour le module de simulation.

Couvre:
- Génération de code Terraform (compute, sql, load_balancer, vide)
- Parsing des coûts via Infracost (mock subprocess)
- Gestion des erreurs (JSON malformé, timeouts, stderr)
"""
import json
from subprocess import TimeoutExpired
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.simulation import InfracostSimulator, SimulationResult, fallback_estimate
from src.config import Config


# ============================================================
# Fallback cost estimator
# ============================================================

class TestFallbackEstimate:
    """Tests pour l'estimateur de coûts hors-ligne."""

    def test_empty_resources_returns_zero(self):
        result = fallback_estimate([])
        assert result.success is True
        assert result.monthly_cost == 0.0

    def test_compute_e2_medium_cost(self):
        result = fallback_estimate([{"type": "compute", "machine_type": "e2-medium", "disk_size": 50}])
        assert result.success is True
        # 29.38 (VM) + 50 * 0.04 (disk) = 31.38
        assert result.monthly_cost == 31.38

    def test_sql_cost(self):
        result = fallback_estimate([{"type": "sql", "db_tier": "db-g1-small"}])
        assert result.success is True
        assert result.monthly_cost == 25.55

    def test_storage_cost(self):
        result = fallback_estimate([{"type": "storage", "storage_class": "COLDLINE"}])
        assert result.success is True
        assert result.monthly_cost == 0.70

    def test_load_balancer_cost(self):
        result = fallback_estimate([{"type": "load_balancer"}])
        assert result.success is True
        assert result.monthly_cost == 18.26

    def test_mixed_resources_sum(self):
        resources = [
            {"type": "compute", "machine_type": "e2-micro", "disk_size": 10},
            {"type": "sql", "db_tier": "db-f1-micro"},
            {"type": "storage", "storage_class": "STANDARD"},
        ]
        result = fallback_estimate(resources)
        # 7.12 + 10*0.04 + 7.67 + 2.60 = 17.79
        assert result.success is True
        assert result.monthly_cost == 17.79

    def test_details_contain_source_fallback(self):
        result = fallback_estimate([{"type": "compute"}])
        assert result.details["_source"] == "fallback"

    def test_details_contain_projects_breakdown(self):
        result = fallback_estimate([{"type": "compute", "display_name": "VM Test"}])
        projects = result.details["projects"]
        assert len(projects) == 1
        resources = projects[0]["breakdown"]["resources"]
        assert len(resources) == 1
        assert resources[0]["name"] == "VM Test"

    def test_unknown_machine_type_uses_default(self):
        """Type de machine inconnu → utilise le prix e2-medium par défaut."""
        result = fallback_estimate([{"type": "compute", "machine_type": "unknown-type", "disk_size": 0}])
        assert result.success is True
        assert result.monthly_cost == 29.38  # default e2-medium

    def test_unknown_db_tier_uses_default(self):
        result = fallback_estimate([{"type": "sql", "db_tier": "unknown-tier"}])
        assert result.success is True
        assert result.monthly_cost == 7.67  # default db-f1-micro


# ============================================================
# SimulationResult dataclass
# ============================================================

class TestSimulationResult:
    """Tests pour la dataclass SimulationResult."""

    def test_creation_success(self):
        result = SimulationResult(
            success=True,
            monthly_cost=50.0,
            details={"key": "value"},
        )
        assert result.success is True
        assert result.monthly_cost == 50.0
        assert result.details == {"key": "value"}
        assert result.error_message is None

    def test_creation_with_error(self):
        result = SimulationResult(
            success=False,
            error_message="Test error",
        )
        assert result.success is False
        assert result.monthly_cost == 0.0
        assert result.error_message == "Test error"

    def test_default_values(self):
        result = SimulationResult(success=True)
        assert result.monthly_cost == 0.0
        assert result.details == {}
        assert result.error_message is None


# ============================================================
# Terraform Code Generation (_generate_terraform_code)
# ============================================================

class TestTerraformCodeGeneration:
    """Tests pour la génération de code HCL."""

    def test_compute_resource_fields(self):
        """Vérifie que le HCL contient les blocs compute et les valeurs sont dans tfvars."""
        simulator = InfracostSimulator()
        resources = [{
            "type": "compute",
            "machine_type": "e2-medium",
            "disk_size": 50,
        }]
        code = simulator._generate_terraform_code(resources, "test-deploy")

        # Structure HCL
        assert "google_compute_instance" in code
        # Valeurs dans le tfvars JSON
        assert "e2-medium" in code
        assert "test-deploy" in code
        # Sécurité : les valeurs passent par des variables Terraform
        assert "var.deployment_id" in code or "test-deploy" in code

    def test_sql_resource_fields(self):
        """Vérifie db_version et tier dans le HCL SQL."""
        simulator = InfracostSimulator()
        resources = [{
            "type": "sql",
            "db_tier": "db-f1-micro",
            "db_version": "POSTGRES_14",
        }]
        code = simulator._generate_terraform_code(resources, "test-deploy")

        assert "db-f1-micro" in code
        assert "POSTGRES_14" in code
        assert "google_sql_database_instance" in code
        assert "deletion_protection = false" in code

    def test_load_balancer_static_ip(self):
        """Vérifie la génération d'IP statique pour le load balancer (fix V10)."""
        simulator = InfracostSimulator()
        resources = [{"type": "load_balancer"}]
        code = simulator._generate_terraform_code(resources, "test-deploy")

        assert "google_compute_global_address" in code
        # Le deployment_id apparaît dans le tfvars
        assert "test-deploy" in code

    def test_empty_resources_returns_valid_terraform(self):
        """Une liste vide doit renvoyer un bloc Terraform valide avec counts à 0."""
        simulator = InfracostSimulator()
        code = simulator._generate_terraform_code([], "empty-deploy")

        assert 'provider "google"' in code
        # Avec l'architecture tfvars, le HCL est statique, les counts sont à 0
        assert '"compute_instances": []' in code
        assert '"sql_instances": []' in code
        assert '"storage_buckets": []' in code
        assert '"lb_count": 0' in code

    def test_include_backend_false_skips_gcs_state(self):
        """Avec include_backend=False, pas de backend GCS."""
        simulator = InfracostSimulator()
        code = simulator._generate_terraform_code(
            [{"type": "compute"}], "sim", include_backend=False,
        )
        assert "backend" not in code
        assert "required_providers" in code

    def test_include_backend_true_has_gcs_state(self):
        """Avec include_backend=True, le backend GCS est présent."""
        simulator = InfracostSimulator()
        code = simulator._generate_terraform_code(
            [{"type": "compute"}], "prod-deploy", include_backend=True,
        )
        assert 'backend "gcs"' in code
        assert Config.TERRAFORM_STATE_BUCKET in code

    def test_multiple_resources_all_present(self):
        """Plusieurs ressources mixtes apparaissent toutes dans le HCL."""
        simulator = InfracostSimulator()
        resources = [
            {"type": "compute", "machine_type": "n2-standard-2", "disk_size": 100},
            {"type": "sql", "db_tier": "db-g1-small", "db_version": "POSTGRES_15"},
            {"type": "storage", "storage_class": "NEARLINE"},
            {"type": "load_balancer"},
        ]
        code = simulator._generate_terraform_code(resources, "multi-test")

        assert "google_compute_instance" in code
        assert "google_sql_database_instance" in code
        assert "google_storage_bucket" in code
        assert "google_compute_global_address" in code

    def test_unknown_resource_type_rejected(self):
        """Un type de ressource inconnu lève ValidationError (CRIT-1 sécurité)."""
        from src.security import ValidationError
        simulator = InfracostSimulator()
        resources = [{"type": "unknown_thing"}]
        with pytest.raises(ValidationError, match="type non autorisé"):
            simulator._generate_terraform_code(resources, "test")


# ============================================================
# Cost Simulation (simulate) – mocked subprocess
# ============================================================

class TestSimulate:
    """Tests pour la méthode simulate (coûts Infracost)."""

    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_parse_valid_json_float_precision(self, mock_tempdir, mock_run):
        """Parse JSON valide et vérifie la précision float du coût."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "totalMonthlyCost": "42.756789",
            "projects": [],
        })
        mock_run.return_value = mock_result

        simulator = InfracostSimulator()
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "compute"}])

        assert result.success is True
        assert result.monthly_cost == pytest.approx(42.756789)

    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_malformed_json_returns_fallback(self, mock_tempdir, mock_run):
        """JSON malformé → fallback estimation, pas de crash."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "NOT VALID JSON {{{["
        mock_run.return_value = mock_result

        simulator = InfracostSimulator()
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "compute"}])

        assert result.success is True
        assert result.monthly_cost > 0
        assert result.details.get("_source") == "fallback"

    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_subprocess_error_returns_fallback(self, mock_tempdir, mock_run):
        """Erreur subprocess (returncode != 0) → fallback estimation."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)

        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Infracost API key invalid"
        mock_run.return_value = mock_result

        simulator = InfracostSimulator()
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "compute"}])

        assert result.success is True
        assert result.monthly_cost > 0
        assert result.details.get("_source") == "fallback"

    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_timeout_returns_fallback(self, mock_tempdir, mock_run):
        """Timeout subprocess → fallback estimation au lieu d'erreur."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)

        mock_run.side_effect = TimeoutExpired(cmd="infracost", timeout=30)

        simulator = InfracostSimulator()
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "compute"}])

        assert result.success is True
        assert result.monthly_cost > 0
        assert result.details.get("_source") == "fallback"

    def test_simulate_empty_resources(self):
        """Liste vide → success=True, coût 0, pas d'appel subprocess."""
        simulator = InfracostSimulator()
        result = simulator.simulate([])

        assert result.success is True
        assert result.monthly_cost == 0.0
        assert result.details == {}

    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_simulate_captures_full_details(self, mock_tempdir, mock_run):
        """Vérifie que le dict details contient l'intégralité de la réponse Infracost."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)

        infracost_payload = {
            "totalMonthlyCost": "100.00",
            "projects": [{"name": "sim", "breakdown": {"resources": []}}],
            "currency": "USD",
        }
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(infracost_payload)
        mock_run.return_value = mock_result

        simulator = InfracostSimulator()
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "sql"}])

        assert result.details["currency"] == "USD"
        assert result.details["projects"][0]["name"] == "sim"


# ============================================================
# Init & Configuration
# ============================================================

class TestInfracostSimulatorInit:
    """Tests d'initialisation du simulateur."""

    def test_init_with_defaults(self):
        simulator = InfracostSimulator()
        assert simulator.project_id == Config.GCP_PROJECT_ID
        assert simulator.timeout == Config.INFRACOST_TIMEOUT

    def test_init_with_custom_values(self):
        simulator = InfracostSimulator(project_id="custom-project", timeout=60)
        assert simulator.project_id == "custom-project"
        assert simulator.timeout == 60


# ============================================================
# Deploy / Destroy (streaming)
# ============================================================

class TestDeployDestroy:
    """Tests pour les méthodes deploy et destroy."""

    @patch("src.simulation.subprocess.Popen")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_deploy_yields_logs(self, mock_tempdir, mock_popen):
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)

        mock_process = MagicMock()
        mock_process.stdout = iter(["init output", "apply output"])
        mock_process.wait.return_value = None
        mock_process.returncode = 0
        mock_popen.return_value = mock_process

        simulator = InfracostSimulator()
        with patch("pathlib.Path.write_text"):
            logs = list(simulator.deploy([{"type": "compute"}], "test-id"))

        assert len(logs) > 0
        assert any("test-id" in log for log in logs)
