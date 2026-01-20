import json
import sys
import os
from pathlib import Path
from typing import Dict, Any, List
from supabase import create_client, Client

class EcoArchParser:
    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        if not self.json_path.exists():
            print(f"❌ Erreur : Le fichier '{json_path}' est introuvable.")
            sys.exit(1)
        self.data = self._load_data()
        self.resources = self._flatten_resources()

    def _load_data(self) -> Dict[str, Any]:
        with open(self.json_path, 'r') as f:
            return json.load(f)

    def _safe_float(self, value: Any) -> float:
        """Convertit en float en gérant les valeurs nulles ou manquantes."""
        try:
            return float(value) if value is not None else 0.0
        except (ValueError, TypeError):
            return 0.0

    def _flatten_resources(self) -> List[Dict[str, Any]]:
        flattened = []
        projects = self.data.get("projects", []) or []
        for project in projects:
            breakdown = project.get("breakdown", {}) or {}
            resources = breakdown.get("resources", []) or []
            for res in resources:
                flattened.append({
                    "name": res.get("name"),
                    "monthly_cost": self._safe_float(res.get("monthlyCost")),
                    "delta": self._safe_float(res.get("diffMonthlyCost"))
                })
        return flattened

    def extract_metrics(self) -> Dict[str, Any]:
        return {
            "total_monthly_cost": self._safe_float(self.data.get("totalMonthlyCost")),
            "diff_monthly_cost": self._safe_float(self.data.get("diffTotalMonthlyCost")),
            "currency": self.data.get("currency", "USD")
        }

    def save_to_supabase(self):
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        if not url or not key:
            print("⏭️ Supabase credentials non trouvées (Variable Protected ?).")
            return

        try:
            supabase = create_client(url, key)
            metrics = self.extract_metrics()
            limit = float(os.getenv("ECOARCH_BUDGET_LIMIT", 100.0))
            
            record = {
                "project_id": os.getenv("CI_PROJECT_NAME", "ecoarch-local"),
                "branch_name": os.getenv("CI_COMMIT_REF_NAME", "local"),
                "commit_sha": os.getenv("CI_COMMIT_SHORT_SHA", "HEAD"),
                "author": os.getenv("CI_COMMIT_AUTHOR", "Unknown"),
                "total_monthly_cost": metrics["total_monthly_cost"],
                "diff_monthly_cost": metrics["diff_monthly_cost"],
                "currency": metrics["currency"],
                "budget_limit": limit,
                "status": "PASSED" if metrics["total_monthly_cost"] <= limit else "FAILED"
            }
            supabase.table("cost_history").insert(record).execute()
            print(f"✅ Data envoyée à Supabase (Statut: {record['status']})")
        except Exception as e:
            print(f"❌ Erreur Supabase : {e}")

    def generate_markdown_report(self) -> str:
        metrics = self.extract_metrics()
        report = [
            f"## 🛠️ EcoArch FinOps Analysis",
            f"**Total Mensuel Estimé :** `{metrics['total_monthly_cost']:.2f} {metrics['currency']}`\n"
        ]
        
        if not self.resources:
            report.append("ℹ️ Aucune ressource détectée dans ce plan (No changes).")
        else:
            report.append("### 🏆 Top 3 Ressources les plus chères")
            report.append("| Ressource | Coût Mensuel |")
            report.append("| :--- | :--- |")
            sorted_res = sorted(self.resources, key=lambda x: x['monthly_cost'], reverse=True)[:3]
            for res in sorted_res:
                report.append(f"| `{res['name']}` | {res['monthly_cost']:.2f} {metrics['currency']} |")
        
        return "\n".join(report)

if __name__ == "__main__":
    parser = EcoArchParser("infracost-report.json")
    print(parser.generate_markdown_report())
    parser.save_to_supabase()