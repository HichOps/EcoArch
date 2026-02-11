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

# Intensité carbone par région (gCO2eq/kWh, catégorisée)
GCP_CARBON_INTENSITY = {
    # Low carbon
    "europe-west1": "low",      # Belgique
    "europe-north1": "low",     # Finlande
    "europe-west9": "low",      # Paris
    "northamerica-northeast1": "low",  # Montréal (approx canada-central1)
    "canada-central1": "low",
    # Medium
    "europe-west4": "medium",   # Pays-Bas
    "us-central1": "medium",
    # High
    "europe-central2": "high",  # Varsovie
    "us-east4": "high",         # Virginie
}

_REGION_FACTORS = {
    "low": 0.8,
    "medium": 1.0,
    "high": 1.2,
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

    # ── Sobriety / Green Score ─────────────────────────────────────

    @staticmethod
    def calculate_sobriety_score(
        resources: list[dict[str, Any]],
        environment: str = "dev",
        region: str = "us-central1",
    ) -> str:
        """Calcule une note de sobriété de A (très sobre) à E (très gourmand).

        Heuristique simple basée sur :
        - vCPU total estimé (machine_type)
        - RAM approximative
        - nombre de VMs et type de storage
        - bonus de sobriété pour l'environnement 'dev'
        """
        if not resources:
            return "A"

        # Approximation vCPU/RAM par famille de machine
        def _machine_profile(machine_type: str) -> tuple[int, int]:
            mt = machine_type.lower()
            if mt.startswith("e2-micro"):
                return 0, 1
            if mt.startswith("e2-small"):
                return 1, 2
            if mt.startswith("e2-medium"):
                return 2, 4
            if "highcpu" in mt:
                return 2, 2
            if "highmem" in mt:
                return 2, 8
            if mt.startswith(("n1-", "n2-", "c2-")):
                return 4, 16
            return 2, 4

        total_vcpu = 0
        total_ram_gb = 0
        storage_penalty = 0.0

        for res in resources:
            rtype = res.get("type")
            if rtype == "compute":
                machine = str(res.get("machine_type", "e2-medium"))
                vcpu, ram = _machine_profile(machine)
                total_vcpu += vcpu
                total_ram_gb += ram
            elif rtype == "storage":
                storage_class = str(res.get("storage_class", "STANDARD"))
                if storage_class == "MULTI_REGIONAL":
                    storage_penalty += 1.0

        # Score brut basé sur vCPU/ram
        score = 0.0
        if total_vcpu <= 2:
            score += 0
        elif total_vcpu <= 4:
            score += 1
        elif total_vcpu <= 8:
            score += 2
        else:
            score += 3

        if total_ram_gb <= 8:
            score += 0
        elif total_ram_gb <= 32:
            score += 1
        else:
            score += 2

        score += storage_penalty

        # Bonus sobriété pour l'environnement dev
        if environment == "dev":
            score = max(0.0, score - 1.0)

        # Facteur d'intensité carbone par région
        category = GCP_CARBON_INTENSITY.get(region, "medium")
        factor = _REGION_FACTORS.get(category, 1.0)
        score *= factor

        # Mapping score -> lettre
        if score <= 1:
            return "A"
        if score <= 2:
            return "B"
        if score <= 3:
            return "C"
        if score <= 4:
            return "D"
        return "E"

    @staticmethod
    def is_high_carbon_region(region: str) -> bool:
        """Retourne True si la région est classée 'high' en intensité carbone."""
        return GCP_CARBON_INTENSITY.get(region, "medium") == "high"

    @staticmethod
    def get_green_alternative(region: str) -> str | None:
        """Retourne une région low-carbon recommandée en alternative.

        Le mapping privilégie des voisins géographiques raisonnables.
        """
        # Si déjà low/medium, pas d'alternative nécessaire
        category = GCP_CARBON_INTENSITY.get(region, "medium")
        if category != "high":
            return None

        # Mappage explicite pour les régions connues
        explicit_map: dict[str, str] = {
            "us-east4": "canada-central1",
            "europe-central2": "europe-west1",
        }
        if region in explicit_map:
            return explicit_map[region]

        # Fallback générique pour toute autre région high-carbon
        return "europe-west9"