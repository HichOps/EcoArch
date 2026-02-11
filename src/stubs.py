"""Stubs légers pour le développement frontend sans backend.

Utilisés automatiquement quand les modules src.* ne sont pas disponibles
(ex: reflex dev sans les dépendances backend installées).

Ce module centralise les fallbacks pour respecter le principe DRY.
"""
from typing import Any


class GCPConfigStub:
    """Stub pour src.config.GCPConfig."""
    INSTANCE_TYPES: list[str] = []
    DB_TIERS: list[str] = []
    DB_VERSIONS: list[str] = []
    STORAGE_CLASSES: list[str] = []
    SOFTWARE_STACKS: dict[str, dict[str, str]] = {}

    @staticmethod
    def get_stack_names() -> list[str]:
        return []

    @staticmethod
    def get_startup_script(stack: str) -> str:
        return ""


class ConfigStub:
    """Stub pour src.config.Config."""
    DEFAULT_BUDGET_LIMIT: float = 50.0
    SUPABASE_URL: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    GCP_PROJECT_ID: str = ""
    DEFAULT_REGION: str = "us-central1"
    TERRAFORM_STATE_BUCKET: str = ""
    INFRACOST_TIMEOUT: int = 300
    REDIS_URL: str = ""
    AUTH_SECRET_KEY: str = ""
    AUTH_ENABLED: bool = False
    GITLAB_TRIGGER_TOKEN: str = ""

    @classmethod
    def get_supabase_client(cls):
        return None


class AuthResultStub:
    """Stub pour src.services.auth_service.AuthResult."""
    def __init__(
        self,
        authenticated: bool = False,
        username: str = "",
        role: str = "",
        error: str = "",
        degraded: bool = False,
    ):
        self.authenticated = authenticated
        self.username = username
        self.role = role
        self.error = error
        self.degraded = degraded


class AuthServiceStub:
    """Stub pour src.services.auth_service.AuthService."""
    @staticmethod
    def verify_credentials(username: str) -> AuthResultStub:
        return AuthResultStub(authenticated=True, username=username, role="admin")

    @staticmethod
    def generate_token(username: str) -> str:
        return ""

    @staticmethod
    def verify_token(username: str, token: str) -> bool:
        return True


class RecommendationEngineStub:
    """Stub pour src.recommendation.RecommendationEngine."""
    @staticmethod
    def generate(answers: dict[str, str]) -> list[dict[str, Any]]:
        return []


class SimulationResultStub:
    """Stub pour src.simulation.SimulationResult."""
    def __init__(
        self,
        success: bool = False,
        monthly_cost: float = 0.0,
        details: dict | None = None,
        error_message: str | None = None,
    ):
        self.success = success
        self.monthly_cost = monthly_cost
        self.details = details or {}
        self.error_message = error_message


class InfracostSimulatorStub:
    """Stub pour src.simulation.InfracostSimulator."""

    # Pricing approximatif GCP ($/mois) – identique à simulation._FALLBACK_*
    _COMPUTE: dict[str, float] = {
        "e2-micro": 7.12, "e2-small": 14.23, "e2-medium": 29.38,
        "e2-standard-2": 58.76, "e2-standard-4": 117.51,
        "n1-standard-1": 24.27, "n2-standard-2": 65.64, "c2-standard-4": 141.24,
    }
    _DISK_PER_GB = 0.04
    _SQL: dict[str, float] = {
        "db-f1-micro": 7.67, "db-g1-small": 25.55,
        "db-custom-1-3840": 50.34, "db-custom-2-7680": 100.67,
        "db-custom-4-15360": 201.34,
    }
    _STORAGE: dict[str, float] = {
        "STANDARD": 2.60, "NEARLINE": 1.30, "COLDLINE": 0.70, "ARCHIVE": 0.15,
    }
    _LB = 18.26

    def __init__(self, project_id: str | None = None, timeout: int | None = None):
        pass

    def simulate(self, resources: list) -> SimulationResultStub:
        """Estimation hors-ligne basée sur le pricing public GCP."""
        if not resources:
            return SimulationResultStub(success=True)

        total = 0.0
        breakdown: list[dict[str, Any]] = []

        for res in resources:
            rt = res.get("type", "compute")
            cost = 0.0
            if rt == "compute":
                cost = self._COMPUTE.get(res.get("machine_type", "e2-medium"), 29.38)
                cost += int(res.get("disk_size", 50)) * self._DISK_PER_GB
            elif rt == "sql":
                cost = self._SQL.get(res.get("db_tier", "db-f1-micro"), 7.67)
            elif rt == "storage":
                cost = self._STORAGE.get(res.get("storage_class", "STANDARD"), 2.60)
            elif rt == "load_balancer":
                cost = self._LB
            total += cost
            breakdown.append({"name": res.get("display_name", rt), "monthlyCost": str(round(cost, 2))})

        return SimulationResultStub(
            success=True,
            monthly_cost=round(total, 2),
            details={
                "totalMonthlyCost": str(round(total, 2)),
                "projects": [{"breakdown": {"resources": breakdown}}],
                "_source": "stub-fallback",
            },
        )

    def deploy(self, resources: list, deployment_id: str):
        yield "Backend non disponible"

    def destroy(self, resources: list, deployment_id: str):
        yield "Backend non disponible"
