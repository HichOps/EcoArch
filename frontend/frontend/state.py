import reflex as rx
import sys
import uuid # <-- Pour générer les IDs uniques
from pathlib import Path
from typing import Dict, Any, List
from supabase import create_client

# --- BRIDGE ---
current_file_path = Path(__file__).resolve()
project_root = current_file_path.parents[2]
sys.path.append(str(project_root))

try:
    from src.config import GCPConfig, Config
    from src.simulation import InfracostSimulator
except ImportError:
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

class State(rx.State):
    # --- MULTI-TENANT & USER (NOUVEAU) ---
    current_user: str = "Alice (DevOps)"
    users_list: List[str] = ["Alice (DevOps)", "Bob (FinOps)", "Charlie (Manager)", "Dave (Admin)"]
    
    # ID Unique de l'infrastructure (UUID court)
    deployment_id: str = str(uuid.uuid4())[:8]

    def set_user(self, value: str):
        self.current_user = value

    def generate_new_id(self):
        """Permet de démarrer une nouvelle session propre"""
        self.deployment_id = str(uuid.uuid4())[:8]
        return rx.toast.info(f"Nouvelle Session ID : {self.deployment_id}")

    def set_deployment_id(self, value: str):
        """Permet de saisir manuellement un ID pour retrouver une infra existante"""
        # On ajoute .strip() pour enlever les espaces invisibles avant/après
        self.deployment_id = value.strip()

    # --- UI STATE ---
    selected_service: str = "compute"
    selected_machine: str = "e2-medium"
    selected_storage: int = 50
    selected_db_tier: str = "db-f1-micro"
    selected_db_version: str = "POSTGRES_14"
    selected_storage_class: str = "STANDARD"

    # --- PANIER & RESULTATS ---
    resource_list: List[Dict[str, Any]] = []
    cost: float = 0.0
    details: Dict[str, Any] = {}
    is_loading: bool = False
    error_msg: str = ""
    history: List[Dict] = []

    # --- DEPLOIEMENT & LOGS ---
    logs: List[str] = []
    is_deploying: bool = False
    deploy_status: str = "idle" 

    # --- CONSTANTES ---
    instance_types: List[str] = GCPConfig.INSTANCE_TYPES
    db_tiers: List[str] = GCPConfig.DB_TIERS
    db_versions: List[str] = GCPConfig.DB_VERSIONS
    storage_classes: List[str] = GCPConfig.STORAGE_CLASSES

    NEON_COLORS = {
        "Compute": "#00f3ff", 
        "SQL": "#bc13fe",     
        "Storage": "#ff9900", 
        "Autre": "#ff00ff"
    }

    # --- SETTERS ---
    def set_service(self, value: str): self.selected_service = value
    def set_machine(self, value: str): self.selected_machine = value
    def set_storage(self, value: List[float]): self.selected_storage = int(value[0])
    def set_db_tier(self, value: str): self.selected_db_tier = value
    def set_db_version(self, value: str): self.selected_db_version = value
    def set_storage_class(self, value: str): self.selected_storage_class = value

    # --- ACTIONS ---
    def add_resource(self):
        res = {}
        if self.selected_service == "compute":
            res = {
                "type": "compute",
                "machine_type": self.selected_machine,
                "disk_size": self.selected_storage,
                "display_name": f"VM - {self.selected_machine}"
            }
        elif self.selected_service == "sql":
            res = {
                "type": "sql",
                "db_tier": self.selected_db_tier,
                "db_version": self.selected_db_version,
                "display_name": f"SQL - {self.selected_db_tier}"
            }
        elif self.selected_service == "storage":
             res = {
                "type": "storage",
                "storage_class": self.selected_storage_class,
                "display_name": f"GCS - {self.selected_storage_class}"
            }
        
        if res:
            self.resource_list.append(res)
            return State.run_simulation

    def remove_resource(self, index: int):
        if 0 <= index < len(self.resource_list):
            self.resource_list.pop(index)
            return State.run_simulation

    def run_simulation(self):
        self.is_loading = True
        self.error_msg = ""
        yield
        try:
            if not self.resource_list:
                self.cost = 0.0
                self.details = {}
            else:
                sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
                result = sim.simulate(self.resource_list)
                if result.success:
                    self.cost = result.monthly_cost
                    self.details = result.details
                else:
                    self.cost = 0.0
                    self.error_msg = result.error_message
        except Exception as e:
            self.error_msg = str(e)
        finally:
            self.is_loading = False

    def start_deployment(self):
        # 1. Vérifications
        if not self.resource_list:
            return rx.toast.error("Rien à déployer !")
        
        if self.cost > Config.DEFAULT_BUDGET_LIMIT:
             return rx.toast.error(f"Budget dépassé ! Limite: {Config.DEFAULT_BUDGET_LIMIT}$")

        # 2. Initialisation UI
        self.is_deploying = True
        self.deploy_status = "running"
        self.logs = [f"--- Protocole Démarré pour : {self.current_user} ---", f"--- ID Session : {self.deployment_id} ---"]
        
        audit_id = None 
        yield 
        
        try:
            # Audit Supabase AVEC Identité
            if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
                try:
                    sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
                    # On inclut l'ID dans le résumé pour la traçabilité sans changer la structure BDD
                    summary_text = f"[{self.deployment_id}] " + ", ".join([r.get("display_name", "Unknown") for r in self.resource_list])
                    
                    response = sb.table("audit_logs").insert({
                        "user": self.current_user, # <-- On utilise le vrai utilisateur
                        "action": "DEPLOY_START",
                        "resources_summary": summary_text,
                        "total_cost": self.cost,
                        "status": "PENDING"
                    }).execute()
                    
                    if response.data:
                        audit_id = response.data[0]['id']
                        self.logs.append(f"✅ Audit Traçabilité (ID: {audit_id})")
                except Exception as e:
                    self.logs.append(f"⚠️ Erreur Audit Init: {str(e)}")

            yield 

            # Lancement Terraform avec l'ID unique
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            # On passe self.deployment_id pour isoler le state
            for log_line in sim.deploy(self.resource_list, self.deployment_id):
                self.logs.append(log_line)
                if len(self.logs) > 100: self.logs.pop(0)
                yield 
            
            self.deploy_status = "success"
            self.logs.append("--- DÉPLOIEMENT TERMINÉ AVEC SUCCÈS ---")

            # Update Supabase -> SUCCESS
            if audit_id and Config.SUPABASE_URL:
                try:
                    sb.table("audit_logs").update({"status": "SUCCESS"}).eq("id", audit_id).execute()
                    self.logs.append("✅ Statut Audit mis à jour : SUCCESS")
                except: pass
            
        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERREUR CRITIQUE : {str(e)}")
            if audit_id and Config.SUPABASE_URL:
                try:
                    sb.table("audit_logs").update({"status": "ERROR"}).eq("id", audit_id).execute()
                except: pass
        
        finally:
            self.is_deploying = False
            yield

    def start_destruction(self):
        """Lance la destruction de l'infrastructure"""
        if self.is_deploying: return

        self.is_deploying = True 
        self.deploy_status = "running"
        self.logs = [f"--- Destruction demandée par : {self.current_user} ---", f"--- Cible ID : {self.deployment_id} ---"]
        
        audit_id = None
        yield

        try:
            # 1. Audit Supabase (DESTROY_START)
            if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
                try:
                    sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
                    summary = f"[{self.deployment_id}] DESTRUCTION TOTALE"
                    
                    response = sb.table("audit_logs").insert({
                        "user": self.current_user, # <-- Utilisateur actif
                        "action": "DESTROY_START",
                        "resources_summary": summary,
                        "total_cost": 0.0,
                        "status": "PENDING"
                    }).execute()
                    
                    if response.data:
                        audit_id = response.data[0]['id']
                        self.logs.append(f"✅ Audit Destruction ID #{audit_id}")
                except Exception as e:
                    self.logs.append(f"⚠️ Erreur Audit: {str(e)}")
            
            yield

            # 2. Lancement Terraform Destroy
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            
            # On passe self.deployment_id pour ne détruire QUE cette infra
            for log_line in sim.destroy(self.resource_list, self.deployment_id):
                self.logs.append(log_line)
                if len(self.logs) > 100: self.logs.pop(0)
                yield

            self.deploy_status = "success"
            self.logs.append("--- NETTOYAGE TERMINÉ ---")

            # 3. Update Supabase (SUCCESS)
            if audit_id and Config.SUPABASE_URL:
                try:
                    sb.table("audit_logs").update({"status": "SUCCESS"}).eq("id", audit_id).execute()
                except: pass

        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERREUR DESTRUCTION : {str(e)}")
            if audit_id and Config.SUPABASE_URL:
                try:
                    sb.table("audit_logs").update({"status": "ERROR"}).eq("id", audit_id).execute()
                except: pass
        
        finally:
            self.is_deploying = False
            yield

    def load_history(self):
        if not (Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY): return
        try:
            sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
            response = sb.table("cost_history").select("*").order("created_at", desc=True).limit(20).execute()
            data = response.data
            for item in data:
                item["total_monthly_cost"] = round(float(item.get("total_monthly_cost", 0)), 2)
                item["display_date"] = item.get("created_at", "").split("T")[0]
            self.history = data
        except Exception: pass

    # --- COMPUTED VARS ---
    @rx.var
    def last_run_cost(self) -> str:
        return f"{self.history[0]['total_monthly_cost']} $" if self.history else "0.00 $"
    @rx.var
    def last_run_status(self) -> str:
        return "Conforme" if self.history and self.history[0].get('status') == 'PASSED' else "Non Conforme"
    @rx.var
    def last_run_color(self) -> str:
        return "grass" if self.history and self.history[0].get('status') == 'PASSED' else "tomato"

    @rx.var
    def chart_data(self) -> List[Dict]:
        if not self.details: return []
        data = []
        try:
            for project in self.details.get('projects', []):
                for res in project.get('breakdown', {}).get('resources', []):
                    val = float(res.get('monthlyCost', 0))
                    if val > 0:
                        name = "Autre"
                        if "sql" in res['name']: name = "SQL"
                        elif "instance" in res['name']: name = "Compute"
                        elif "storage" in res['name']: name = "Storage"
                        color = self.NEON_COLORS.get(name, self.NEON_COLORS["Autre"])
                        data.append({"name": name, "value": val, "fill": color})
        except: pass
        return data