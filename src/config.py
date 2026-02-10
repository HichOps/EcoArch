"""Configuration centralisée de l'application EcoArch."""
import logging
import os
from dotenv import load_dotenv

load_dotenv(override=False)  # Les variables Secret Manager / Cloud Run ont priorité

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────


def _get_env(key: str, default: str = "") -> str:
    """Récupère une variable d'environnement avec valeur par défaut."""
    return os.getenv(key, default)


def _get_env_float(key: str, default: float) -> float:
    """Récupère une variable d'environnement comme float."""
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def _get_env_int(key: str, default: int) -> int:
    """Récupère une variable d'environnement comme int."""
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


# ── GCP Secret Manager ───────────────────────────────────────────

def _is_running_in_gcp() -> bool:
    """Détecte si l'application tourne dans un environnement GCP (Cloud Run, GCE, GKE)."""
    return bool(
        os.getenv("K_SERVICE")                    # Cloud Run
        or os.getenv("GOOGLE_CLOUD_PROJECT")       # GCE / GKE
        or os.getenv("GCLOUD_PROJECT")             # Legacy
    )


def _get_secret(secret_id: str, project_id: str | None = None) -> str | None:
    """Récupère un secret depuis GCP Secret Manager.

    Retourne None si :
    - On n'est pas dans GCP
    - Le secret n'existe pas
    - La librairie n'est pas installée
    """
    if not _is_running_in_gcp():
        return None

    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        gcp_project = project_id or os.getenv("GCP_PROJECT_ID", "")
        name = f"projects/{gcp_project}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception as exc:
        logger.warning("Secret Manager: impossible de lire '%s' – %s", secret_id, exc)
        return None


def _get_secret_or_env(secret_id: str, env_key: str, default: str = "") -> str:
    """Essaie Secret Manager d'abord, sinon variable d'environnement."""
    value = _get_secret(secret_id)
    if value:
        return value
    return os.getenv(env_key, default)


class Config:
    """Configuration globale de l'application."""
    
    # GCP
    GCP_PROJECT_ID = _get_env("GCP_PROJECT_ID", "simulation-project")
    DEFAULT_REGION = _get_env("GCP_REGION", "us-central1")
    DEFAULT_IMAGE = "debian-cloud/debian-11"
    TERRAFORM_STATE_BUCKET = "ecoarch-tfstate-514436528658"
    
    # Budget
    DEFAULT_BUDGET_LIMIT = _get_env_float("ECOARCH_BUDGET_LIMIT", 50.0)
    
    # Infracost (clé sensible → Secret Manager en prod)
    INFRACOST_API_KEY = _get_secret_or_env("infracost-api-key", "INFRACOST_API_KEY")
    INFRACOST_TIMEOUT = _get_env_int("INFRACOST_TIMEOUT", 30)
    TEMP_FILE_PREFIX = "ecoarch_sim_"
    
    # Supabase (secrets sensibles → Secret Manager en prod)
    SUPABASE_URL = _get_secret_or_env("supabase-url", "SUPABASE_URL")
    SUPABASE_SERVICE_KEY = _get_secret_or_env("supabase-service-key", "SUPABASE_SERVICE_KEY")

    # GitLab CI/CD (secrets sensibles → Secret Manager en prod)
    GITLAB_TRIGGER_TOKEN = _get_secret_or_env(
        "GITLAB_TRIGGER_TOKEN", "GITLAB_TRIGGER_TOKEN"
    )
    GITLAB_PROJECT_ID = _get_secret_or_env(
        "GITLAB_PROJECT_ID", "GITLAB_PROJECT_ID", default="77811562"
    )
    GITLAB_REF = _get_env("GITLAB_REF", "main")
    GITLAB_PIPELINE_BASE_URL = (
        f"https://gitlab.com/api/v4/projects/{GITLAB_PROJECT_ID}/trigger/pipeline"
    )
    GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

    # Redis / Celery (legacy – non utilisé sur Cloud Run)
    REDIS_URL = _get_env("REDIS_URL", "redis://localhost:6379/0")

class GCPConfig:
    """Options disponibles pour les ressources GCP."""
    
    # Régions (triées par coût croissant)
    REGIONS = [
        "us-central1",      # Iowa - Moins cher
        "us-east1",         # South Carolina
        "europe-west1",     # Belgique
        "europe-west9",     # Paris
        "asia-northeast1",  # Tokyo
    ]
    
    # Compute Engine - Types de machines
    INSTANCE_TYPES = [
        "e2-micro", "e2-small", "e2-medium",
        "e2-standard-2", "e2-standard-4",
        "n1-standard-1", "n2-standard-2", "c2-standard-4",
    ]
    
    # Cloud SQL - Tiers et versions
    DB_TIERS = [
        "db-f1-micro", "db-g1-small",
        "db-custom-1-3840", "db-custom-2-7680", "db-custom-4-15360",
    ]
    DB_VERSIONS = ["POSTGRES_13", "POSTGRES_14", "POSTGRES_15"]
    
    # Cloud Storage - Classes
    STORAGE_CLASSES = ["STANDARD", "NEARLINE", "COLDLINE", "ARCHIVE"]
    
    # Limites de stockage
    MIN_STORAGE_GB = 10
    MAX_STORAGE_GB = 64000
    
    # Software Stacks - Logiciels pré-installés
    SOFTWARE_STACKS: dict[str, dict[str, str]] = {
        "none": {
            "name": "Aucun (VM vide)",
            "description": "Instance sans logiciel pré-installé",
            "script": "",
        },
        "web-nginx": {
            "name": "Serveur Web (Nginx)",
            "description": "Nginx + Certbot pour HTTPS",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
apt-get install -y nginx certbot python3-certbot-nginx
systemctl enable nginx
systemctl start nginx
echo "Nginx installed successfully" > /var/log/startup-script.log
""",
        },
        "web-apache": {
            "name": "Serveur Web (Apache)",
            "description": "Apache2 + mod_ssl",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
apt-get install -y apache2 certbot python3-certbot-apache
a2enmod ssl rewrite
systemctl enable apache2
systemctl start apache2
echo "Apache installed successfully" > /var/log/startup-script.log
""",
        },
        "nodejs": {
            "name": "Node.js Runtime",
            "description": "Node.js 20 LTS + npm + PM2",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs
npm install -g pm2
pm2 startup systemd
echo "Node.js $(node -v) installed successfully" > /var/log/startup-script.log
""",
        },
        "python-django": {
            "name": "Python Django",
            "description": "Python 3.11 + Django + Gunicorn + Nginx",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
apt-get install -y python3.11 python3.11-venv python3-pip nginx
pip3 install django gunicorn
systemctl enable nginx
systemctl start nginx
echo "Python Django stack installed successfully" > /var/log/startup-script.log
""",
        },
        "python-flask": {
            "name": "Python Flask",
            "description": "Python 3.11 + Flask + Gunicorn",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
apt-get install -y python3.11 python3.11-venv python3-pip
pip3 install flask gunicorn
echo "Python Flask stack installed successfully" > /var/log/startup-script.log
""",
        },
        "docker": {
            "name": "Docker",
            "description": "Docker Engine + Docker Compose",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
apt-get install -y ca-certificates curl gnupg
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release && echo $VERSION_CODENAME) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker
echo "Docker installed successfully" > /var/log/startup-script.log
""",
        },
        "lamp": {
            "name": "LAMP Stack",
            "description": "Linux + Apache + MySQL + PHP",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
MYSQL_ROOT_PWD=$(gcloud secrets versions access latest --secret=mysql-root-password --project="$GCP_PROJECT_ID" 2>/dev/null || echo "changeme-$(head -c 16 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')")
debconf-set-selections <<< "mysql-server mysql-server/root_password password $MYSQL_ROOT_PWD"
debconf-set-selections <<< "mysql-server mysql-server/root_password_again password $MYSQL_ROOT_PWD"
apt-get install -y apache2 mysql-server php libapache2-mod-php php-mysql
systemctl enable apache2 mysql
systemctl start apache2 mysql
echo "LAMP stack installed successfully" > /var/log/startup-script.log
""",
        },
        "lemp": {
            "name": "LEMP Stack",
            "description": "Linux + Nginx + MySQL + PHP-FPM",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y
MYSQL_ROOT_PWD=$(gcloud secrets versions access latest --secret=mysql-root-password --project="$GCP_PROJECT_ID" 2>/dev/null || echo "changeme-$(head -c 16 /dev/urandom | base64 | tr -dc 'a-zA-Z0-9')")
debconf-set-selections <<< "mysql-server mysql-server/root_password password $MYSQL_ROOT_PWD"
debconf-set-selections <<< "mysql-server mysql-server/root_password_again password $MYSQL_ROOT_PWD"
apt-get install -y nginx mysql-server php-fpm php-mysql
systemctl enable nginx mysql php*-fpm
systemctl start nginx mysql php*-fpm
echo "LEMP stack installed successfully" > /var/log/startup-script.log
""",
        },
        "monitoring": {
            "name": "Monitoring Stack",
            "description": "Prometheus + Node Exporter + Grafana",
            "script": """#!/bin/bash
set -e
apt-get update && apt-get upgrade -y

# Node Exporter
useradd --no-create-home --shell /bin/false node_exporter || true
wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
tar xzf node_exporter-1.6.1.linux-amd64.tar.gz
cp node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/
rm -rf node_exporter-*

# Grafana
apt-get install -y apt-transport-https software-properties-common
wget -q -O - https://packages.grafana.com/gpg.key | apt-key add -
echo "deb https://packages.grafana.com/oss/deb stable main" | tee /etc/apt/sources.list.d/grafana.list
apt-get update
apt-get install -y grafana
systemctl enable grafana-server
systemctl start grafana-server

echo "Monitoring stack installed successfully" > /var/log/startup-script.log
""",
        },
    }
    
    @classmethod
    def get_stack_names(cls) -> list[str]:
        """Retourne la liste des identifiants de stacks."""
        return list(cls.SOFTWARE_STACKS.keys())
    
    @classmethod
    def get_stack_display_names(cls) -> list[tuple[str, str]]:
        """Retourne les tuples (id, nom_affichage) pour les stacks."""
        return [(k, v["name"]) for k, v in cls.SOFTWARE_STACKS.items()]
    
    @classmethod
    def get_startup_script(cls, stack_id: str) -> str:
        """Retourne le script de démarrage pour une stack donnée."""
        return cls.SOFTWARE_STACKS.get(stack_id, {}).get("script", "")