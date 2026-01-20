"""
Module de simulation de coûts infrastructure avec Infracost.
Logique métier pure, testable indépendamment de l'UI.
"""
import subprocess
import json
import tempfile
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

# On importe uniquement la config, pas "run_simulation" !
from .config import Config, GCPConfig

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Résultat d'une simulation de coût."""
    monthly_cost: float
    details: Dict[str, Any]
    success: bool = True
    error_message: Optional[str] = None


class InfracostSimulator:
    """Simulateur de coûts infrastructure utilisant Infracost."""
    
    def __init__(self, project_id: Optional[str] = None, timeout: Optional[int] = None):
        self.project_id = project_id or Config.GCP_PROJECT_ID
        self.timeout = timeout or Config.INFRACOST_TIMEOUT
    
    def generate_terraform_code(self, instance_type: str, region: str, storage_size: int) -> str:
        return f"""
provider "google" {{
  project = "{self.project_id}"
  region  = "{region}"
}}

resource "google_compute_instance" "simulated_vm" {{
  name         = "simulation-vm"
  machine_type = "{instance_type}"
  zone         = "{region}-a"
  
  boot_disk {{
    initialize_params {{
      image = "{Config.DEFAULT_IMAGE}"
      size  = {storage_size}
    }}
  }}
  
  network_interface {{
    network = "default"
  }}
}}
"""
    
    def run_infracost(self, target_path: Path) -> Dict[str, Any]:
        result = subprocess.run(
            ["infracost", "breakdown", "--path", str(target_path), "--format", "json"],
            capture_output=True,
            text=True,
            timeout=self.timeout,
            check=True
        )
        return json.loads(result.stdout)
    
    def simulate(self, instance_type: str, region: str, storage_size: int) -> SimulationResult:
        # Validation
        if instance_type not in GCPConfig.INSTANCE_TYPES:
            logger.warning(f"Type d'instance non reconnu: {instance_type}")
        
        if region not in GCPConfig.REGIONS:
            logger.warning(f"Région non reconnue: {region}")
        
        if not (GCPConfig.MIN_STORAGE_GB <= storage_size <= GCPConfig.MAX_STORAGE_GB):
            return SimulationResult(
                monthly_cost=0.0,
                details={},
                success=False,
                error_message=f"Stockage doit être entre {GCPConfig.MIN_STORAGE_GB} et {GCPConfig.MAX_STORAGE_GB} GB"
            )
        
        # Exécution
        try:
            with tempfile.TemporaryDirectory(prefix=Config.TEMP_FILE_PREFIX) as tmpdirname:
                tf_file_path = Path(tmpdirname) / "main.tf"
                
                tf_code = self.generate_terraform_code(instance_type, region, storage_size)
                with open(tf_file_path, "w") as f:
                    f.write(tf_code)
                
                logger.info(f"Environnement Terraform créé dans: {tmpdirname}")
                
                data = self.run_infracost(Path(tmpdirname))
                monthly_cost = float(data.get('totalMonthlyCost', 0.0))
                
                # Check erreur silencieuse
                if monthly_cost == 0.0 and data.get('projects'):
                    metadata = data['projects'][0].get('metadata', {})
                    if metadata.get('errors'):
                        raise Exception(f"Infracost Error: {metadata['errors'][0].get('message')}")

                return SimulationResult(monthly_cost=monthly_cost, details=data, success=True)

        except subprocess.TimeoutExpired:
            return SimulationResult(monthly_cost=0.0, details={}, success=False, error_message=f"Timeout ({self.timeout}s)")
        except subprocess.CalledProcessError as e:
            return SimulationResult(monthly_cost=0.0, details={}, success=False, error_message=f"Erreur CLI: {e.stderr}")
        except Exception as e:
            logger.exception("Erreur inattendue")
            return SimulationResult(monthly_cost=0.0, details={}, success=False, error_message=str(e))


def run_simulation(instance_type: str, region: str, storage_size: int) -> Tuple[Optional[float], Any]:
    """
    Fonction utilitaire pour compatibilité avec le code existant.
    """
    simulator = InfracostSimulator()
    result = simulator.simulate(instance_type, region, storage_size)
    
    if result.success:
        return result.monthly_cost, result.details
    else:
        return None, result.error_message