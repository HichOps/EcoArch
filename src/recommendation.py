from typing import List, Dict, Any

class RecommendationEngine:
    """
    Architecte Virtuel V3 : Haute Disponibilité & Load Balancing
    """

    @staticmethod
    def generate(answers: Dict[str, str]) -> List[Dict[str, Any]]:
        resources = []
        
        env = answers.get("environment", "dev")
        traffic = answers.get("traffic", "low")
        workload = answers.get("workload", "general")
        criticality = answers.get("criticality", "low")

        # --- LOGIQUE HA (High Availability) ---
        # On active la HA si c'est la PROD et que (Trafic Haut OU Critique)
        is_ha = env == "prod" and (traffic == "high" or criticality == "high")
        
        # Nombre d'instances (Redondance)
        instance_count = 2 if is_ha else 1

        # --- 1. COMPUTE (Les VMs) ---
        if env == "dev":
            machine = "e2-micro"
            disk = 20
        else:
            if workload == "cpu": machine = "e2-highcpu-2"
            elif workload == "memory": machine = "e2-highmem-2"
            else: machine = "e2-medium"
            disk = 50

        # On ajoute les VMs (1 ou 2 selon HA)
        for i in range(instance_count):
            suffix = f" (Replica {i+1})" if is_ha else ""
            resources.append({
                "type": "compute",
                "machine_type": machine,
                "disk_size": disk,
                "display_name": f"App Server{suffix} [{machine}]"
            })

        # --- 2. NETWORK (Le Load Balancer) ---
        # Si on a plusieurs instances, il faut un LB pour répartir le trafic
        if is_ha:
            resources.append({
                "type": "load_balancer",
                "display_name": "Global Load Balancer (HTTP)"
            })

        # --- 3. DATABASE ---
        db_tier = "db-f1-micro"
        if env == "prod":
            # Si HA, on prend une base robuste (simulée ici par le tier custom)
            if is_ha:
                db_tier = "db-custom-2-3840" 
                db_display = "PostgreSQL (Regional HA)"
            else:
                db_tier = "db-g1-small"
                db_display = "PostgreSQL (Standard)"
        else:
            db_display = "PostgreSQL (Dev)"

        if answers.get("type") != "batch": # Pas de DB pour du batch pur
            resources.append({
                "type": "sql",
                "db_tier": db_tier,
                "db_version": "POSTGRES_15",
                "display_name": db_display
            })

        # --- 4. STORAGE ---
        storage_class = "MULTI_REGIONAL" if is_ha else "STANDARD"
        resources.append({
            "type": "storage",
            "storage_class": storage_class,
            "display_name": f"Assets Bucket ({storage_class})"
        })

        return resources