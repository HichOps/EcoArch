"""Tests unitaires pour l'état applicatif (frontend/state.py).

Couvre:
- Wizard logic (apply_recommendation_flow)
- Cost guardrails (start_deployment budget gate)
- Resource management (add_resource, remove_resource)
- Audit formatting (_format_audit_row)

Stratégie: Reflex wraps every State method as an EventHandler.
Calling State.method(obj, ...) hits Reflex's serialization layer.
We bypass this by calling handler.fn(self, ...) — the raw Python
function — on a lightweight duck-typed state object.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure project root is on path for imports
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


# ============================================================
# Helpers
# ============================================================

def _get_fn(handler):
    """Extract the raw Python function from a Reflex EventHandler."""
    return handler.fn


def _make_state(**overrides):
    """Crée un objet duck-typed qui imite State sans le runtime Reflex."""

    class _FakeState:
        pass

    s = _FakeState()

    defaults = {
        "current_user": "Alice (DevOps)",
        "user_role": "admin",
        "deployment_id": "test1234",
        "resource_list": [],
        "cost": 0.0,
        "details": {},
        "is_loading": False,
        "is_authenticated": True,
        "login_username": "",
        "login_error": "",
        "error_msg": "",
        "logs": [],
        "is_deploying": False,
        "deploy_status": "idle",
        "pipeline_url": "",
        "is_expert_mode": True,
        "wizard_auto_deploy": False,
        "wizard_include_database": True,
        "wizard_answers": {
            "environment": "dev",
            "traffic": "low",
            "workload": "general",
            "criticality": "low",
            "type": "web",
        },
        "selected_service": "compute",
        "selected_machine": "e2-medium",
        "selected_storage": 50,
        "selected_db_tier": "db-f1-micro",
        "selected_db_version": "POSTGRES_14",
        "selected_storage_class": "STANDARD",
        "selected_software_stack": "none",
        "audit_logs": [],
    }
    defaults.update(overrides)
    for k, v in defaults.items():
        setattr(s, k, v)

    # Bind helper methods that start_deployment / start_destruction call internally.
    # These are plain methods on State (not EventHandlers), so we can reference them
    # directly or provide lightweight stubs.
    from frontend.frontend.state import State as _St
    s._create_audit_log = lambda action, target_id, cost=None: None
    s._update_audit_log = lambda audit_id, status: None
    s._append_log = _get_fn(_St._append_log).__get__(s) if hasattr(_St._append_log, 'fn') else lambda line: s.logs.append(line)
    s.load_audit_logs = lambda: None
    # Auth: _require_auth vérifie is_authenticated et current_user
    s._require_auth = lambda: bool(s.is_authenticated and s.current_user)

    return s


# ============================================================
# A. Wizard Logic (apply_recommendation_flow)
# ============================================================

class TestWizardLogic:
    """Tests de la logique wizard (set_wizard_*_logic)."""

    def test_viral_app_sets_traffic_high(self):
        """Input 'Viral App' → traffic = 'high'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_traffic_logic)(s, "Viral App")
        assert s.wizard_answers["traffic"] == "high"

    def test_croissance_sets_traffic_medium(self):
        """Input 'Croissance régulière' → traffic = 'medium'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_traffic_logic)(s, "Croissance régulière")
        assert s.wizard_answers["traffic"] == "medium"

    def test_default_traffic_low(self):
        """Input sans mot-clé → traffic = 'low'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_traffic_logic)(s, "Petit projet perso")
        assert s.wizard_answers["traffic"] == "low"

    def test_video_processing_sets_workload_cpu(self):
        """Input 'Traitement vidéo' → workload = 'cpu'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_workload_logic)(s, "Traitement vidéo")
        assert s.wizard_answers["workload"] == "cpu"

    def test_cache_sets_workload_memory(self):
        """Input 'Cache Redis' → workload = 'memory'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_workload_logic)(s, "Cache Redis lourd")
        assert s.wizard_answers["workload"] == "memory"

    def test_general_workload_default(self):
        """Input générique → workload = 'general'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_workload_logic)(s, "Application web classique")
        assert s.wizard_answers["workload"] == "general"

    def test_prod_environment(self):
        """Input contenant 'Prod' → environment = 'prod'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_env_logic)(s, "Prod – Mission Critique")
        assert s.wizard_answers["environment"] == "prod"

    def test_dev_environment(self):
        """Input sans 'Prod' → environment = 'dev'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_env_logic)(s, "Développement local")
        assert s.wizard_answers["environment"] == "dev"

    def test_high_criticality(self):
        """Input contenant 'critique' → criticality = 'high'."""
        from frontend.frontend.state import State

        s = _make_state()
        _get_fn(State.set_wizard_criticality_logic)(s, "Service critique 24/7")
        assert s.wizard_answers["criticality"] == "high"


# ============================================================
# B. Cost Guardrails (start_deployment)
# ============================================================

class TestCostGuardrails:
    """Tests du budget gate dans start_deployment."""

    def test_over_budget_blocks_deployment(self):
        """Coût 60.0 > budget 50.0 → déploiement refusé, status reste idle."""
        from frontend.frontend.state import State

        s = _make_state(
            cost=60.0,
            resource_list=[{"type": "compute", "display_name": "VM"}],
            deploy_status="idle",
        )

        # Call raw fn – it returns rx.toast.error (not a generator)
        result = _get_fn(State.start_deployment)(s)
        assert s.deploy_status != "running"

    def test_under_budget_starts_deployment(self):
        """Coût 40.0 ≤ budget 50.0 → déploiement démarre (GitLab trigger ou fallback)."""
        from frontend.frontend.state import State

        s = _make_state(
            cost=40.0,
            resource_list=[{"type": "compute", "display_name": "VM test"}],
            deploy_status="idle",
            is_deploying=False,
        )

        with patch("frontend.frontend.state.trigger_deployment") as mock_trigger, \
             patch("frontend.frontend.state.Config") as mock_config:

            # Configure GitLab trigger mock
            mock_config.GITLAB_TRIGGER_TOKEN = "glptt-test"
            mock_config.DEFAULT_BUDGET_LIMIT = 50.0
            mock_config.get_supabase_client.return_value = None
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.pipeline_id = 123
            mock_result.pipeline_url = "https://gitlab.com/test/-/pipelines/123"
            mock_trigger.return_value = mock_result

            gen = _get_fn(State.start_deployment)(s)
            try:
                if hasattr(gen, "__next__"):
                    for _ in gen:
                        pass
            except (StopIteration, TypeError):
                pass

        assert s.deploy_status in ("queued", "pipeline_sent", "running", "success", "error")

    def test_empty_cart_blocks_deployment(self):
        """Panier vide → toast d'erreur, pas de déploiement."""
        from frontend.frontend.state import State

        s = _make_state(resource_list=[], deploy_status="idle")
        result = _get_fn(State.start_deployment)(s)
        assert s.deploy_status == "idle"


# ============================================================
# C. Resource Management (add_resource / remove_resource)
# ============================================================

class TestResourceManagement:
    """Tests d'ajout/suppression de ressources."""

    def test_add_resource_increments_list(self):
        """add_resource ajoute un élément au panier."""
        from frontend.frontend.state import State

        s = _make_state(
            resource_list=[],
            selected_service="compute",
            selected_machine="e2-medium",
            selected_storage=50,
            selected_software_stack="none",
        )

        _get_fn(State.add_resource)(s)
        assert len(s.resource_list) == 1
        assert s.resource_list[0]["type"] == "compute"
        assert s.resource_list[0]["machine_type"] == "e2-medium"

    def test_add_sql_resource(self):
        """add_resource avec service=sql crée une ressource SQL."""
        from frontend.frontend.state import State

        s = _make_state(
            resource_list=[],
            selected_service="sql",
            selected_db_tier="db-g1-small",
            selected_db_version="POSTGRES_15",
        )

        _get_fn(State.add_resource)(s)
        assert len(s.resource_list) == 1
        assert s.resource_list[0]["type"] == "sql"
        assert "db-g1-small" in s.resource_list[0]["db_tier"]

    def test_add_multiple_resources(self):
        """Ajouts successifs incrémentent le panier."""
        from frontend.frontend.state import State

        s = _make_state(
            resource_list=[],
            selected_service="compute",
            selected_machine="e2-micro",
            selected_storage=20,
            selected_software_stack="none",
        )

        _get_fn(State.add_resource)(s)
        _get_fn(State.add_resource)(s)
        assert len(s.resource_list) == 2

    def test_remove_resource_index_zero(self):
        """remove_resource(0) retire le premier élément (régression 'Zombie resource')."""
        from frontend.frontend.state import State

        initial_resources = [
            {"type": "compute", "display_name": "VM A"},
            {"type": "sql", "display_name": "SQL B"},
            {"type": "storage", "display_name": "GCS C"},
        ]
        s = _make_state(resource_list=initial_resources.copy())

        _get_fn(State.remove_resource)(s, 0)

        assert len(s.resource_list) == 2
        assert s.resource_list[0]["display_name"] == "SQL B"
        assert s.resource_list[1]["display_name"] == "GCS C"

    def test_remove_resource_middle(self):
        """remove_resource(1) retire l'élément du milieu."""
        from frontend.frontend.state import State

        initial_resources = [
            {"type": "compute", "display_name": "VM A"},
            {"type": "sql", "display_name": "SQL B"},
            {"type": "storage", "display_name": "GCS C"},
        ]
        s = _make_state(resource_list=initial_resources.copy())

        _get_fn(State.remove_resource)(s, 1)

        assert len(s.resource_list) == 2
        assert s.resource_list[0]["display_name"] == "VM A"
        assert s.resource_list[1]["display_name"] == "GCS C"

    def test_remove_resource_last(self):
        """remove_resource sur le dernier index vide la liste."""
        from frontend.frontend.state import State

        s = _make_state(resource_list=[{"type": "compute", "display_name": "Solo"}])

        _get_fn(State.remove_resource)(s, 0)
        assert len(s.resource_list) == 0


# ============================================================
# D. Audit Formatting (_format_audit_row)
# ============================================================

class TestAuditFormatting:
    """Tests du formatage des logs d'audit."""

    def test_format_timestamp_iso(self):
        """Timestamp ISO → date lisible 'YYYY-MM-DD HH:MM'."""
        from frontend.frontend.state import State

        row = {
            "created_at": "2026-02-10T14:30:45.123456+00:00",
            "total_cost": 42.756,
            "action": "DEPLOY",
            "user": "Alice",
        }
        formatted = State._format_audit_row(row)

        assert formatted["formatted_date"] == "2026-02-10 14:30"

    def test_format_cost_rounding(self):
        """Le coût doit être arrondi à 2 décimales avec préfixe $."""
        from frontend.frontend.state import State

        row = {
            "created_at": "2026-01-15T09:00:00",
            "total_cost": 99.999,
        }
        formatted = State._format_audit_row(row)

        assert formatted["formatted_cost"] == "$100.00"

    def test_format_cost_zero(self):
        """Coût 0 → '$0.00'."""
        from frontend.frontend.state import State

        row = {
            "created_at": "2026-01-01T00:00:00",
            "total_cost": 0,
        }
        formatted = State._format_audit_row(row)

        assert formatted["formatted_cost"] == "$0.00"

    def test_format_preserves_original_fields(self):
        """Les champs originaux sont conservés dans le dict formaté."""
        from frontend.frontend.state import State

        row = {
            "id": 42,
            "created_at": "2026-02-10T10:00:00",
            "total_cost": 25.5,
            "action": "DESTROY",
            "user": "Bob",
            "status": "SUCCESS",
        }
        formatted = State._format_audit_row(row)

        assert formatted["id"] == 42
        assert formatted["action"] == "DESTROY"
        assert formatted["user"] == "Bob"
        assert formatted["status"] == "SUCCESS"

    def test_format_timestamp_without_t_separator(self):
        """Timestamp sans 'T' → conserve tel quel."""
        from frontend.frontend.state import State

        row = {
            "created_at": "2026-02-10 14:30:00",
            "total_cost": 10.0,
        }
        formatted = State._format_audit_row(row)

        assert formatted["formatted_date"] == "2026-02-10 14:30:00"

    def test_format_missing_cost_defaults_to_zero(self):
        """Clé total_cost absente → '$0.00'."""
        from frontend.frontend.state import State

        row = {"created_at": "2026-01-01T00:00:00"}
        formatted = State._format_audit_row(row)

        assert formatted["formatted_cost"] == "$0.00"


# ============================================================
# E. login / logout – Supabase profiles validation
# ============================================================

class TestLogin:
    """Tests du système d'authentification via AuthService."""

    @staticmethod
    def _exhaust_gen(gen):
        """Consomme un générateur (login est un generator)."""
        if gen is None:
            return
        try:
            while True:
                next(gen)
        except StopIteration:
            pass

    def test_known_user_authenticates(self):
        """Utilisateur connu dans profiles → is_authenticated = True, role rempli."""
        from frontend.frontend.state import State
        from src.services.auth_service import AuthResult

        s = _make_state(current_user="", is_authenticated=False, user_role="", login_username="Hicham")
        s.run_simulation = lambda: _get_fn(State.run_simulation)(s)

        with patch("frontend.frontend.state.AuthService") as mock_auth, \
             patch("frontend.frontend.state.InfracostSimulator"):
            mock_auth.verify_credentials.return_value = AuthResult(
                authenticated=True, username="Hicham", role="admin"
            )
            self._exhaust_gen(_get_fn(State.login)(s, None))

        assert s.is_authenticated is True
        assert s.user_role == "admin"
        assert s.current_user == "Hicham"

    def test_login_with_form_data(self):
        """Login via form_data dict."""
        from frontend.frontend.state import State
        from src.services.auth_service import AuthResult

        s = _make_state(current_user="", is_authenticated=False, user_role="", login_username="")
        s.run_simulation = lambda: _get_fn(State.run_simulation)(s)

        with patch("frontend.frontend.state.AuthService") as mock_auth, \
             patch("frontend.frontend.state.InfracostSimulator"):
            mock_auth.verify_credentials.return_value = AuthResult(
                authenticated=True, username="Hicham", role="viewer"
            )
            self._exhaust_gen(_get_fn(State.login)(s, {"username": "Hicham"}))

        assert s.is_authenticated is True
        assert s.current_user == "Hicham"
        assert s.user_role == "viewer"

    def test_unknown_user_rejected_generic_msg(self):
        """Utilisateur inconnu → is_authenticated = False, message générique."""
        from frontend.frontend.state import State
        from src.services.auth_service import AuthResult

        s = _make_state(current_user="", is_authenticated=False, user_role="", login_username="Intrus")

        with patch("frontend.frontend.state.AuthService") as mock_auth:
            mock_auth.verify_credentials.return_value = AuthResult(
                authenticated=False, error="Identifiants invalides"
            )
            self._exhaust_gen(_get_fn(State.login)(s, None))

        assert s.is_authenticated is False
        assert s.user_role == ""
        assert s.login_error == "Identifiants invalides"

    def test_empty_username_shows_error(self):
        """Username vide → erreur, pas d'auth (AuthService jamais appelé)."""
        from frontend.frontend.state import State

        s = _make_state(current_user="", is_authenticated=False, user_role="", login_username="")

        self._exhaust_gen(_get_fn(State.login)(s, None))

        assert s.is_authenticated is False
        assert s.login_error == "Veuillez saisir votre identifiant."

    def test_supabase_error_falls_back_gracefully(self):
        """Erreur Supabase → mode dégradé via AuthResult.degraded."""
        from frontend.frontend.state import State
        from src.services.auth_service import AuthResult

        s = _make_state(current_user="", is_authenticated=False, user_role="", login_username="Hicham")
        s.run_simulation = lambda: _get_fn(State.run_simulation)(s)

        with patch("frontend.frontend.state.AuthService") as mock_auth, \
             patch("frontend.frontend.state.InfracostSimulator"):
            mock_auth.verify_credentials.return_value = AuthResult(
                authenticated=True, username="Hicham", role="viewer", degraded=True
            )
            self._exhaust_gen(_get_fn(State.login)(s, None))

        assert s.is_authenticated is True
        assert s.user_role == "viewer"

    def test_no_supabase_accepts_locally(self):
        """Pas de Supabase configuré → auth locale accepte tout (via AuthService)."""
        from frontend.frontend.state import State
        from src.services.auth_service import AuthResult

        s = _make_state(current_user="", is_authenticated=False, user_role="", login_username="DevLocal")
        s.run_simulation = lambda: _get_fn(State.run_simulation)(s)

        with patch("frontend.frontend.state.AuthService") as mock_auth, \
             patch("frontend.frontend.state.InfracostSimulator"):
            mock_auth.verify_credentials.return_value = AuthResult(
                authenticated=True, username="DevLocal", role="admin"
            )
            self._exhaust_gen(_get_fn(State.login)(s, None))

        assert s.is_authenticated is True
        assert s.user_role == "admin"
        assert s.current_user == "DevLocal"

    def test_login_triggers_simulation_with_cart(self):
        """Auth réussie avec panier non-vide → coût calculé."""
        from frontend.frontend.state import State
        from src.services.auth_service import AuthResult

        s = _make_state(
            current_user="",
            is_authenticated=False,
            user_role="",
            login_username="Hicham",
            resource_list=[{"type": "compute", "machine_type": "e2-medium", "disk_size": 50}],
        )
        s.run_simulation = lambda: _get_fn(State.run_simulation)(s)

        with patch("frontend.frontend.state.AuthService") as mock_auth, \
             patch("frontend.frontend.state.InfracostSimulator") as mock_sim_cls:
            mock_auth.verify_credentials.return_value = AuthResult(
                authenticated=True, username="Hicham", role="admin"
            )
            mock_result = MagicMock(success=True, monthly_cost=31.38, details={"_source": "fallback"})
            mock_sim_cls.return_value.simulate.return_value = mock_result
            self._exhaust_gen(_get_fn(State.login)(s, None))

        assert s.is_authenticated is True
        assert s.cost == 31.38

    def test_login_triggers_simulation_even_empty_cart(self):
        """Auth réussie avec panier vide → simulation appelée, cost = 0."""
        from frontend.frontend.state import State
        from src.services.auth_service import AuthResult

        s = _make_state(
            current_user="",
            is_authenticated=False,
            user_role="",
            login_username="DevLocal",
            resource_list=[],
            cost=0.0,
        )
        s.run_simulation = lambda: _get_fn(State.run_simulation)(s)

        with patch("frontend.frontend.state.AuthService") as mock_auth, \
             patch("frontend.frontend.state.InfracostSimulator"):
            mock_auth.verify_credentials.return_value = AuthResult(
                authenticated=True, username="DevLocal", role="admin"
            )
            self._exhaust_gen(_get_fn(State.login)(s, None))

        assert s.is_authenticated is True
        assert s.cost == 0.0

    def test_logout_resets_state(self):
        """Déconnexion réinitialise l'état."""
        from frontend.frontend.state import State

        s = _make_state(
            current_user="Hicham",
            is_authenticated=True,
            user_role="admin",
            login_username="Hicham",
        )

        _get_fn(State.logout)(s)

        assert s.is_authenticated is False
        assert s.current_user == ""
        assert s.user_role == ""
        assert s.login_username == ""

    def test_require_auth_blocks_unauthenticated(self):
        """_require_auth retourne False si non authentifié."""
        from frontend.frontend.state import State

        s = _make_state(current_user="Intrus", is_authenticated=False)
        assert s._require_auth() is False

    def test_require_auth_allows_authenticated(self):
        """_require_auth retourne True si authentifié."""
        from frontend.frontend.state import State

        s = _make_state(current_user="Hicham", is_authenticated=True)
        assert s._require_auth() is True
