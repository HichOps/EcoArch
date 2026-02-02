import subprocess
import json
import tempfile
import logging
import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Generator
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
    
    def _generate_terraform_code(self, resources: List[Dict[str, Any]], deployment_id: str = "simulation") -> str:
        # 1. ISOLATION : Le prefix du backend dépend maintenant de l'ID unique !
        state_prefix = f"terraform/state/{deployment_id}"

        tf_code = f"""
        terraform {{
          backend "gcs" {{
            bucket  = "{Config.TERRAFORM_STATE_BUCKET}"
            prefix  = "{state_prefix}"
          }}
        }}

        provider "google" {{
          project = "{self.project_id}"
          region  = "{Config.DEFAULT_REGION}"
        }}
        """
        
        for idx, res in enumerate(resources):
            r_type = res.get("type", "compute")
            # Nom interne Terraform
            name = f"res-{idx}-{r_type}"
            
            # --- CAS 1 : COMPUTE ENGINE (VM) ---
            if r_type == "compute":
                machine = res.get("machine_type", "e2-medium")
                disk = res.get("disk_size", 50)
                zone = f"{Config.DEFAULT_REGION}-a"
                
                # Nom réel GCP avec l'ID pour éviter les conflits
                gcp_name = f"{name}-{deployment_id}"

                tf_code += f"""
                resource "google_compute_instance" "{name}" {{
                  name         = "{gcp_name}" 
                  machine_type = "{machine}"
                  zone         = "{zone}"
                  boot_disk {{
                    initialize_params {{
                      image = "{Config.DEFAULT_IMAGE}"
                      size  = {disk}
                    }}
                  }}
                  network_interface {{ network = "default" }}
                  labels = {{
                    deployment_id = "{deployment_id}"
                    managed_by = "ecoarch-app"
                  }}
                }}
                """

            # --- CAS 2 : CLOUD SQL (DATABASE) ---
            elif r_type == "sql":
                tier = res.get("db_tier", "db-f1-micro")
                version = res.get("db_version", "POSTGRES_14")
                gcp_name = f"{name}-{deployment_id}"
                
                tf_code += f"""
                resource "google_sql_database_instance" "{name}" {{
                  name             = "{gcp_name}"
                  database_version = "{version}"
                  region           = "{Config.DEFAULT_REGION}"
                  settings {{
                    tier = "{tier}"
                  }}
                  deletion_protection = false
                }}
                """

            # --- CAS 3 : CLOUD STORAGE ---
            elif r_type == "storage":
                storage_class = res.get("storage_class", "STANDARD")
                # Bucket doit être en minuscules et unique mondialement
                safe_name = f"{self.project_id}-{name}-{deployment_id}".lower()
                
                tf_code += f"""
                resource "google_storage_bucket" "{name}" {{
                  name          = "{safe_name}"
                  location      = "{Config.DEFAULT_REGION}"
                  storage_class = "{storage_class}"
                  force_destroy = true
                }}
                """

            # --- NOUVEAU BLOC : LOAD BALANCER ---
            elif r_type == "load_balancer":
                # On simule un Global Forwarding Rule (HTTP LB classique)
                tf_code += f"""
                resource "google_compute_global_forwarding_rule" "{name}" {{
                  name       = "{name}-{deployment_id}"
                  target     = "default-target-http-proxy" # Simplifié pour le coût
                  port_range = "80"
                  labels = {{
                    deployment_id = "{deployment_id}"
                  }}
                }}
                """

        return tf_code
    
    def simulate(self, resources: List[Dict[str, Any]]) -> SimulationResult:
        if not resources:
            return SimulationResult(success=True, monthly_cost=0.0, details={})

        try:
            with tempfile.TemporaryDirectory(prefix=Config.TEMP_FILE_PREFIX) as tmpdirname:
                tf_path = Path(tmpdirname) / "main.tf"
                # Pour la simulation de coût, l'ID importe peu, on met "simulation_tmp"
                with open(tf_path, "w") as f:
                    f.write(self._generate_terraform_code(resources, deployment_id="simulation_tmp"))
                
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

        except Exception as e:
            return SimulationResult(success=False, error_message=str(e))

    # --- DEPLOIEMENT ISOLE ---
    def deploy(self, resources: List[Dict[str, Any]], deployment_id: str) -> Generator[str, None, None]:
        if not resources:
            yield "❌ Erreur : Aucune ressource à déployer."
            return

        with tempfile.TemporaryDirectory(prefix=f"ecoarch_{deployment_id}_") as tmpdirname:
            tf_path = Path(tmpdirname) / "main.tf"
            
            yield f"📝 ID de déploiement unique : {deployment_id}"
            with open(tf_path, "w") as f:
                f.write(self._generate_terraform_code(resources, deployment_id))
            
            yield "⚙️ Isolation du Workspace (Init)..."
            init_cmd = ["terraform", "init", "-input=false", "-no-color"]
            process_init = subprocess.Popen(init_cmd, cwd=tmpdirname, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
            process_init.wait()

            if process_init.returncode != 0:
                yield "❌ Échec de l'initialisation Terraform."
                raise Exception("Terraform Init Failed")

            yield "🚀 Démarrage du déploiement isolé..."
            apply_cmd = ["terraform", "apply", "-auto-approve", "-input=false", "-no-color"]
            process_apply = subprocess.Popen(apply_cmd, cwd=tmpdirname, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
            
            for line in process_apply.stdout:
                clean = line.strip()
                if clean: yield clean
            
            process_apply.wait()
            if process_apply.returncode == 0: yield "✅ Déploiement terminé avec succès !"
            else: 
                yield "⚠️ Erreur lors du déploiement."
                raise Exception("Terraform Apply Failed")

    # --- DESTRUCTION CIBLÉE ---
    def destroy(self, resources: List[Dict[str, Any]], deployment_id: str) -> Generator[str, None, None]:
        with tempfile.TemporaryDirectory(prefix=f"ecoarch_destroy_{deployment_id}_") as tmpdirname:
            tf_path = Path(tmpdirname) / "main.tf"
            
            yield f"🔥 Ciblage de l'environnement : {deployment_id}"          
            # On passe une liste VIDE [] au lieu de 'resources'.
            # Cela force Terraform à se concentrer uniquement sur le fichier d'état distant (l'ID).
            with open(tf_path, "w") as f:
                f.write(self._generate_terraform_code([], deployment_id))
            
            yield "⚙️ Connexion au State isolé..."
            init_cmd = ["terraform", "init", "-input=false", "-no-color"]
            subprocess.Popen(init_cmd, cwd=tmpdirname, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ).wait()

            yield "⚠️ Destruction des ressources de CET environnement uniquement..."
            destroy_cmd = ["terraform", "destroy", "-auto-approve", "-input=false", "-no-color"]
            process_destroy = subprocess.Popen(destroy_cmd, cwd=tmpdirname, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=os.environ)
            
            for line in process_destroy.stdout:
                clean = line.strip()
                if clean: yield f"Destroy > {clean}"
            
            process_destroy.wait()
            if process_destroy.returncode == 0: yield "🗑️ Environnement spécifique détruit."
            else: 
                yield "⚠️ Erreur lors de la destruction."
                raise Exception("Terraform Destroy Failed")