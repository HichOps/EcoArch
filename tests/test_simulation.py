"""Tests unitaires pour le module de simulation."""
import json
from subprocess import TimeoutExpired
from unittest.mock import Mock, patch, MagicMock

import pytest

from src.simulation import InfracostSimulator, SimulationResult
from src.config import Config


class TestSimulationResult:
    """Tests pour la dataclass SimulationResult."""
    
    def test_creation_success(self):
        """Test de création d'un SimulationResult réussi."""
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
        """Test de création d'un SimulationResult avec erreur."""
        result = SimulationResult(
            success=False,
            error_message="Test error",
        )
        
        assert result.success is False
        assert result.monthly_cost == 0.0
        assert result.error_message == "Test error"
    
    def test_default_values(self):
        """Test des valeurs par défaut."""
        result = SimulationResult(success=True)
        
        assert result.monthly_cost == 0.0
        assert result.details == {}
        assert result.error_message is None


class TestInfracostSimulator:
    """Tests pour la classe InfracostSimulator."""
    
    def test_init_with_defaults(self):
        """Test d'initialisation avec les valeurs par défaut."""
        simulator = InfracostSimulator()
        
        assert simulator.project_id == Config.GCP_PROJECT_ID
        assert simulator.timeout == Config.INFRACOST_TIMEOUT
    
    def test_init_with_custom_values(self):
        """Test d'initialisation avec des valeurs personnalisées."""
        simulator = InfracostSimulator(project_id="custom-project", timeout=60)
        
        assert simulator.project_id == "custom-project"
        assert simulator.timeout == 60
    
    def test_generate_terraform_code_compute(self):
        """Test de génération du code Terraform pour Compute."""
        simulator = InfracostSimulator()
        resources = [{
            "type": "compute",
            "machine_type": "e2-medium",
            "disk_size": 50,
        }]
        
        code = simulator._generate_terraform_code(resources, "test-deploy")
        
        assert "e2-medium" in code
        assert "size  = 50" in code
        assert "google_compute_instance" in code
        assert "test-deploy" in code
        assert Config.DEFAULT_IMAGE in code
    
    def test_generate_terraform_code_sql(self):
        """Test de génération du code Terraform pour SQL."""
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
    
    def test_generate_terraform_code_storage(self):
        """Test de génération du code Terraform pour Storage."""
        simulator = InfracostSimulator()
        resources = [{
            "type": "storage",
            "storage_class": "STANDARD",
        }]
        
        code = simulator._generate_terraform_code(resources, "test-deploy")
        
        assert "STANDARD" in code
        assert "google_storage_bucket" in code
    
    def test_generate_terraform_code_load_balancer(self):
        """Test de génération du code Terraform pour Load Balancer."""
        simulator = InfracostSimulator()
        resources = [{
            "type": "load_balancer",
        }]
        
        code = simulator._generate_terraform_code(resources, "test-deploy")
        
        assert "google_compute_global_address" in code
        assert "lb-ip-test-deploy" in code
    
    def test_simulate_empty_resources(self):
        """Test de simulation avec liste vide."""
        simulator = InfracostSimulator()
        result = simulator.simulate([])
        
        assert result.success is True
        assert result.monthly_cost == 0.0
        assert result.details == {}
    
    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_simulate_success(self, mock_tempdir, mock_run):
        """Test de simulation réussie."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps({
            "totalMonthlyCost": "42.75",
            "projects": [],
        })
        mock_run.return_value = mock_result
        
        simulator = InfracostSimulator()
        
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "compute"}])
        
        assert result.success is True
        assert result.monthly_cost == 42.75
    
    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_simulate_infracost_error(self, mock_tempdir, mock_run):
        """Test de simulation avec erreur Infracost (non bloquante)."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)
        
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = "Infracost error"
        mock_run.return_value = mock_result
        
        simulator = InfracostSimulator()
        
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "compute"}])
        
        assert result.success is True
        assert result.monthly_cost == 0.0
        assert "Warning" in result.error_message
    
    @patch("src.simulation.subprocess.run")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_simulate_timeout(self, mock_tempdir, mock_run):
        """Test de timeout lors de la simulation."""
        mock_tempdir.return_value.__enter__ = Mock(return_value="/tmp/test")
        mock_tempdir.return_value.__exit__ = Mock(return_value=False)
        
        mock_run.side_effect = TimeoutExpired(cmd="infracost", timeout=30)
        
        simulator = InfracostSimulator()
        
        with patch("pathlib.Path.write_text"):
            result = simulator.simulate([{"type": "compute"}])
        
        assert result.success is False
        assert "Timeout" in result.error_message


class TestDeployDestroy:
    """Tests pour les méthodes deploy et destroy."""
    
    @patch("src.simulation.subprocess.Popen")
    @patch("src.simulation.tempfile.TemporaryDirectory")
    def test_deploy_yields_logs(self, mock_tempdir, mock_popen):
        """Test que deploy yield des logs."""
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
