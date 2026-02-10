"""Tests du moteur de recommandation d'infrastructure.

Couvre toutes les combinaisons env × traffic × workload × criticality × type.
"""
import pytest

from src.recommendation import (
    APP_TYPE_STACKS,
    ENV_CONFIG,
    WORKLOAD_MACHINES,
    RecommendationEngine,
)


# ── Fixtures ──────────────────────────────────────────────────────

def _base_answers(**overrides) -> dict[str, str]:
    """Crée un jeu de réponses avec des valeurs par défaut."""
    defaults = {
        "environment": "dev",
        "traffic": "low",
        "workload": "general",
        "criticality": "low",
        "type": "web",
    }
    defaults.update(overrides)
    return defaults


# ── Tests de base ─────────────────────────────────────────────────

class TestGenerateBasic:
    """Vérifications structurelles de generate()."""

    def test_returns_list(self):
        result = RecommendationEngine.generate(_base_answers())
        assert isinstance(result, list)

    def test_non_empty(self):
        result = RecommendationEngine.generate(_base_answers())
        assert len(result) > 0

    def test_each_resource_has_type(self):
        result = RecommendationEngine.generate(_base_answers())
        for r in result:
            assert "type" in r

    def test_each_resource_has_display_name(self):
        result = RecommendationEngine.generate(_base_answers())
        for r in result:
            assert "display_name" in r


# ── Tests par environnement ───────────────────────────────────────

class TestEnvironments:
    """Vérifie les configurations dev vs prod."""

    def test_dev_uses_micro_machine(self):
        """En dev, la VM doit être e2-micro."""
        resources = RecommendationEngine.generate(_base_answers(environment="dev"))
        computes = [r for r in resources if r["type"] == "compute"]
        assert all(c["machine_type"] == "e2-micro" for c in computes)

    def test_dev_uses_small_disk(self):
        """En dev, le disque doit être 20 GB."""
        resources = RecommendationEngine.generate(_base_answers(environment="dev"))
        computes = [r for r in resources if r["type"] == "compute"]
        assert all(c["disk_size"] == 20 for c in computes)

    def test_dev_uses_micro_db(self):
        """En dev, la DB doit être db-f1-micro."""
        resources = RecommendationEngine.generate(_base_answers(environment="dev"))
        dbs = [r for r in resources if r["type"] == "sql"]
        assert all(d["db_tier"] == "db-f1-micro" for d in dbs)

    def test_prod_uses_workload_machine(self):
        """En prod, la VM est définie par le workload."""
        for workload, expected_machine in WORKLOAD_MACHINES.items():
            resources = RecommendationEngine.generate(
                _base_answers(environment="prod", workload=workload)
            )
            computes = [r for r in resources if r["type"] == "compute"]
            assert computes[0]["machine_type"] == expected_machine, (
                f"workload={workload}: attendu {expected_machine}, "
                f"obtenu {computes[0]['machine_type']}"
            )

    def test_prod_uses_larger_disk(self):
        """En prod, le disque doit être 50 GB."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert all(c["disk_size"] == 50 for c in computes)


# ── Tests Haute Disponibilité ─────────────────────────────────────

class TestHighAvailability:
    """Vérifie la logique HA : prod + (traffic=high OU criticality=high)."""

    def test_dev_never_ha(self):
        """En dev, pas de HA même avec trafic/criticité élevés."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="dev", traffic="high", criticality="high")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert len(computes) == 1  # Pas de réplique

    def test_prod_low_traffic_not_ha(self):
        """Prod + trafic faible + criticité faible = pas HA."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", traffic="low", criticality="low")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert len(computes) == 1

    def test_prod_high_traffic_triggers_ha(self):
        """Prod + trafic élevé = HA (2 répliques)."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", traffic="high")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert len(computes) == 2

    def test_prod_high_criticality_triggers_ha(self):
        """Prod + criticité élevée = HA (2 répliques)."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", criticality="high")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert len(computes) == 2

    def test_ha_includes_load_balancer(self):
        """En mode HA, un Load Balancer doit être ajouté."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", traffic="high")
        )
        lbs = [r for r in resources if r["type"] == "load_balancer"]
        assert len(lbs) == 1

    def test_non_ha_no_load_balancer(self):
        """Sans HA, pas de Load Balancer."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="dev")
        )
        lbs = [r for r in resources if r["type"] == "load_balancer"]
        assert len(lbs) == 0

    def test_ha_db_tier(self):
        """En HA, la DB doit être db-custom-2-3840."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", traffic="high")
        )
        dbs = [r for r in resources if r["type"] == "sql"]
        assert dbs[0]["db_tier"] == "db-custom-2-3840"

    def test_ha_storage_class(self):
        """En HA, le storage doit être MULTI_REGIONAL."""
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", traffic="high")
        )
        storages = [r for r in resources if r["type"] == "storage"]
        assert storages[0]["storage_class"] == "MULTI_REGIONAL"


# ── Tests par type d'application ──────────────────────────────────

class TestAppTypes:
    """Vérifie que chaque type d'app recommande la bonne stack."""

    @pytest.mark.parametrize("app_type,expected_stack", list(APP_TYPE_STACKS.items()))
    def test_stack_mapping(self, app_type, expected_stack):
        """Chaque type d'app doit mapper vers la stack attendue."""
        resources = RecommendationEngine.generate(
            _base_answers(type=app_type)
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert computes[0]["software_stack"] == expected_stack

    def test_batch_no_database(self):
        """Les jobs batch ne doivent pas inclure de base de données."""
        resources = RecommendationEngine.generate(
            _base_answers(type="batch")
        )
        dbs = [r for r in resources if r["type"] == "sql"]
        assert len(dbs) == 0

    def test_web_includes_database(self):
        """Les applications web doivent inclure une base de données."""
        resources = RecommendationEngine.generate(
            _base_answers(type="web")
        )
        dbs = [r for r in resources if r["type"] == "sql"]
        assert len(dbs) == 1


# ── Tests par workload ────────────────────────────────────────────

class TestWorkloads:
    """Vérifie le mapping workload → type de machine."""

    def test_cpu_workload(self):
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", workload="cpu")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert computes[0]["machine_type"] == "e2-highcpu-2"

    def test_memory_workload(self):
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", workload="memory")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert computes[0]["machine_type"] == "e2-highmem-2"

    def test_general_workload(self):
        resources = RecommendationEngine.generate(
            _base_answers(environment="prod", workload="general")
        )
        computes = [r for r in resources if r["type"] == "compute"]
        assert computes[0]["machine_type"] == "e2-medium"


# ── Tests combinatoires exhaustifs ────────────────────────────────

class TestCombinations:
    """Vérifie la stabilité sur toutes les combinaisons raisonnables."""

    ENVS = ["dev", "prod"]
    TRAFFICS = ["low", "medium", "high"]
    WORKLOADS = ["general", "cpu", "memory"]
    CRITICALITIES = ["low", "high"]
    APP_TYPES = ["web", "api", "backend", "batch", "microservices"]

    @pytest.mark.parametrize("env", ENVS)
    @pytest.mark.parametrize("traffic", TRAFFICS)
    @pytest.mark.parametrize("workload", WORKLOADS)
    @pytest.mark.parametrize("criticality", CRITICALITIES)
    def test_always_has_compute_and_storage(self, env, traffic, workload, criticality):
        """Chaque combinaison doit avoir au moins 1 VM et 1 bucket."""
        resources = RecommendationEngine.generate(
            _base_answers(
                environment=env,
                traffic=traffic,
                workload=workload,
                criticality=criticality,
            )
        )
        types = [r["type"] for r in resources]
        assert "compute" in types
        assert "storage" in types

    @pytest.mark.parametrize("app_type", APP_TYPES)
    def test_app_type_produces_valid_resources(self, app_type):
        """Chaque type d'app produit des ressources valides."""
        resources = RecommendationEngine.generate(
            _base_answers(type=app_type)
        )
        for r in resources:
            assert "type" in r
            assert "display_name" in r
            assert r["type"] in {"compute", "sql", "storage", "load_balancer"}


# ── Tests de non-régression ───────────────────────────────────────

class TestStability:
    """Vérifie que generate() est déterministe."""

    def test_same_input_same_output(self):
        """Deux appels identiques doivent donner le même résultat."""
        answers = _base_answers(environment="prod", traffic="high", criticality="high")
        r1 = RecommendationEngine.generate(answers)
        r2 = RecommendationEngine.generate(answers)
        assert r1 == r2

    def test_storage_always_present(self):
        """Le storage est toujours présent, quel que soit l'input."""
        for env in ["dev", "prod"]:
            for app_type in ["web", "batch"]:
                resources = RecommendationEngine.generate(
                    _base_answers(environment=env, type=app_type)
                )
                storages = [r for r in resources if r["type"] == "storage"]
                assert len(storages) >= 1, f"Pas de storage pour {env}/{app_type}"

    def test_all_db_versions_are_postgres_15(self):
        """Toutes les DB recommandées doivent être en PostgreSQL 15."""
        for env in ["dev", "prod"]:
            resources = RecommendationEngine.generate(
                _base_answers(environment=env, type="web")
            )
            dbs = [r for r in resources if r["type"] == "sql"]
            for db in dbs:
                assert db["db_version"] == "POSTGRES_15"
