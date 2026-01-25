import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Configuration globale"""
    GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "simulation-project")
    
    # MODIFICATION : Passage en US Central1 (Iowa) pour réduire les coûts
    DEFAULT_REGION = os.getenv("GCP_REGION", "us-central1")
    DEFAULT_IMAGE = "debian-cloud/debian-11"
    
    # MODIFICATION : Ajout du nom de votre bucket d'état Terraform
    TERRAFORM_STATE_BUCKET = "ecoarch-tfstate-514436528658"
    
    DEFAULT_BUDGET_LIMIT = float(os.getenv("ECOARCH_BUDGET_LIMIT", "50.0"))
    
    INFRACOST_API_KEY = os.getenv("INFRACOST_API_KEY")
    INFRACOST_TIMEOUT = int(os.getenv("INFRACOST_TIMEOUT", "30"))
    TEMP_FILE_PREFIX = "ecoarch_sim_"
    
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

class GCPConfig:
    """Listes de choix techniques"""
    # Mise à jour de la liste pour mettre en avant les régions US moins chères
    REGIONS = [
        "us-central1", # Iowa (Souvent la moins chère)
        "us-east1",    # South Carolina
        "europe-west1", 
        "europe-west9", 
        "asia-northeast1"
    ]
    
    # VM (Compute Engine)
    INSTANCE_TYPES = [
        "e2-micro", "e2-small", "e2-medium", "e2-standard-2", 
        "e2-standard-4", "n1-standard-1", "n2-standard-2", "c2-standard-4"
    ]
    
    # Database (Cloud SQL)
    DB_TIERS = [
        "db-f1-micro", "db-g1-small", "db-custom-1-3840", 
        "db-custom-2-7680", "db-custom-4-15360"
    ]
    DB_VERSIONS = ["POSTGRES_13", "POSTGRES_14", "POSTGRES_15"]

    # STORAGE (Google Cloud Storage)
    STORAGE_CLASSES = [
        "STANDARD",
        "NEARLINE",
        "COLDLINE",
        "ARCHIVE"
    ]
    
    MIN_STORAGE_GB = 10
    MAX_STORAGE_GB = 64000