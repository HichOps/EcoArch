import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

class EcoArchParser:
    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        if not self.json_path.exists():
            raise FileNotFoundError(f"Fichier non trouvé : {json_path}")
        self.data = self._load_data()
        # Extraction à plat de toutes les ressources pour faciliter le tri
        self.resources = self._flatten_resources()

    def _load_data(self) -> Dict[str, Any]:
        with open(self.json_path, 'r') as f:
            return json.load(f)

    def _flatten_resources(self) -> List[Dict[str, Any]]:
        """Extrait toutes les ressources des différents projets Infracost."""
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
        """
        Extrait les métriques globales. 
        Cette méthode est requise par pytest et budget_gate.py.
        """
        return {
            "total_monthly_cost": float(self.data.get("totalMonthlyCost", 0)),
            "diff_monthly_cost": float(self.data.get("diffTotalMonthlyCost", 0)),
            "currency": self.data.get("currency", "USD")
        }

    def get_top_expensive(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Retourne le Top N des ressources les plus coûteuses."""
        sorted_res = sorted(self.resources, key=lambda x: x['monthly_cost'], reverse=True)
        return sorted_res[:limit]

    def get_biggest_increase(self) -> Optional[Dict[str, Any]]:
        """Identifie la ressource avec la plus forte augmentation absolue."""
        if not self.resources:
            return None
        return max(self.resources, key=lambda x: x['delta'])

    def generate_markdown_report(self) -> str:
        """Génère un rapport détaillé au format Markdown pour GitLab."""
        top_3 = self.get_top_expensive(3)
        increase = self.get_biggest_increase()
        metrics = self.extract_metrics()

        report = [
            f"## 🛠️ EcoArch FinOps Analysis",
            f"**Total Monthly Estimate:** `{metrics['total_monthly_cost']:.2f} {metrics['currency']}`\n",
            "### 🏆 Top 3 Expensive Resources",
            "| Resource | Monthly Cost |",
            "| :--- | :--- |"
        ]
        
        for res in top_3:
            report.append(f"| `{res['name']}` | {res['monthly_cost']:.2f} {metrics['currency']} |")

        if increase and increase['delta'] > 0:
            report.append("\n### ⚠️ Highest Increase")
            report.append(f"Resource `{increase['name']}` increased by **{increase['delta']:.2f} {metrics['currency']}**")

        return "\n".join(report)

if __name__ == "__main__":
    try:
        # On s'attend à ce que le fichier soit dans le répertoire courant
        parser = EcoArchParser("infracost-report.json")
        print(parser.generate_markdown_report())
    except Exception as e:
        print(f"Error parsing Infracost report: {e}")
        sys.exit(1)