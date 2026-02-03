"""Configuration centralisée de l'application EcoArch."""
import os
from dotenv import load_dotenv

load_dotenv()


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


class Config:
    """Configuration globale de l'application."""
    
    # GCP
    GCP_PROJECT_ID = _get_env("GCP_PROJECT_ID", "simulation-project")
    DEFAULT_REGION = _get_env("GCP_REGION", "us-central1")
    DEFAULT_IMAGE = "debian-cloud/debian-11"
    TERRAFORM_STATE_BUCKET = "ecoarch-tfstate-514436528658"
    
    # Budget
    DEFAULT_BUDGET_LIMIT = _get_env_float("ECOARCH_BUDGET_LIMIT", 50.0)
    
    # Infracost
    INFRACOST_API_KEY = _get_env("INFRACOST_API_KEY")
    INFRACOST_TIMEOUT = _get_env_int("INFRACOST_TIMEOUT", 30)
    TEMP_FILE_PREFIX = "ecoarch_sim_"
    
    # Supabase
    SUPABASE_URL = _get_env("SUPABASE_URL")
    SUPABASE_SERVICE_KEY = _get_env("SUPABASE_SERVICE_KEY")

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
debconf-set-selections <<< 'mysql-server mysql-server/root_password password root'
debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password root'
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
debconf-set-selections <<< 'mysql-server mysql-server/root_password password root'
debconf-set-selections <<< 'mysql-server mysql-server/root_password_again password root'
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
    MAX_STORAGE_GB = 64000