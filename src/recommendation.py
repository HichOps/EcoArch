"""Moteur de recommandation d'infrastructure GCP."""
from typing import Any


# Mapping workload -> type de machine
WORKLOAD_MACHINES = {
    "cpu": "e2-highcpu-2",
    "memory": "e2-highmem-2",
    "general": "e2-medium",
}

# Configuration par environnement
ENV_CONFIG = {
    "dev": {"machine": "e2-micro", "disk": 20, "db_tier": "db-f1-micro"},
    "prod": {"machine": None, "disk": 50, "db_tier": "db-g1-small"},  # machine définie par workload
}

# Mapping type d'application -> stack logicielle recommandée
APP_TYPE_STACKS = {
    "web": "web-nginx",
    "api": "nodejs",
    "backend": "python-django",
    "batch": "docker",
    "microservices": "docker",
}


class RecommendationEngine:
    """Génère des recommandations d'infrastructure basées sur les besoins."""
    
    @staticmethod
    def generate(answers: dict[str, str]) -> list[dict[str, Any]]:
        """Génère une liste de ressources recommandées."""
        env = answers.get("environment", "dev")
        traffic = answers.get("traffic", "low")
        workload = answers.get("workload", "general")
        criticality = answers.get("criticality", "low")
        app_type = answers.get("type", "web")
        
        # Haute disponibilité si PROD + (trafic élevé OU critique)
        is_ha = env == "prod" and (traffic == "high" or criticality == "high")
        
        resources = []
        
        # 1. COMPUTE
        resources.extend(
            RecommendationEngine._generate_compute(env, workload, is_ha, app_type)
        )
        
        # 2. LOAD BALANCER (si HA)
        if is_ha:
            resources.append({
                "type": "load_balancer",
                "display_name": "Global Load Balancer (HTTP)",
            })
        
        # 3. DATABASE (sauf pour batch pur)
        if answers.get("type") != "batch":
            resources.append(
                RecommendationEngine._generate_database(env, is_ha)
            )
        
        # 4. STORAGE
        storage_class = "MULTI_REGIONAL" if is_ha else "STANDARD"
        resources.append({
            "type": "storage",
            "storage_class": storage_class,
            "display_name": f"Assets Bucket ({storage_class})",
        })
        
        return resources
    
    @staticmethod
    def _generate_compute(env: str, workload: str, is_ha: bool, app_type: str = "web") -> list[dict]:
        """Génère les ressources Compute."""
        config = ENV_CONFIG.get(env, ENV_CONFIG["dev"])
        machine = config["machine"] or WORKLOAD_MACHINES.get(workload, "e2-medium")
        disk = config["disk"]
        software_stack = APP_TYPE_STACKS.get(app_type, "none")
        
        instance_count = 2 if is_ha else 1
        
        return [
            {
                "type": "compute",
                "machine_type": machine,
                "disk_size": disk,
                "software_stack": software_stack,
                "display_name": f"App Server{f' (Replica {i+1})' if is_ha else ''} [{machine}]",
            }
            for i in range(instance_count)
        ]
    
    @staticmethod
    def _generate_database(env: str, is_ha: bool) -> dict:
        """Génère la ressource Database."""
        if env == "dev":
            return {
                "type": "sql",
                "db_tier": "db-f1-micro",
                "db_version": "POSTGRES_15",
                "display_name": "PostgreSQL (Dev)",
            }
        
        if is_ha:
            return {
                "type": "sql",
                "db_tier": "db-custom-2-3840",
                "db_version": "POSTGRES_15",
                "display_name": "PostgreSQL (Regional HA)",
            }
        
        return {
            "type": "sql",
            "db_tier": "db-g1-small",
            "db_version": "POSTGRES_15",
            "display_name": "PostgreSQL (Standard)",
        }