"""Tests des tâches Celery et utilitaires tasks.py.

Couvre :
- _sanitize_log_line : filtrage des données sensibles
- deploy_task / destroy_task : exécution avec mocks
"""
import pytest
from unittest.mock import MagicMock, patch

from src.tasks import _sanitize_log_line, _SENSITIVE_PATTERNS


# ══════════════════════════════════════════════════════════════════
#  Tests : _sanitize_log_line
# ══════════════════════════════════════════════════════════════════

class TestSanitizeLogLine:
    """Vérifie le filtrage des données sensibles dans les logs."""

    # ── Patterns à filtrer ────────────────────────────────────────

    def test_password_key_value(self):
        assert "[REDACTED]" in _sanitize_log_line("password=SuperSecret123")

    def test_password_with_colon(self):
        assert "[REDACTED]" in _sanitize_log_line("password: my_password")

    def test_secret_key_value(self):
        assert "[REDACTED]" in _sanitize_log_line("secret=abc123xyz")

    def test_token_key_value(self):
        assert "[REDACTED]" in _sanitize_log_line("token=eyJhbGciOiJIUzI1NiJ9")

    def test_credential_key_value(self):
        assert "[REDACTED]" in _sanitize_log_line("credential=some_cred")

    def test_key_key_value(self):
        assert "[REDACTED]" in _sanitize_log_line("key = abcdef123456")

    def test_private_key_rsa(self):
        assert "[REDACTED]" in _sanitize_log_line("-----BEGIN RSA PRIVATE KEY-----")

    def test_private_key_ec(self):
        assert "[REDACTED]" in _sanitize_log_line("-----BEGIN EC PRIVATE KEY-----")

    def test_private_key_generic(self):
        assert "[REDACTED]" in _sanitize_log_line("-----BEGIN PRIVATE KEY-----")

    def test_supabase_service_key(self):
        assert "[REDACTED]" in _sanitize_log_line(
            "supabase_service_key=eyJhbGciOiJIUzI1NiJ9.xxx"
        )

    # ── Texte sain non modifié ────────────────────────────────────

    def test_safe_text_unchanged(self):
        safe = "Terraform plan: 3 to add, 0 to change, 0 to destroy"
        assert _sanitize_log_line(safe) == safe

    def test_empty_string(self):
        assert _sanitize_log_line("") == ""

    def test_normal_terraform_output(self):
        line = "google_compute_instance.main: Creating..."
        assert _sanitize_log_line(line) == line

    def test_apply_complete(self):
        line = "Apply complete! Resources: 2 added, 0 changed, 0 destroyed."
        assert _sanitize_log_line(line) == line

    # ── Cas limites ───────────────────────────────────────────────

    def test_case_insensitive(self):
        assert "[REDACTED]" in _sanitize_log_line("PASSWORD=secret123")
        assert "[REDACTED]" in _sanitize_log_line("Secret=abc")
        assert "[REDACTED]" in _sanitize_log_line("TOKEN=xyz")

    def test_multiple_sensitive_in_one_line(self):
        line = "password=abc token=xyz"
        result = _sanitize_log_line(line)
        assert "abc" not in result
        assert "xyz" not in result

    def test_password_in_context(self):
        line = 'root_password = "SuperSecret123"'
        result = _sanitize_log_line(line)
        # Le pattern devrait matcher root_password = ...
        assert "[REDACTED]" in result


# ══════════════════════════════════════════════════════════════════
#  Tests : deploy_task
# ══════════════════════════════════════════════════════════════════

class TestDeployTask:
    """Tests de la tâche Celery deploy_task avec mocks."""

    @patch("src.simulation.InfracostSimulator")
    def test_deploy_task_success(self, MockSimulator):
        """Un déploiement réussi retourne status=SUCCESS."""
        from src.tasks import deploy_task

        mock_sim = MagicMock()
        mock_sim.deploy.return_value = iter([
            "📝 Initialisation...",
            "Terraform plan...",
            "Apply complete! Resources: 1 added.",
        ])
        MockSimulator.return_value = mock_sim

        # Mock update_state pour éviter la connexion Redis
        with patch.object(deploy_task, "update_state"):
            result = deploy_task.run(
                resources=[{"type": "compute", "machine_type": "e2-micro"}],
                deployment_id="test-deploy-123",
                project_id="test-project",
                timeout=30,
            )

        assert result["status"] == "SUCCESS"
        assert result["deployment_id"] == "test-deploy-123"
        assert isinstance(result["logs"], list)
        assert len(result["logs"]) > 0

    @patch("src.simulation.InfracostSimulator")
    def test_deploy_task_failure(self, MockSimulator):
        """Un déploiement échoué retourne status=ERROR."""
        from src.tasks import deploy_task

        mock_sim = MagicMock()
        mock_sim.deploy.side_effect = RuntimeError("Terraform failed")
        MockSimulator.return_value = mock_sim

        with patch.object(deploy_task, "update_state"):
            result = deploy_task.run(
                resources=[{"type": "compute"}],
                deployment_id="test-fail",
                project_id="test-project",
                timeout=30,
            )

        assert result["status"] == "ERROR"
        assert "Terraform failed" in result["error"]
        assert result["deployment_id"] == "test-fail"

    @patch("src.simulation.InfracostSimulator")
    def test_deploy_task_sanitizes_logs(self, MockSimulator):
        """Les logs de déploiement doivent être sanitizés."""
        from src.tasks import deploy_task

        mock_sim = MagicMock()
        mock_sim.deploy.return_value = iter([
            "Normal output",
            "password=SuperSecret123",
        ])
        MockSimulator.return_value = mock_sim

        with patch.object(deploy_task, "update_state"):
            result = deploy_task.run(
                resources=[{"type": "compute"}],
                deployment_id="test-sanitize",
                project_id="test-project",
            )

        # Le mot de passe ne doit pas apparaître dans les logs
        all_logs = " ".join(result["logs"])
        assert "SuperSecret123" not in all_logs

    @patch("src.simulation.InfracostSimulator")
    def test_deploy_task_returns_logs(self, MockSimulator):
        """La tâche doit retourner les logs de chaque étape."""
        from src.tasks import deploy_task

        mock_sim = MagicMock()
        mock_sim.deploy.return_value = iter(["line1", "line2", "line3"])
        MockSimulator.return_value = mock_sim

        with patch.object(deploy_task, "update_state"):
            result = deploy_task.run(
                resources=[{"type": "compute"}],
                deployment_id="test-progress",
                project_id="test-project",
            )

        # Les logs doivent contenir les lignes émises + le message initial
        assert len(result["logs"]) >= 3


# ══════════════════════════════════════════════════════════════════
#  Tests : destroy_task
# ══════════════════════════════════════════════════════════════════

class TestDestroyTask:
    """Tests de la tâche Celery destroy_task avec mocks."""

    @patch("src.simulation.InfracostSimulator")
    def test_destroy_task_success(self, MockSimulator):
        """Une destruction réussie retourne status=SUCCESS."""
        from src.tasks import destroy_task

        mock_sim = MagicMock()
        mock_sim.destroy.return_value = iter([
            "🔥 Destruction...",
            "Destroy complete! Resources: 1 destroyed.",
        ])
        MockSimulator.return_value = mock_sim

        with patch.object(destroy_task, "update_state"):
            result = destroy_task.run(
                resources=[{"type": "compute"}],
                deployment_id="test-destroy",
                project_id="test-project",
                timeout=30,
            )

        assert result["status"] == "SUCCESS"
        assert result["deployment_id"] == "test-destroy"

    @patch("src.simulation.InfracostSimulator")
    def test_destroy_task_failure(self, MockSimulator):
        """Une destruction échouée retourne status=ERROR."""
        from src.tasks import destroy_task

        mock_sim = MagicMock()
        mock_sim.destroy.side_effect = RuntimeError("Cannot destroy")
        MockSimulator.return_value = mock_sim

        with patch.object(destroy_task, "update_state"):
            result = destroy_task.run(
                resources=[{"type": "compute"}],
                deployment_id="test-destroy-fail",
                project_id="test-project",
            )

        assert result["status"] == "ERROR"
        assert "Cannot destroy" in result["error"]

    @patch("src.simulation.InfracostSimulator")
    def test_destroy_task_sanitizes_sensitive_errors(self, MockSimulator):
        """Les erreurs de destruction doivent être sanitizées."""
        from src.tasks import destroy_task

        mock_sim = MagicMock()
        mock_sim.destroy.side_effect = RuntimeError("password=leaked123 in config")
        MockSimulator.return_value = mock_sim

        with patch.object(destroy_task, "update_state"):
            result = destroy_task.run(
                resources=[{"type": "compute"}],
                deployment_id="test-sanitize-err",
                project_id="test-project",
            )

        assert "leaked123" not in result["error"]


# ══════════════════════════════════════════════════════════════════
#  Tests : Patterns de filtrage
# ══════════════════════════════════════════════════════════════════

class TestSensitivePatterns:
    """Vérifie que les patterns regex sont bien compilés et fonctionnels."""

    def test_patterns_are_compiled(self):
        """Tous les patterns doivent être des regex compilés."""
        import re
        for p in _SENSITIVE_PATTERNS:
            assert isinstance(p, re.Pattern)

    def test_patterns_count(self):
        """Il doit y avoir au moins 3 patterns de filtrage."""
        assert len(_SENSITIVE_PATTERNS) >= 3
