import subprocess
import json
import tempfile
import logging
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SimulationResult:
    success: bool
    monthly_cost: float = 0.0
    details: Dict[str, Any] = None
    error_message: Optional[str] = None

class InfracostSimulator:
    def __init__(self, project_id: Optional[str] = None, timeout: Optional[int] = None):
        self.project_id = project_id or Config.GCP_PROJECT_ID
        self.timeout = timeout or Config.INFRACOST_TIMEOUT
    
    def _generate_terraform_code(self, resources: List[Dict[str, Any]]) -> str:
        tf_code = f"""
        provider "google" {{
          project = "{self.project_id}"
          region  = "{Config.DEFAULT_REGION}"
        }}
        """
        
        for idx, res in enumerate(resources):
            r_type = res.get("type", "compute")
            name = f"res_{idx}_{r_type}"
            
            # --- CAS 1 : COMPUTE ENGINE (VM) ---
            if r_type == "compute":
                machine = res.get("machine_type", "e2-medium")
                disk = res.get("disk_size", 50)
                zone = f"{Config.DEFAULT_REGION}-a"
                
                tf_code += f"""
                resource "google_compute_instance" "{name}" {{
                  name         = "{name}"
                  machine_type = "{machine}"
                  zone         = "{zone}"
                  boot_disk {{
                    initialize_params {{
                      image = "{Config.DEFAULT_IMAGE}"
                      size  = {disk}
                    }}
                  }}
                  network_interface {{ network = "default" }}
                }}
                """

            # --- CAS 2 : CLOUD SQL (DATABASE) ---
            elif r_type == "sql":
                tier = res.get("db_tier", "db-f1-micro")
                version = res.get("db_version", "POSTGRES_14")
                
                tf_code += f"""
                resource "google_sql_database_instance" "{name}" {{
                  name             = "{name}"
                  database_version = "{version}"
                  region           = "{Config.DEFAULT_REGION}"
                  settings {{
                    tier = "{tier}"
                  }}
                  deletion_protection = false
                }}
                """

            # --- CAS 3 : CLOUD STORAGE (NOUVEAU) ---
            elif r_type == "storage":
                storage_class = res.get("storage_class", "STANDARD")
                # On convertit le nom pour qu'il soit valide (minuscules, pas d'underscore)
                safe_name = name.replace("_", "-").lower()
                
                tf_code += f"""
                resource "google_storage_bucket" "{name}" {{
                  name          = "{safe_name}"
                  location      = "{Config.DEFAULT_REGION}"
                  storage_class = "{storage_class}"
                  force_destroy = true
                }}
                """
            
        return tf_code
    
    def simulate(self, resources: List[Dict[str, Any]]) -> SimulationResult:
        if not resources:
            return SimulationResult(success=True, monthly_cost=0.0, details={})

        try:
            with tempfile.TemporaryDirectory(prefix=Config.TEMP_FILE_PREFIX) as tmpdirname:
                tf_path = Path(tmpdirname) / "main.tf"
                with open(tf_path, "w") as f:
                    f.write(self._generate_terraform_code(resources))
                
                cmd = ["infracost", "breakdown", "--path", str(tmpdirname), "--format", "json", "--log-level", "info"]
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, env=os.environ)

                if process.returncode != 0:
                    return SimulationResult(success=False, error_message=f"Erreur CLI: {process.stderr}")

                try:
                    data = json.loads(process.stdout)
                    total_cost = float(data.get("totalMonthlyCost", 0.0))
                    return SimulationResult(success=True, monthly_cost=total_cost, details=data)
                except json.JSONDecodeError:
                     return SimulationResult(success=False, error_message="Réponse Infracost invalide")

        except subprocess.TimeoutExpired:
            return SimulationResult(success=False, error_message=f"Timeout Infracost ({self.timeout}s)")
        except Exception as e:
            return SimulationResult(success=False, error_message=str(e))