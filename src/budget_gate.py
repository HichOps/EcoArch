import sys
import os
from parser import EcoArchParser

def check_budget():
    # On récupère le budget depuis la CI, défaut à 100$ si non défini
    budget_limit = float(os.getenv("ECOARCH_BUDGET_LIMIT", 100.0))
    report_path = "infracost-report.json"

    try:
        parser = EcoArchParser(report_path)
        metrics = parser.extract_metrics()
        total_cost = metrics["total_monthly_cost"]

        print(f"--- EcoArch Budget Gate ---")
        print(f"Target Project: {os.getenv('CI_PROJECT_NAME')}")
        print(f"Current Estimate: {total_cost:.2f} {metrics['currency']}")
        print(f"Budget Limit: {budget_limit:.2f} {metrics['currency']}")

        if total_cost > budget_limit:
            print(f"❌ ERROR: Budget exceeded! (+{total_cost - budget_limit:.2f})")
            sys.exit(1)  # Bloque la pipeline
        
        print("✅ SUCCESS: Within budget limits.")
        sys.exit(0)

    except Exception as e:
        print(f"⚠️ Error during budget check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_budget()