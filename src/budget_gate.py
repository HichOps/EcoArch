"""Budget Gate - Vérifie que les coûts respectent le budget.

Améliorations :
- ARCH-4 : logging au lieu de print().
- ARCH-5 : import corrigé (src.parser au lieu de parser).
- ARCH-6 : Exception au lieu de sys.exit() pour testabilité.
"""
import logging
import os
import sys

from src.parser import EcoArchParser

logger = logging.getLogger(__name__)

# Constantes
DEFAULT_BUDGET = 100.0
REPORT_PATH = "infracost-report.json"


class BudgetExceededError(Exception):
    """Levée quand le coût dépasse le budget autorisé."""

    def __init__(self, cost: float, budget: float, currency: str = "USD"):
        self.cost = cost
        self.budget = budget
        self.currency = currency
        super().__init__(
            f"Budget exceeded: {cost:.2f} {currency} > {budget:.2f} {currency}"
        )


def check_budget(report_path: str = REPORT_PATH) -> dict:
    """Vérifie les coûts par rapport au budget.

    Returns:
        dict avec les clés: passed (bool), cost, budget, currency

    Raises:
        BudgetExceededError: si le coût dépasse le budget.
    """
    budget_limit = float(os.getenv("ECOARCH_BUDGET_LIMIT", DEFAULT_BUDGET))
    project_name = os.getenv("CI_PROJECT_NAME", "unknown")

    logger.info("--- EcoArch Budget Gate ---")
    logger.info("Project: %s", project_name)

    parser = EcoArchParser(report_path)
    metrics = parser.extract_metrics()
    total_cost = metrics["total_monthly_cost"]
    currency = metrics["currency"]

    logger.info("Estimate: %.2f %s", total_cost, currency)
    logger.info("Budget:   %.2f %s", budget_limit, currency)

    result = {
        "passed": total_cost <= budget_limit,
        "cost": total_cost,
        "budget": budget_limit,
        "currency": currency,
    }

    if not result["passed"]:
        excess = total_cost - budget_limit
        logger.error("FAILED: Budget exceeded by %.2f %s", excess, currency)
        raise BudgetExceededError(total_cost, budget_limit, currency)

    logger.info("PASSED: Within budget")
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        check_budget()
        sys.exit(0)
    except BudgetExceededError:
        sys.exit(1)
    except Exception as e:
        logger.error("Error: %s", e)
        sys.exit(1)
