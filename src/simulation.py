"""Simulateur de coûts infrastructure via Infracost et Terraform."""
import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional

from .config import Config, GCPConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class SimulationResult:
    """Résultat d'une simulation de coûts."""
    success: bool
    monthly_cost: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None


class InfracostSimulator:
    """Simule et déploie des ressources GCP avec estimation des coûts."""
    
    def __init__(
        self,
        project_id: Optional[str] = None,
        timeout: Optional[int] = None,
    ):
        self.project_id = project_id or Config.GCP_PROJECT_ID
        self.timeout = timeout or Config.INFRACOST_TIMEOUT
    
    def _generate_terraform_code(
        self,
        resources: list[dict[str, Any]],
        deployment_id: str = "simulation",
        include_backend: bool = True,
    ) -> str:
        """Génère le code Terraform pour les ressources demandées."""
        state_prefix = f"terraform/state/{deployment_id}"
        
        # Header Terraform - avec ou sans backend selon le contexte
        if include_backend:
            tf_header = f'''
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
'''
        else:
            # Pour la simulation Infracost, pas besoin de backend
            tf_header = f'''
terraform {{
  required_providers {{
    google = {{
      source = "hashicorp/google"
    }}
  }}
}}

provider "google" {{
  project = "{self.project_id}"
  region  = "{Config.DEFAULT_REGION}"
}}
'''
        
        tf_parts = [tf_header]
        
        # Génération des ressources
        for idx, res in enumerate(resources):
            resource_type = res.get("type", "compute")
            tf_code = self._generate_resource_tf(idx, resource_type, res, deployment_id)
            if tf_code:
                tf_parts.append(tf_code)
        
        return "\n".join(tf_parts)
    
    def _generate_resource_tf(
        self,
        idx: int,
        resource_type: str,
        res: dict,
        deployment_id: str,
    ) -> str:
        """Génère le code Terraform pour une ressource spécifique."""
        name = f"res-{idx}-{resource_type}"
        gcp_name = f"{name}-{deployment_id}"
        
        generators = {
            "compute": self._tf_compute,
            "sql": self._tf_sql,
            "storage": self._tf_storage,
            "load_balancer": self._tf_load_balancer,
        }
        
        generator = generators.get(resource_type)
        if generator:
            return generator(name, gcp_name, res, deployment_id)
        return ""
    
    def _tf_compute(self, name: str, gcp_name: str, res: dict, deployment_id: str) -> str:
        """Génère une ressource Compute Engine."""
        machine = res.get("machine_type", "e2-medium")
        disk = res.get("disk_size", 50)
        zone = f"{Config.DEFAULT_REGION}-a"
        software_stack = res.get("software_stack", "none")
        startup_script = GCPConfig.get_startup_script(software_stack)
        
        # Section metadata pour startup_script si une stack est sélectionnée
        metadata_section = ""
        if startup_script:
            # Échapper les guillemets et retours à la ligne pour Terraform
            # Utiliser un heredoc Terraform pour les scripts multi-lignes
            metadata_section = f'''
  metadata = {{
    startup-script = <<-EOF
{startup_script}
EOF
  }}'''
        
        return f'''
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
  network_interface {{ network = "default" }}{metadata_section}
  labels = {{
    deployment_id = "{deployment_id}"
    managed_by    = "ecoarch-app"
    software_stack = "{software_stack}"
  }}
}}
'''
    
    def _tf_sql(self, name: str, gcp_name: str, res: dict, _: str) -> str:
        """Génère une ressource Cloud SQL."""
        tier = res.get("db_tier", "db-f1-micro")
        version = res.get("db_version", "POSTGRES_14")
        
        return f'''
resource "google_sql_database_instance" "{name}" {{
  name             = "{gcp_name}"
  database_version = "{version}"
  region           = "{Config.DEFAULT_REGION}"
  settings {{ tier = "{tier}" }}
  deletion_protection = false
}}
'''
    
    def _tf_storage(self, name: str, _: str, res: dict, deployment_id: str) -> str:
        """Génère une ressource Cloud Storage."""
        storage_class = res.get("storage_class", "STANDARD")
        safe_name = f"{self.project_id}-{name}-{deployment_id}".lower()
        
        return f'''
resource "google_storage_bucket" "{name}" {{
  name          = "{safe_name}"
  location      = "{Config.DEFAULT_REGION}"
  storage_class = "{storage_class}"
  force_destroy = true
}}
'''
    
    def _tf_load_balancer(self, name: str, _: str, __: dict, deployment_id: str) -> str:
        """Génère une ressource Load Balancer."""
        return f'''
resource "google_compute_global_address" "{name}" {{
  name = "lb-ip-{deployment_id}"
}}
'''
    
    def simulate(self, resources: list[dict[str, Any]]) -> SimulationResult:
        """Simule les coûts des ressources via Infracost."""
        if not resources:
            return SimulationResult(success=True, monthly_cost=0.0, details={})
        
        try:
            with tempfile.TemporaryDirectory(prefix=Config.TEMP_FILE_PREFIX) as tmpdir:
                tf_path = Path(tmpdir) / "main.tf"
                # Utiliser include_backend=False pour la simulation (pas besoin d'état GCS)
                tf_path.write_text(
                    self._generate_terraform_code(resources, "simulation_tmp", include_backend=False)
                )
                
                result = subprocess.run(
                    ["infracost", "breakdown", "--path", tmpdir, "--format", "json"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    env=os.environ,
                    check=False,
                )
                
                if result.returncode != 0:
                    return SimulationResult(
                        success=True,
                        monthly_cost=0.0,
                        details={},
                        error_message=f"Warning: {result.stderr}",
                    )
                
                try:
                    data = json.loads(result.stdout)
                    return SimulationResult(
                        success=True,
                        monthly_cost=float(data.get("totalMonthlyCost", 0.0)),
                        details=data,
                    )
                except (json.JSONDecodeError, ValueError):
                    return SimulationResult(success=True, monthly_cost=0.0, details={})
                    
        except subprocess.TimeoutExpired:
            return SimulationResult(
                success=False,
                error_message="Timeout: Infracost n'a pas répondu à temps",
            )
        except Exception as e:
            return SimulationResult(success=False, error_message=str(e))
    
    def deploy(
        self,
        resources: list[dict[str, Any]],
        deployment_id: str,
    ) -> Generator[str, None, None]:
        """Déploie les ressources via Terraform (générateur pour streaming)."""
        with tempfile.TemporaryDirectory(prefix=f"ecoarch_{deployment_id}_") as tmpdir:
            tf_path = Path(tmpdir) / "main.tf"
            yield f"📝 ID: {deployment_id}"
            
            tf_path.write_text(self._generate_terraform_code(resources, deployment_id))
            
            # Init
            yield "⚙️ Terraform init..."
            yield from self._run_terraform(tmpdir, ["init", "-input=false", "-no-color", "-reconfigure"])
            
            # Apply
            yield "🚀 Terraform apply..."
            yield from self._run_terraform(tmpdir, ["apply", "-auto-approve", "-input=false", "-no-color"])
            
            yield "✅ Déploiement terminé"
    
    def destroy(
        self,
        resources: list[dict[str, Any]],
        deployment_id: str,
    ) -> Generator[str, None, None]:
        """Détruit les ressources via Terraform (générateur pour streaming)."""
        with tempfile.TemporaryDirectory(prefix=f"ecoarch_destroy_{deployment_id}_") as tmpdir:
            tf_path = Path(tmpdir) / "main.tf"
            yield f"🔥 Cible: {deployment_id}"
            
            # On génère un fichier vide pour récupérer le state et tout détruire
            tf_path.write_text(self._generate_terraform_code([], deployment_id))
            
            # Init
            yield "⏳ Connexion au state..."
            for line in self._run_terraform(tmpdir, ["init", "-input=false", "-no-color", "-reconfigure"]):
                yield f"Init > {line}"
            
            # Destroy avec -lock=false pour forcer
            yield "⚠️ Destruction en cours..."
            for line in self._run_terraform(
                tmpdir,
                ["destroy", "-auto-approve", "-input=false", "-lock=false", "-no-color"],
            ):
                if line.strip():
                    yield f"Destroy > {line}"
            
            yield "🗑️ Nettoyage terminé"
    
    def _run_terraform(
        self,
        cwd: str,
        args: list[str],
    ) -> Generator[str, None, None]:
        """Exécute une commande Terraform avec streaming des logs."""
        process = subprocess.Popen(
            ["terraform", *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=os.environ,
            bufsize=1,
        )
        
        for line in process.stdout:
            yield line.strip()
        
        process.wait()
        
        if process.returncode != 0:
            raise Exception(f"Terraform {args[0]} failed")