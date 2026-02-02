import reflex as rx
import sys
import uuid
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
    from src.recommendation import RecommendationEngine
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
    class RecommendationEngine:
        @staticmethod
        def generate(answers): return []

class State(rx.State):
    # --- 1. IDENTITÉ & SESSION ---
    current_user: str = "Alice (DevOps)"
    users_list: List[str] = ["Alice (DevOps)", "Bob (FinOps)", "Charlie (Manager)", "Dave (Admin)"]
    deployment_id: str = str(uuid.uuid4())[:8]

    def set_user(self, value: str):
        self.current_user = value

    def generate_new_id(self):
        self.deployment_id = str(uuid.uuid4())[:8]
        return rx.toast.info(f"Nouvelle Session ID : {self.deployment_id}")

    def set_deployment_id(self, value: str):
        self.deployment_id = value.strip()

    # --- 2. MODE ASSISTANT (WIZARD V3) ---
    is_expert_mode: bool = True
    wizard_auto_deploy: bool = False
    
    # Réponses enrichies pour le moteur HA
    wizard_answers: Dict[str, str] = {
        "environment": "dev", 
        "traffic": "low",
        "workload": "general",  # CPU, Memory, General
        "criticality": "low"    # Low (Standard), High (HA/Critique)
    }

    def toggle_mode(self, val: bool):
        self.is_expert_mode = val

    def set_wizard_auto_deploy(self, val: bool):
        self.wizard_auto_deploy = val

    # --- LOGIQUE DE NETTOYAGE DES RÉPONSES ---
    
    # Q1 : Type (Non utilisé pour le calcul HA mais utile pour le contexte)
    def set_wizard_type_logic(self, value: str):
        clean = value.split(" ")[0].lower()
        self.wizard_answers["type"] = clean

    # Q2 : Environnement
    def set_wizard_env_logic(self, value: str):
        res = "prod" if "Prod" in value else "dev"
        self.wizard_answers["environment"] = res

    # Q3 : Trafic
    def set_wizard_traffic_logic(self, value: str):
        if "Élevé" in value: res = "high"
        elif "Moyen" in value: res = "medium"
        else: res = "low"
        self.wizard_answers["traffic"] = res

    # Q4 : Nature de la charge (NOUVEAU)
    def set_wizard_workload_logic(self, value: str):
        # "Calcul Intensif (CPU)" -> "cpu"
        if "CPU" in value: res = "cpu"
        elif "Mémoire" in value: res = "memory"
        else: res = "general"
        self.wizard_answers["workload"] = res

    # Q5 : Criticité (NOUVEAU - Déclenche le HA)
    def set_wizard_criticality_logic(self, value: str):
        # "Critique (Haute Disponibilité)" -> "high"
        if "Critique" in value: res = "high"
        else: res = "low"
        self.wizard_answers["criticality"] = res

    # --- FLUX INTELLIGENT ---
    def apply_recommendation_flow(self):
        self.is_loading = True
        yield
        try:
            # A. Génération intelligente
            recommended_resources = RecommendationEngine.generate(self.wizard_answers)
            self.resource_list = recommended_resources
            
            # B. Simulation
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            result = sim.simulate(self.resource_list)
            
            if result.success:
                self.cost = result.monthly_cost
                self.details = result.details
            else:
                self.cost = 0.0
                raise Exception(result.error_message)
            
            # C. UI Update
            self.is_expert_mode = True
            yield 

            # D. Auto-Déploiement
            if self.wizard_auto_deploy:
                if self.cost <= Config.DEFAULT_BUDGET_LIMIT:
                    rx.toast.info(f"Budget OK : Lancement du déploiement...")
                    yield from self.start_deployment()
                else:
                    rx.toast.warning(f"Auto-déploiement stoppé : Budget dépassé ({self.cost}$)")
            else:
                rx.toast.success("Stack optimisée générée. Vérifiez les détails.")

        except Exception as e:
            rx.toast.error(f"Erreur Flow : {str(e)}")
        finally:
            self.is_loading = False
            yield

    # --- 3. LOGIQUE EXPERT (Inchangée) ---
    selected_service: str = "compute"
    selected_machine: str = "e2-medium"
    selected_storage: int = 50
    selected_db_tier: str = "db-f1-micro"
    selected_db_version: str = "POSTGRES_14"
    selected_storage_class: str = "STANDARD"

    resource_list: List[Dict[str, Any]] = []
    cost: float = 0.0
    details: Dict[str, Any] = {}
    is_loading: bool = False
    error_msg: str = ""
    history: List[Dict] = []
    
    logs: List[str] = []
    is_deploying: bool = False
    deploy_status: str = "idle" 

    instance_types: List[str] = GCPConfig.INSTANCE_TYPES
    db_tiers: List[str] = GCPConfig.DB_TIERS
    db_versions: List[str] = GCPConfig.DB_VERSIONS
    storage_classes: List[str] = GCPConfig.STORAGE_CLASSES
    NEON_COLORS = {"Compute": "#00f3ff", "SQL": "#bc13fe", "Storage": "#ff9900", "Network": "#00ff99", "Autre": "#ff00ff"}

    def set_service(self, value: str): self.selected_service = value
    def set_machine(self, value: str): self.selected_machine = value
    def set_storage(self, value: List[float]): self.selected_storage = int(value[0])
    def set_db_tier(self, value: str): self.selected_db_tier = value
    def set_db_version(self, value: str): self.selected_db_version = value
    def set_storage_class(self, value: str): self.selected_storage_class = value

    def add_resource(self):
        res = {}
        if self.selected_service == "compute":
            res = {"type": "compute", "machine_type": self.selected_machine, "disk_size": self.selected_storage, "display_name": f"VM - {self.selected_machine}"}
        elif self.selected_service == "sql":
            res = {"type": "sql", "db_tier": self.selected_db_tier, "db_version": self.selected_db_version, "display_name": f"SQL - {self.selected_db_tier}"}
        elif self.selected_service == "storage":
             res = {"type": "storage", "storage_class": self.selected_storage_class, "display_name": f"GCS - {self.selected_storage_class}"}
        
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
        if not self.resource_list: return rx.toast.error("Rien à déployer !")
        if self.cost > Config.DEFAULT_BUDGET_LIMIT: return rx.toast.error(f"Budget dépassé ! Limite: {Config.DEFAULT_BUDGET_LIMIT}$")

        self.is_deploying = True
        self.deploy_status = "running"
        self.logs = [f"--- Protocole Démarré pour : {self.current_user} ---", f"--- ID Session : {self.deployment_id} ---"]
        audit_id = None 
        yield 
        
        try:
            if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
                try:
                    sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
                    summary_text = f"[{self.deployment_id}] " + ", ".join([r.get("display_name", "Unknown") for r in self.resource_list])
                    response = sb.table("audit_logs").insert({"user": self.current_user, "action": "DEPLOY_START", "resources_summary": summary_text, "total_cost": self.cost, "status": "PENDING"}).execute()
                    if response.data: audit_id = response.data[0]['id']; self.logs.append(f"✅ Audit Traçabilité (ID: {audit_id})")
                except Exception as e: self.logs.append(f"⚠️ Erreur Audit Init: {str(e)}")
            yield 
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            for log_line in sim.deploy(self.resource_list, self.deployment_id):
                self.logs.append(log_line)
                if len(self.logs) > 100: self.logs.pop(0)
                yield 
            self.deploy_status = "success"
            self.logs.append("--- DÉPLOIEMENT TERMINÉ AVEC SUCCÈS ---")
            if audit_id and Config.SUPABASE_URL:
                try: sb.table("audit_logs").update({"status": "SUCCESS"}).eq("id", audit_id).execute(); self.logs.append("✅ Statut Audit mis à jour : SUCCESS")
                except: pass
        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERREUR CRITIQUE : {str(e)}")
            if audit_id and Config.SUPABASE_URL:
                try: sb.table("audit_logs").update({"status": "ERROR"}).eq("id", audit_id).execute()
                except: pass
        finally:
            self.is_deploying = False
            yield

    def start_destruction(self):
        if self.is_deploying: return
        self.is_deploying = True 
        self.deploy_status = "running"
        self.logs = [f"--- Destruction demandée par : {self.current_user} ---", f"--- Cible ID : {self.deployment_id} ---"]
        audit_id = None
        yield
        try:
            if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
                try:
                    sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
                    summary = f"[{self.deployment_id}] DESTRUCTION TOTALE"
                    response = sb.table("audit_logs").insert({"user": self.current_user, "action": "DESTROY_START", "resources_summary": summary, "total_cost": 0.0, "status": "PENDING"}).execute()
                    if response.data: audit_id = response.data[0]['id']; self.logs.append(f"✅ Audit Destruction ID #{audit_id}")
                except Exception as e: self.logs.append(f"⚠️ Erreur Audit: {str(e)}")
            yield
            sim = InfracostSimulator(project_id=Config.GCP_PROJECT_ID)
            for log_line in sim.destroy(self.resource_list, self.deployment_id):
                self.logs.append(log_line)
                if len(self.logs) > 100: self.logs.pop(0)
                yield
            self.deploy_status = "success"
            self.logs.append("--- NETTOYAGE TERMINÉ ---")
            if audit_id and Config.SUPABASE_URL:
                try: sb.table("audit_logs").update({"status": "SUCCESS"}).eq("id", audit_id).execute()
                except: pass
        except Exception as e:
            self.deploy_status = "error"
            self.logs.append(f"❌ ERREUR DESTRUCTION : {str(e)}")
            if audit_id and Config.SUPABASE_URL:
                try: sb.table("audit_logs").update({"status": "ERROR"}).eq("id", audit_id).execute()
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

    @rx.var
    def last_run_cost(self) -> str: return f"{self.history[0]['total_monthly_cost']} $" if self.history else "0.00 $"
    @rx.var
    def last_run_status(self) -> str: return "Conforme" if self.history and self.history[0].get('status') == 'PASSED' else "Non Conforme"
    @rx.var
    def last_run_color(self) -> str: return "grass" if self.history and self.history[0].get('status') == 'PASSED' else "tomato"
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
                        elif "forwarding_rule" in res['name']: name = "Network" # <--- IMPORTANT: Support graphique LB
                        color = self.NEON_COLORS.get(name, self.NEON_COLORS["Autre"])
                        data.append({"name": name, "value": val, "fill": color})
        except: pass
        return data

    # --- AUDIT LOGS (NOUVEAU) ---
    audit_logs: List[Dict[str, Any]] = []

    def load_audit_logs(self):
        """Récupère les logs d'audit depuis Supabase pour l'affichage"""
        if not (Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY):
            return
            
        try:
            sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
            # On récupère les 50 derniers logs, du plus récent au plus ancien
            response = sb.table("audit_logs").select("*").order("created_at", desc=True).limit(50).execute()
            
            raw_data = response.data
            
            # Petit formatage pour l'affichage (Dates, Prix)
            formatted_data = []
            for row in raw_data:
                # Nettoyage de la date (ex: 2026-01-25T14:35...)
                date_str = row.get("created_at", "")
                if "T" in date_str:
                    date_str = date_str.split("T")[0] + " " + date_str.split("T")[1][:5]
                
                row["formatted_date"] = date_str
                row["formatted_cost"] = f"${row.get('total_cost', 0):.2f}"
                formatted_data.append(row)

            self.audit_logs = formatted_data
        except Exception as e:
            print(f"Erreur chargement logs: {e}")
            rx.toast.error("Impossible de charger l'historique d'audit.")