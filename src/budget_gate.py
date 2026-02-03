"""Budget Gate - Vérifie que les coûts respectent le budget."""
import os
import sys

from parser import EcoArchParser

# Constantes
DEFAULT_BUDGET = 100.0
REPORT_PATH = "infracost-report.json"


def check_budget() -> None:
    """Vérifie les coûts par rapport au budget et bloque la CI si dépassé."""
    budget_limit = float(os.getenv("ECOARCH_BUDGET_LIMIT", DEFAULT_BUDGET))
    project_name = os.getenv("CI_PROJECT_NAME", "unknown")
    
    print("--- EcoArch Budget Gate ---")
    print(f"Project: {project_name}")
    
    try:
        parser = EcoArchParser(REPORT_PATH)
        metrics = parser.extract_metrics()
        total_cost = metrics["total_monthly_cost"]
        currency = metrics["currency"]
        
        print(f"Estimate: {total_cost:.2f} {currency}")
        print(f"Budget:   {budget_limit:.2f} {currency}")
        
        if total_cost > budget_limit:
            excess = total_cost - budget_limit
            print(f"❌ FAILED: Budget exceeded by {excess:.2f} {currency}")
            sys.exit(1)
        
        print("✅ PASSED: Within budget")
        sys.exit(0)
        
    except Exception as e:
        print(f"⚠️ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_budget()