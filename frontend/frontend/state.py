"""État global de l'application EcoArch (Reflex State)."""
import sys
import uuid
from pathlib import Path
from typing import Any

import reflex as rx
from supabase import create_client

# Bridge vers le module src
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.append(str(PROJECT_ROOT))

try:
    from src.config import GCPConfig, Config
    from src.simulation import InfracostSimulator
    from src.recommendation import RecommendationEngine
except ImportError:
    # Fallbacks pour le développement sans backend
    class GCPConfig:
        INSTANCE_TYPES = []
        DB_TIERS = []
        DB_VERSIONS = []
        STORAGE_CLASSES = []
    
    class Config:
        DEFAULT_BUDGET_LIMIT = 50.0
        SUPABASE_URL = ""
        SUPABASE_SERVICE_KEY = ""
        GCP_PROJECT_ID = ""
    
    class RecommendationEngine:
        @staticmethod
        def generate(answers):
            return []


class State(rx.State):
    """État principal de l'application."""
    
    # ===== UTILISATEUR & SESSION =====
    current_user: str = "Alice (DevOps)"
    users_list: list[str] = [
        "Alice (DevOps)", "Bob (FinOps)", "Charlie (Manager)", "Dave (Admin)"
    ]
    deployment_id: str = str(uuid.uuid4())[:8]
    destroy_id_input: str = ""
    
    def set_user(self, value: str) -> None:
        self.current_user = value
    
    def set_destroy_id_input(self, value: str) -> None:
        self.destroy_id_input = value.strip()
    
    def generate_new_id(self):
        self.deployment_id = str(uuid.uuid4())[:8]
        return rx.toast.info(f"Nouvelle Session: {self.deployment_id}")
    
    def set_deployment_id(self, value: str) -> None:
        self.deployment_id = value.strip()
    
    # ===== MODE & WIZARD =====
    is_expert_mode: bool = True
    wizard_auto_deploy: bool = False
    wizard_answers: dict[str, str] = {
        "environment": "dev",
        "traffic": "low",
        "workload": "general",
        "criticality": "low",
        "type": "web",
    }
    
    def toggle_mode(self, val: bool) -> None:
        self.is_expert_mode = val
    
    def set_wizard_auto_deploy(self, val: bool) -> None:
        self.wizard_auto_deploy = val
    
    def set_wizard_env_logic(self, value: str) -> None:
        self.wizard_answers["environment"] = "prod" if "Prod" in value else "dev"
    
    def set_wizard_workload_logic(self, value: str) -> None:
        if "Traitement" in value:
            self.wizard_answers["workload"] = "cpu"
        elif "Cache" in value:
            self.wizard_answers["workload"] = "memory"
        else:
            self.wizard_answers["workload"] = "general"
    
    def set_wizard_criticality_logic(self, value: str) -> None:
        self.wizard_answers["criticality"] = "high" if "critique" in value else "low"
    
    def set_wizard_traffic_logic(self, value: str) -> None:
        if "Viral" in value:
            self.wizard_answers["traffic"] = "high"
        elif "Croissance" in value:
            self.wizard_answers["traffic"] = "medium"
        else:
            self.wizard_answers["traffic"] = "low"
    
    def set_wizard_app_type_logic(self, value: str) -> None:
        """Définit le type d'application pour la recommandation de stack."""
        type_mapping = {
            "Site Web": "web",
            "API REST": "api",
            "Backend": "backend",
            "Jobs / Scripts": "batch",
            "Microservices": "microservices",
        }
        for key, app_type in type_mapping.items():
            if key in value:
                self.wizard_answers["type"] = app_type
                return
        self.wizard_answers["type"] = "web"
    
    def apply_recommendation_flow(self):
        """Applique les recommandations du wizard et lance la simulation."""
        self.is_loading = True
        yield
        
        try:
            self.resource_list = list(RecommendationEngine.generate(self.wizard_answers))
            yield from self.run_simulation()
            self.is_expert_mode = True
            yield
            
            # Auto-deploy si activé et budget respecté
            if self.wizard_auto_deploy and self.cost <= Config.DEFAULT_BUDGET_LIMIT:
                yield from self.start_deployment()
                
        except Exception as e:
            rx.toast.error(f"Erreur Wizard: {e}")
        finally:
            self.is_loading = False
            yield
    
    # ===== CONFIGURATION RESSOURCES =====
    selected_service: str = "compute"
    selected_machine: str = "e2-medium"
    selected_storage: int = 50
    selected_db_tier: str = "db-f1-micro"
    selected_db_version: str = "POSTGRES_14"
    selected_storage_class: str = "STANDARD"
    selected_software_stack: str = "none"
    
    # Listes d'options
    instance_types: list[str] = GCPConfig.INSTANCE_TYPES
    db_tiers: list[str] = GCPConfig.DB_TIERS
    db_versions: list[str] = GCPConfig.DB_VERSIONS
    storage_classes: list[str] = GCPConfig.STORAGE_CLASSES
    software_stacks: list[str] = GCPConfig.get_stack_names()
    
    def set_service(self, value: str) -> None:
        self.selected_service = value
    
    def set_machine(self, value: str) -> None:
        self.selected_machine = value
    
    def set_storage(self, value: list[float]) -> None:
        self.selected_storage = int(value[0])
    
    def set_db_tier(self, value: str) -> None:
        self.selected_db_tier = value
    
    def set_db_version(self, value: str) -> None:
        self.selected_db_version = value
    
    def set_storage_class(self, value: str) -> None:
        self.selected_storage_class = value
    
    def set_software_stack(self, value: str) -> None:
        """Définit la stack logicielle sélectionnée."""
        self.selected_software_stack = value
    
    @rx.var
    def stack_description(self) -> str:
        """Retourne la description de la stack sélectionnée."""
        stack_info = GCPConfig.SOFTWARE_STACKS.get(self.selected_software_stack, {})
        return stack_info.get("description", "")
    
    # ===== PANIER & SIMULATION =====
    resource_list: list[dict[str, Any]] = []
    cost: float = 0.0
    details: dict[str, Any] = {}
    is_loading: bool = False
    error_msg: str = ""
    
    def add_resource(self):
        """Ajoute une ressource au panier selon le service sélectionné."""
        # Récupérer le nom d'affichage de la stack
        stack_info = GCPConfig.SOFTWARE_STACKS.get(self.selected_software_stack, {})
        stack_display = stack_info.get("name", "Aucun") if stack_info else "Aucun"
        
        resource_builders = {
            "compute": lambda: {
                "type": "compute",
                "machine_type": self.selected_machine,
                "disk_size": self.selected_storage,
                "software_stack": self.selected_software_stack,
                "display_name": f"VM {self.selected_machine} ({stack_display})",
            },
            "sql": lambda: {
                "type": "sql",
                "db_tier": self.selected_db_tier,
                "db_version": self.selected_db_version,
                "display_name": f"SQL {self.selected_db_tier}",
            },
            "storage": lambda: {
                "type": "storage",
                "storage_class": self.selected_storage_class,
                "display_name": f"GCS {self.selected_storage_class}",
            },
        }
        
        builder = resource_builders.get(self.selected_service)
        if builder:
            self.resource_list = self.resource_list + [builder()]
            return State.run_simulation
    
    def remove_resource(self, index: int):
        """Retire une ressource du panier par son index."""
        self.resource_list = [r for i, r in enumerate(self.resource_list) if i != index]
        return State.run_simulation
    
    def run_simulation(self):
        """Lance la simulation des coûts via Infracost."""
        self.is_loading = True
        yield
        
        try:
            if not self.resource_list:
                self.cost, self.details = 0.0, {}
            else:
                sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
                result = sim.simulate(self.resource_list)
                
                if result.success:
                    self.cost = round(result.monthly_cost, 2)
                    self.details = result.details
                    self.error_msg = ""
                else:
                    self.cost = 0.0
                    self.error_msg = result.error_message or "Erreur inconnue"
                    
        except Exception as e:
            self.error_msg = str(e)
        finally:
            self.is_loading = False
            yield
    
    # ===== DÉPLOIEMENT =====
    logs: list[str] = []
    is_deploying: bool = False
    deploy_status: str = "idle"  # idle, running, success, error
    
    def start_deployment(self):
        """Démarre le déploiement Terraform des ressources."""
        if not self.resource_list:
            return rx.toast.error("Panier vide!")
        
        if self.cost > Config.DEFAULT_BUDGET_LIMIT:
            return rx.toast.error("Budget dépassé!")
        
        self.is_deploying = True
        self.deploy_status = "running"
        target_id = self.deployment_id
        self.logs = [f"--- DEPLOY: {target_id} ---"]
        audit_id = None
        yield
        
        try:
            # Log dans Supabase (optionnel)
            audit_id = self._create_audit_log("DEPLOY", target_id)
            yield
            
            # Exécution Terraform
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            for line in sim.deploy(self.resource_list, target_id):
                self._append_log(line)
                yield
            
            self.deploy_status = "success"
            self.logs.append("✅ SUCCESS")
            yield
            
            self._update_audit_log(audit_id, "SUCCESS")
            
        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERROR: {e}")
            self._update_audit_log(audit_id, "ERROR")
            
        finally:
            self.is_deploying = False
            self.load_audit_logs()
            yield
    
    def start_destruction(self):
        """Démarre la destruction Terraform de l'infrastructure."""
        if self.is_deploying:
            return
        
        self.is_deploying = True
        self.deploy_status = "running"
        target_id = self.destroy_id_input or self.deployment_id
        self.logs = [f"--- DESTROY: {target_id} ---"]
        yield
        
        try:
            self._create_audit_log("DESTROY", target_id, cost=0.0)
            
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            for line in sim.destroy(self.resource_list, target_id):
                self._append_log(line)
                yield
            
            self.deploy_status = "success"
            self.logs.append("✅ DESTROY SUCCESS")
            
        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERROR: {e}")
            
        finally:
            self.is_deploying = False
            self.load_audit_logs()
            yield
    
    def _append_log(self, line: str) -> None:
        """Ajoute une ligne au log avec limite de taille."""
        self.logs.append(line)
        if len(self.logs) > 100:
            self.logs.pop(0)
    
    def _create_audit_log(
        self,
        action: str,
        target_id: str,
        cost: float | None = None,
    ) -> int | None:
        """Crée un log d'audit dans Supabase."""
        if not Config.SUPABASE_URL:
            return None
        
        try:
            sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
            summary = f"[{target_id}] " + ", ".join(
                r.get("display_name", "") for r in self.resource_list
            )
            
            res = sb.table("audit_logs").insert({
                "user": self.current_user,
                "action": action,
                "resources_summary": summary,
                "total_cost": cost if cost is not None else self.cost,
                "status": "PENDING",
            }).execute()
            
            return res.data[0]["id"] if res.data else None
        except Exception:
            return None
    
    def _update_audit_log(self, audit_id: int | None, status: str) -> None:
        """Met à jour le statut d'un log d'audit."""
        if not audit_id or not Config.SUPABASE_URL:
            return
        
        try:
            sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
            sb.table("audit_logs").update({"status": status}).eq("id", audit_id).execute()
        except Exception:
            pass
    
    # ===== AUDIT LOGS =====
    audit_logs: list[dict] = []
    
    def load_audit_logs(self) -> None:
        """Charge les logs d'audit depuis Supabase."""
        if not (Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY):
            return
        
        try:
            sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
            res = sb.table("audit_logs").select("*").order(
                "created_at", desc=True
            ).limit(50).execute()
            
            self.audit_logs = [
                self._format_audit_row(row) for row in res.data
            ]
        except Exception:
            pass
    
    @staticmethod
    def _format_audit_row(row: dict) -> dict:
        """Formate une ligne d'audit pour l'affichage."""
        created_at = row.get("created_at", "")
        
        if "T" in created_at:
            date_part, time_part = created_at.split("T")
            formatted_date = f"{date_part} {time_part[:5]}"
        else:
            formatted_date = created_at
        
        return {
            **row,
            "formatted_date": formatted_date,
            "formatted_cost": f"${row.get('total_cost', 0):.2f}",
        }
    
    # ===== COMPUTED PROPERTIES =====
    @rx.var
    def chart_data(self) -> list[dict]:
        """Données pour le graphique de répartition des coûts."""
        if not self.details:
            return []
        
        # Couleurs par catégorie
        colors = {
            "Compute": "#00f3ff",
            "SQL": "#bc13fe",
            "Storage": "#ff9900",
            "Network": "#00ff99",
            "Autre": "#ff00ff",
        }
        
        data = []
        
        try:
            for project in self.details.get("projects", []):
                resources = project.get("breakdown", {}).get("resources", [])
                
                for res in resources:
                    value = float(res.get("monthlyCost", 0))
                    if value <= 0:
                        continue
                    
                    # Classification simple par nom
                    name = res.get("name", "").lower()
                    category = self._categorize_resource(name)
                    
                    data.append({
                        "name": category,
                        "value": value,
                        "fill": colors.get(category, colors["Autre"]),
                    })
                    
        except Exception:
            pass
        
        return data
    
    @staticmethod
    def _categorize_resource(name: str) -> str:
        """Catégorise une ressource par son nom."""
        if "sql" in name:
            return "SQL"
        if "instance" in name:
            return "Compute"
        if "storage" in name:
            return "Storage"
        if "address" in name or "forwarding" in name:
            return "Network"
        return "Autre"