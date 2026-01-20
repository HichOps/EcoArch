"""
Tests unitaires pour le module de simulation.
"""
import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from src.simulation import InfracostSimulator, SimulationResult, run_simulation
from src.config import Config, GCPConfig


class TestInfracostSimulator:
    """Tests pour la classe InfracostSimulator."""
    
    def test_generate_terraform_code(self):
        """Test de génération du code Terraform."""
        simulator = InfracostSimulator()
        code = simulator.generate_terraform_code("e2-medium", "europe-west1", 20)
        
        assert "e2-medium" in code
        assert "europe-west1" in code
        assert "size  = 20" in code
        assert Config.DEFAULT_IMAGE in code
        assert simulator.project_id in code
    
    def test_init_with_custom_values(self):
        """Test d'initialisation avec des valeurs personnalisées."""
        simulator = InfracostSimulator(project_id="custom-project", timeout=60)
        
        assert simulator.project_id == "custom-project"
        assert simulator.timeout == 60
    
    def test_init_with_defaults(self):
        """Test d'initialisation avec les valeurs par défaut."""
        simulator = InfracostSimulator()
        
        assert simulator.project_id == Config.GCP_PROJECT_ID
        assert simulator.timeout == Config.INFRACOST_TIMEOUT
    
    @patch('src.simulation.subprocess.run')
    def test_run_infracost_success(self, mock_run):
        """Test d'exécution réussie d'Infracost."""
        # Mock de la réponse
        mock_result = Mock()
        mock_result.stdout = json.dumps({"totalMonthlyCost": "25.50"})
        mock_run.return_value = mock_result
        
        simulator = InfracostSimulator()
        tf_file = Path("/tmp/test.tf")
        
        result = simulator.run_infracost(tf_file)
        
        assert result["totalMonthlyCost"] == "25.50"
        mock_run.assert_called_once()
        
        # Vérification des arguments
        call_args = mock_run.call_args
        assert call_args.kwargs['timeout'] == simulator.timeout
        assert call_args.kwargs['check'] is True
    
    @patch('src.simulation.subprocess.run')
    @patch('src.simulation.tempfile.NamedTemporaryFile')
    @patch('src.simulation.Path.exists')
    @patch('src.simulation.Path.unlink')
    def test_simulate_success(self, mock_unlink, mock_exists, mock_tempfile, mock_run):
        """Test de simulation complète réussie."""
        # Mock du fichier temporaire
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_sim.tf"
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_tempfile.return_value = mock_file
        
        # Mock de la réponse Infracost
        mock_result = Mock()
        mock_result.stdout = json.dumps({
            "totalMonthlyCost": "42.75",
            "projects": []
        })
        mock_run.return_value = mock_result
        
        # Mock du nettoyage
        mock_exists.return_value = True
        
        simulator = InfracostSimulator()
        result = simulator.simulate("e2-medium", "europe-west1", 20)
        
        assert result.success is True
        assert result.monthly_cost == 42.75
        assert result.error_message is None
        assert "totalMonthlyCost" in result.details
        
        # Vérification du nettoyage
        mock_unlink.assert_called_once()
    
    @patch('src.simulation.subprocess.run')
    @patch('src.simulation.tempfile.NamedTemporaryFile')
    def test_simulate_invalid_storage(self, mock_tempfile, mock_run):
        """Test avec stockage invalide."""
        simulator = InfracostSimulator()
        
        # Stockage trop grand
        result = simulator.simulate("e2-medium", "europe-west1", 5000)
        
        assert result.success is False
        assert "Stockage doit être entre" in result.error_message
        assert result.monthly_cost == 0.0
        
        # Vérifier qu'aucun fichier temporaire n'a été créé
        mock_tempfile.assert_not_called()
    
    @patch('src.simulation.subprocess.run')
    @patch('src.simulation.tempfile.NamedTemporaryFile')
    @patch('src.simulation.Path.exists')
    @patch('src.simulation.Path.unlink')
    def test_simulate_timeout(self, mock_unlink, mock_exists, mock_tempfile, mock_run):
        """Test de timeout lors de l'exécution."""
        # Mock du fichier temporaire
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_timeout.tf"
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_tempfile.return_value = mock_file
        
        # Simuler un timeout
        from subprocess import TimeoutExpired
        mock_run.side_effect = TimeoutExpired(cmd="infracost", timeout=30)
        
        mock_exists.return_value = True
        
        simulator = InfracostSimulator()
        result = simulator.simulate("e2-medium", "europe-west1", 20)
        
        assert result.success is False
        assert "Timeout" in result.error_message
        assert result.monthly_cost == 0.0
        
        # Vérification du nettoyage même en cas d'erreur
        mock_unlink.assert_called_once()
    
    @patch('src.simulation.subprocess.run')
    @patch('src.simulation.tempfile.NamedTemporaryFile')
    @patch('src.simulation.Path.exists')
    @patch('src.simulation.Path.unlink')
    def test_simulate_json_error(self, mock_unlink, mock_exists, mock_tempfile, mock_run):
        """Test avec réponse JSON invalide."""
        # Mock du fichier temporaire
        mock_file = MagicMock()
        mock_file.name = "/tmp/test_json.tf"
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_tempfile.return_value = mock_file
        
        # Réponse non-JSON
        mock_result = Mock()
        mock_result.stdout = "Not a JSON response"
        mock_run.return_value = mock_result
        
        mock_exists.return_value = True
        
        simulator = InfracostSimulator()
        result = simulator.simulate("e2-medium", "europe-west1", 20)
        
        assert result.success is False
        assert "Réponse Infracost invalide" in result.error_message
        
        # Nettoyage doit quand même avoir lieu
        mock_unlink.assert_called_once()


class TestRunSimulation:
    """Tests pour la fonction utilitaire run_simulation."""
    
    @patch('src.simulation.InfracostSimulator')
    def test_run_simulation_success(self, mock_simulator_class):
        """Test de la fonction wrapper avec succès."""
        # Mock du simulateur
        mock_simulator = Mock()
        mock_simulator.simulate.return_value = SimulationResult(
            monthly_cost=35.20,
            details={"test": "data"},
            success=True
        )
        mock_simulator_class.return_value = mock_simulator
        
        cost, details = run_simulation("e2-medium", "europe-west1", 20)
        
        assert cost == 35.20
        assert details == {"test": "data"}
    
    @patch('src.simulation.InfracostSimulator')
    def test_run_simulation_failure(self, mock_simulator_class):
        """Test de la fonction wrapper avec échec."""
        # Mock du simulateur
        mock_simulator = Mock()
        mock_simulator.simulate.return_value = SimulationResult(
            monthly_cost=0.0,
            details={},
            success=False,
            error_message="Test error"
        )
        mock_simulator_class.return_value = mock_simulator
        
        cost, error = run_simulation("e2-medium", "europe-west1", 20)
        
        assert cost is None
        assert error == "Test error"


class TestSimulationResult:
    """Tests pour la dataclass SimulationResult."""
    
    def test_simulation_result_creation(self):
        """Test de création d'un SimulationResult."""
        result = SimulationResult(
            monthly_cost=50.0,
            details={"key": "value"}
        )
        
        assert result.monthly_cost == 50.0
        assert result.details == {"key": "value"}
        assert result.success is True
        assert result.error_message is None
    
    def test_simulation_result_with_error(self):
        """Test de création d'un SimulationResult avec erreur."""
        result = SimulationResult(
            monthly_cost=0.0,
            details={},
            success=False,
            error_message="An error occurred"
        )
        
        assert result.success is False
        assert result.error_message == "An error occurred"
