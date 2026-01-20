"""
Configuration centralisée pour EcoArch.
Toutes les constantes et variables de configuration sont définies ici.
"""
import os
from typing import List
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Configuration globale de l'application."""
    
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
    # GCP Simulation
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "simulation-project")
    DEFAULT_IMAGE = "debian-cloud/debian-11"
    
    # Budget
    DEFAULT_BUDGET_LIMIT = float(os.getenv("BUDGET_LIMIT", "50.0"))
    
    # Infracost
    INFRACOST_TIMEOUT = int(os.getenv("INFRACOST_TIMEOUT", "30"))  # secondes
    
    # Simulation
    TEMP_FILE_PREFIX = "ecoarch_simulation_"
    

class GCPConfig:
    """Configuration spécifique GCP."""
    
    REGIONS: List[str] = [
        "us-central1",
        "europe-west1",
        "europe-west9",
        "asia-east1"
    ]
    
    INSTANCE_TYPES: List[str] = [
        "e2-micro",
        "e2-small",
        "e2-medium",
        "n2-standard-2",
        "n2-standard-4",
        "n2-standard-8",
        "c2-standard-4"
    ]
    
    DEFAULT_INSTANCE = "e2-medium"
    DEFAULT_REGION = "europe-west1"
    
    # Limites
    MIN_STORAGE_GB = 10
    MAX_STORAGE_GB = 1000
    DEFAULT_STORAGE_GB = 20
