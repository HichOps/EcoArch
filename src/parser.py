import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from supabase import create_client, Client

class EcoArchParser:
    def __init__(self, json_path: str):
        """Initialise le parser et vérifie l'existence du fichier source."""
        self.json_path = Path(json_path)
        
        if not self.json_path.exists():
            print(f"❌ Erreur critique : Le fichier '{json_path}' est introuvable.")
            print("💡 Vérifiez que le job 'infracost_analysis' a bien généré ce rapport.")
            sys.exit(1)
            
        self.data = self._load_data()
        self.resources = self._flatten_resources()

    def _load_data(self) -> Dict[str, Any]:
        """Charge le contenu JSON du rapport Infracost."""
        with open(self.json_path, 'r') as f:
            return json.load(f)

    def _flatten_resources(self) -> List[Dict[str, Any]]:
        """Extrait et aplatit la liste des ressources pour faciliter l'analyse."""
        flattened = []
        projects = self.data.get("projects", [])
        for project in projects:
            breakdown = project.get("breakdown", {})
            resources = breakdown.get("resources", [])
            for res in resources:
                flattened.append({
                    "name": res.get("name"),
                    "monthly_cost": float(res.get("monthlyCost", 0)),
                    "past_monthly_cost": float(res.get("pastMonthlyCost", 0)),
                    "delta": float(res.get("diffMonthlyCost", 0)),
                    "metadata": res.get("metadata", {})
                })
        return flattened

    def extract_metrics(self) -> Dict[str, Any]:
        """Extrait les métriques financières globales du run."""
        return {
            "total_monthly_cost": float(self.data.get("totalMonthlyCost", 0)),
            "diff_monthly_cost": float(self.data.get("diffTotalMonthlyCost", 0)),
            "currency": self.data.get("currency", "USD")
        }

    def save_to_supabase(self):
        """Sauvegarde les résultats du run dans Supabase avec les métadonnées de la CI."""
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            print("⏭️ Supabase credentials not found, skipping persistence.")
            return

        # Connexion au client Supabase
        supabase: Client = create_client(url, key)
        metrics = self.extract_metrics()
        
        # Récupération de la limite budgétaire (défaut à 100.0)
        limit = float(os.getenv("ECOARCH_BUDGET_LIMIT", 100.0))
        status = "PASSED" if metrics["total_monthly_cost"] <= limit else "FAILED"

        # Préparation de l'enregistrement aligné sur l'architecture SQL
        record = {
            "project_id": os.getenv("CI_PROJECT_NAME", "ecoarch-local"),
            "branch_name": os.getenv("CI_COMMIT_REF_NAME", "local"),
            "commit_sha": os.getenv("CI_COMMIT_SHORT_SHA", "HEAD"),
            "author": os.getenv("CI_COMMIT_AUTHOR", "Unknown"),
            "total_monthly_cost": metrics["total_monthly_cost"],
            "diff_monthly_cost": metrics["diff_monthly_cost"],
            "currency": metrics["currency"],
            "budget_limit": limit,
            "status": status
        }

        try:
            # Insertion dans la table cost_history
            supabase.table("cost_history").insert(record).execute()
            print(f"✅ Data persisted to Supabase (Status: {status})")
        except Exception as e:
            print(f"❌ Failed to persist data to Supabase: {e}")

    def generate_markdown_report(self) -> str:
        """Génère le corps du rapport pour le bot GitLab."""
        metrics = self.extract_metrics()
        report = [
            f"## 🛠️ EcoArch FinOps Analysis",
            f"**Total Monthly Estimate:** `{metrics['total_monthly_cost']:.2f} {metrics['currency']}`\n",
            "### 🏆 Top 3 Expensive Resources",
            "| Resource | Monthly Cost |",
            "| :--- | :--- |"
        ]
        
        # Tri des ressources par coût décroissant
        sorted_res = sorted(self.resources, key=lambda x: x['monthly_cost'], reverse=True)[:3]
        for res in sorted_res:
            report.append(f"| `{res['name']}` | {res['monthly_cost']:.2f} {metrics['currency']} |")

        return "\n".join(report)

if __name__ == "__main__":
    try:
        # Fichier généré par la commande Infracost dans le job précédent
        parser = EcoArchParser("infracost-report.json")
        
        # 1. Génération du rapport texte (sera capturé par report.md dans le CI)
        print(parser.generate_markdown_report())
        
        # 2. Persistance dans la base de données
        parser.save_to_supabase()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)