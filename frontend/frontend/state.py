import reflex as rx
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from supabase import create_client

# --- BRIDGE VERS LOGIQUE EXISTANTE ---
current_file_path = Path(__file__).resolve()
project_root = current_file_path.parents[2]
sys.path.append(str(project_root))

try:
    from src.config import GCPConfig, Config
    from src.simulation import InfracostSimulator
except ImportError as e:
    print(f"❌ Erreur d'import : {e}")
    # Fallbacks...
    class GCPConfig:
        REGIONS = ["us-central1"]
        INSTANCE_TYPES = ["e2-medium"]
    class Config:
        DEFAULT_BUDGET_LIMIT = 50.0
        SUPABASE_URL = ""
        SUPABASE_SERVICE_KEY = ""

class State(rx.State):
    # --- VARIABLES SIMULATEUR ---
    region: str = "europe-west1"
    instance_type: str = "e2-medium"
    storage: int = 50
    cost: float = 0.0
    details: Dict[str, Any] = {}
    is_loading: bool = False
    error_msg: str = ""
    
    # --- VARIABLES GOUVERNANCE (Nouveau) ---
    history: List[Dict] = []
    
    # Listes constantes
    regions: List[str] = GCPConfig.REGIONS
    instance_types: List[str] = GCPConfig.INSTANCE_TYPES

    # --- INITIALISATION ---
    def load_history(self):
        """Récupère l'historique depuis Supabase au chargement"""
        if Config.SUPABASE_URL and Config.SUPABASE_SERVICE_KEY:
            try:
                sb = create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_KEY)
                response = sb.table("cost_history").select("*").order("created_at", desc=True).execute()
                # On formate un peu les données pour l'affichage
                raw_data = response.data
                for item in raw_data:
                    # On arrondit pour l'affichage propre
                    item["total_monthly_cost"] = round(float(item["total_monthly_cost"]), 2)
                    # On simplifie la date (juste YYYY-MM-DD HH:MM)
                    if "T" in item["created_at"]:
                         item["display_date"] = item["created_at"].split("T")[0]
                    else:
                         item["display_date"] = item["created_at"]
                
                self.history = raw_data
            except Exception as e:
                print(f"Erreur Supabase: {e}")

    # --- COMPUTED VARS (Simulateur) ---
    @rx.var
    def budget_status_color(self) -> str:
        if self.cost == 0: return "gray"
        return "green" if self.cost <= Config.DEFAULT_BUDGET_LIMIT else "red"

    @rx.var
    def budget_accent_color(self) -> str:
        if self.cost == 0: return "gray"
        return "grass" if self.cost <= Config.DEFAULT_BUDGET_LIMIT else "tomato"

    @rx.var
    def budget_icon(self) -> str:
        if self.cost == 0: return "minus"
        return "check" if self.cost <= Config.DEFAULT_BUDGET_LIMIT else "alert-triangle"

    @rx.var
    def budget_label(self) -> str:
        if self.cost == 0: return "En attente"
        return "Budget Respecté" if self.cost <= Config.DEFAULT_BUDGET_LIMIT else "Budget Dépassé"

    @rx.var
    def chart_data(self) -> List[Dict]:
        if not self.details or 'projects' not in self.details: return []
        data = []
        try:
            resources = self.details['projects'][0]['breakdown']['resources']
            for res in resources:
                c_str = res.get('monthlyCost') or res.get('totalMonthlyCost')
                if c_str:
                    try:
                        val = float(c_str)
                        if val > 0:
                            name = "Compute" if "instance" in res['name'] else ("Stockage" if "disk" in res['name'] else "Autre")
                            data.append({"name": name, "value": val})
                    except: pass
        except: pass
        return data

    # --- COMPUTED VARS (Gouvernance) ---
    @rx.var
    def last_run_cost(self) -> str:
        if not self.history: return "0.00 $"
        return f"{self.history[0]['total_monthly_cost']} $"

    @rx.var
    def last_run_status(self) -> str:
        if not self.history: return "Inconnu"
        return "Conforme" if self.history[0]['status'] == 'PASSED' else "Non Conforme"

    @rx.var
    def last_run_color(self) -> str:
        if not self.history: return "gray"
        return "grass" if self.history[0]['status'] == 'PASSED' else "tomato"

    # --- ACTIONS ---
    def set_region(self, value: str): self.region = value
    def set_instance_type(self, value: str): self.instance_type = value
    def set_storage_value(self, value: List[float]): self.storage = int(value[0])

    def run_simulation(self):
        self.is_loading = True
        self.error_msg = ""
        yield
        try:
            sim = InfracostSimulator()
            result = sim.simulate(self.instance_type, self.region, self.storage)
            if result.success:
                self.cost = result.monthly_cost
                self.details = result.details
            else:
                self.error_msg = result.error_message
                self.cost = 0.0     
        except Exception as e:
            self.error_msg = str(e)
        finally:
            self.is_loading = False