import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration globale"""
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "simulation-project")
    DEFAULT_REGION = os.getenv("GCP_REGION", "europe-west1")
    DEFAULT_IMAGE = "debian-cloud/debian-11"
    
    DEFAULT_BUDGET_LIMIT = float(os.getenv("ECOARCH_BUDGET_LIMIT", "50.0"))
    
    INFRACOST_API_KEY = os.getenv("INFRACOST_API_KEY")
    INFRACOST_TIMEOUT = int(os.getenv("INFRACOST_TIMEOUT", "30"))
    TEMP_FILE_PREFIX = "ecoarch_sim_"
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class GCPConfig:
    """Listes de choix techniques"""
    REGIONS = [
        "europe-west1", "europe-west9", "us-central1", "us-east1", "asia-northeast1"
    ]
    
    # VM (Compute Engine)
    INSTANCE_TYPES = [
        "e2-micro", "e2-small", "e2-medium", "e2-standard-2", 
        "e2-standard-4", "n1-standard-1", "n2-standard-2", "c2-standard-4"
    ]
    
    # Database (Cloud SQL) - NOUVEAU !
    DB_TIERS = [
        "db-f1-micro", "db-g1-small", "db-custom-1-3840", 
        "db-custom-2-7680", "db-custom-4-15360"
    ]
    DB_VERSIONS = ["POSTGRES_13", "POSTGRES_14", "POSTGRES_15"]

    # STORAGE (Google Cloud Storage) - NOUVEAU !
    STORAGE_CLASSES = [
        "STANDARD",
        "NEARLINE",
        "COLDLINE",
        "ARCHIVE"
    ]
    
    MIN_STORAGE_GB = 10
    MAX_STORAGE_GB = 64000