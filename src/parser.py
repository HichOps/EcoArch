"""Parser pour les rapports Infracost JSON."""
import json
import os
from pathlib import Path
from typing import Any


class EcoArchParser:
    """Parse et analyse les rapports de coûts Infracost."""
    
    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self.data = self._load_data()
        self.resources = self._flatten_resources()
    
    def _load_data(self) -> dict:
        """Charge le fichier JSON ou retourne un dict vide."""
        if not self.json_path.exists():
            print(f"❌ Fichier introuvable: {self.json_path}")
            return {}
        
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            print(f"❌ JSON malformé: {e}")
            return {}
    
    @staticmethod
    def _safe_float(value: Any) -> float:
        """Convertit une valeur en float de manière sécurisée."""
        if value is None:
            return 0.0
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0
    
    def _flatten_resources(self) -> list[dict]:
        """Extrait une liste plate des ressources depuis tous les projets."""
        resources = []
        
        for project in self.data.get("projects") or []:
            breakdown = project.get("breakdown") or {}
            for res in breakdown.get("resources") or []:
                resources.append({
                    "name": res.get("name", "Unnamed"),
                    "type": res.get("resourceType", "Unknown"),
                    "monthly_cost": self._safe_float(res.get("monthlyCost")),
                    "delta": self._safe_float(res.get("diffMonthlyCost")),
                })
        
        return resources
    
    def extract_metrics(self) -> dict[str, Any]:
        """Extrait les métriques principales du rapport."""
        return {
            "total_monthly_cost": self._safe_float(self.data.get("totalMonthlyCost")),
            "diff_monthly_cost": self._safe_float(self.data.get("diffTotalMonthlyCost")),
            "currency": self.data.get("currency", "USD"),
        }
    
    def save_to_supabase(self) -> None:
        """Enregistre les métriques dans Supabase (optionnel)."""
        from supabase import create_client
        
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_KEY")
        
        if not url or not key:
            print("⏭️ Supabase non configuré, sauvegarde ignorée.")
            return
        
        try:
            supabase = create_client(url, key)
            metrics = self.extract_metrics()
            budget = float(os.getenv("ECOARCH_BUDGET_LIMIT", 100.0))
            cost = metrics["total_monthly_cost"]
            
            record = {
                "project_id": os.getenv("CI_PROJECT_NAME", "ecoarch-local"),
                "branch_name": os.getenv("CI_COMMIT_REF_NAME", "local"),
                "commit_sha": os.getenv("CI_COMMIT_SHORT_SHA", "HEAD"),
                "author": os.getenv("CI_COMMIT_AUTHOR", "Unknown"),
                "total_monthly_cost": cost,
                "diff_monthly_cost": metrics["diff_monthly_cost"],
                "currency": metrics["currency"],
                "budget_limit": budget,
                "status": "PASSED" if cost <= budget else "FAILED",
            }
            
            supabase.table("cost_history").insert(record).execute()
            print(f"✅ Supabase: {record['status']}")
            
        except Exception as e:
            print(f"❌ Erreur Supabase: {e}")
    
    def generate_markdown_report(self) -> str:
        """Génère un rapport Markdown pour GitLab/GitHub."""
        metrics = self.extract_metrics()
        currency = metrics["currency"]
        total = metrics["total_monthly_cost"]
        diff = metrics["diff_monthly_cost"]
        
        lines = [
            "## 🛠️ EcoArch FinOps Analysis",
            f"**Total Mensuel Estimé:** `{total:.2f} {currency}`",
        ]
        
        # Indicateur de variation
        if diff > 0:
            lines.append(f"**Variation:** 🔺 `+{diff:.2f} {currency}` (Hausse)")
        elif diff < 0:
            lines.append(f"**Variation:** 🟢 `{diff:.2f} {currency}` (Économie)")
        else:
            lines.append(f"**Variation:** ➖ `0.00 {currency}` (Stable)")
        
        return "\n".join(lines)