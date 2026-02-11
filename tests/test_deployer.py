"""Tests du module src/deployer.py – déclencheur de pipeline GitLab CI/CD.

Couvre :
- trigger_deployment : succès, erreurs API, token manquant, timeout, connexion
- trigger_destruction : raccourci avec action=destroy
- PipelineResult : dataclass de résultat
"""
import json

import pytest
from unittest.mock import patch, MagicMock

from src.deployer import (
    trigger_deployment,
    trigger_destruction,
    PipelineResult,
    check_pipeline_status,
    extract_pipeline_id,
    _enrich_resources_for_terraform,
)


# ══════════════════════════════════════════════════════════════════
#  Tests : PipelineResult
# ══════════════════════════════════════════════════════════════════

class TestPipelineResult:
    """Vérifie la dataclass PipelineResult."""

    def test_success_result(self):
        r = PipelineResult(success=True, pipeline_id=123, pipeline_url="https://gitlab.com/pipelines/123")
        assert r.success is True
        assert r.pipeline_id == 123
        assert "123" in r.pipeline_url

    def test_error_result(self):
        r = PipelineResult(success=False, error="Token invalide")
        assert r.success is False
        assert r.pipeline_id is None
        assert "Token invalide" in r.error

    def test_defaults(self):
        r = PipelineResult(success=True)
        assert r.pipeline_id is None
        assert r.pipeline_url is None
        assert r.error is None


# ══════════════════════════════════════════════════════════════════
#  Tests : trigger_deployment
# ══════════════════════════════════════════════════════════════════

class TestTriggerDeployment:
    """Tests du déclenchement de pipeline GitLab."""

    RESOURCES = [
        {"type": "compute", "machine_type": "e2-medium", "display_name": "VM e2-medium"},
    ]

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_success_returns_pipeline_url(self, MockConfig, mock_post):
        """Un appel réussi (201) retourne l'URL du pipeline."""
        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test-token"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {
            "id": 456,
            "web_url": "https://gitlab.com/hichops/ecoarch/-/pipelines/456",
        }
        mock_post.return_value = mock_resp

        result = trigger_deployment(self.RESOURCES, "deploy-001")

        assert result.success is True
        assert result.pipeline_id == 456
        assert "456" in result.pipeline_url

        # Vérifier l'appel POST
        call_args = mock_post.call_args
        assert "trigger/pipeline" in call_args[0][0]
        payload = call_args[1]["data"]
        assert payload["token"] == "glptt-test-token"
        assert payload["ref"] == "main"
        # Le panier est enrichi avec startup_script pour les compute
        arch = json.loads(payload["variables[TF_VAR_architecture_json]"])
        assert arch[0]["type"] == "compute"
        assert arch[0]["machine_type"] == "e2-medium"
        assert "startup_script" in arch[0]

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_api_error_returns_failure(self, MockConfig, mock_post):
        """Un code HTTP != 201 retourne un échec."""
        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.text = "Forbidden"
        mock_post.return_value = mock_resp

        result = trigger_deployment(self.RESOURCES, "deploy-002")

        assert result.success is False
        assert "403" in result.error

    @patch("src.deployer.Config")
    def test_missing_token_returns_error(self, MockConfig):
        """Token manquant → échec sans appel réseau."""
        MockConfig.GITLAB_TRIGGER_TOKEN = ""
        MockConfig.GITLAB_PROJECT_ID = "77811562"

        result = trigger_deployment(self.RESOURCES, "deploy-003")

        assert result.success is False
        assert "GITLAB_TRIGGER_TOKEN" in result.error

    @patch("src.deployer.Config")
    def test_missing_project_id_returns_error(self, MockConfig):
        """Project ID manquant → échec."""
        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = ""

        result = trigger_deployment(self.RESOURCES, "deploy-004")

        assert result.success is False
        assert "GITLAB_PROJECT_ID" in result.error

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_timeout_returns_failure(self, MockConfig, mock_post):
        """Timeout réseau → échec gracieux."""
        import requests as real_requests

        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_post.side_effect = real_requests.Timeout("Connection timed out")

        result = trigger_deployment(self.RESOURCES, "deploy-005")

        assert result.success is False
        assert "Timeout" in result.error

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_connection_error_returns_failure(self, MockConfig, mock_post):
        """Erreur de connexion → échec gracieux."""
        import requests as real_requests

        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_post.side_effect = real_requests.ConnectionError("DNS failure")

        result = trigger_deployment(self.RESOURCES, "deploy-006")

        assert result.success is False
        assert "Connexion impossible" in result.error

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_payload_contains_architecture_json(self, MockConfig, mock_post):
        """Le payload doit contenir le panier sérialisé en JSON."""
        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 789, "web_url": "https://example.com/789"}
        mock_post.return_value = mock_resp

        resources = [
            {"type": "compute", "machine_type": "e2-medium"},
            {"type": "sql", "db_tier": "db-f1-micro"},
        ]
        trigger_deployment(resources, "deploy-007", action="apply")

        payload = mock_post.call_args[1]["data"]
        arch_json = payload["variables[TF_VAR_architecture_json]"]
        parsed = json.loads(arch_json)
        assert len(parsed) == 2
        assert parsed[0]["type"] == "compute"
        assert parsed[1]["type"] == "sql"

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_action_variable_sent(self, MockConfig, mock_post):
        """La variable ECOARCH_ACTION doit être transmise."""
        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 101, "web_url": "https://example.com/101"}
        mock_post.return_value = mock_resp

        trigger_deployment(self.RESOURCES, "deploy-008", action="destroy")

        payload = mock_post.call_args[1]["data"]
        assert payload["variables[ECOARCH_ACTION]"] == "destroy"

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_fallback_url_when_web_url_missing(self, MockConfig, mock_post):
        """Si web_url absent de la réponse, construit l'URL manuellement."""
        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 999}  # pas de web_url
        mock_post.return_value = mock_resp

        result = trigger_deployment(self.RESOURCES, "deploy-009")

        assert result.success is True
        assert "999" in result.pipeline_url
        assert "hichops/ecoarch" in result.pipeline_url


# ══════════════════════════════════════════════════════════════════
#  Tests : trigger_destruction
# ══════════════════════════════════════════════════════════════════

class TestTriggerDestruction:
    """Tests du raccourci de destruction."""

    @patch("src.deployer.requests.post")
    @patch("src.deployer.Config")
    def test_destruction_sends_destroy_action(self, MockConfig, mock_post):
        """trigger_destruction envoie action='destroy'."""
        MockConfig.GITLAB_TRIGGER_TOKEN = "glptt-test"
        MockConfig.GITLAB_PROJECT_ID = "77811562"
        MockConfig.GITLAB_REF = "main"
        MockConfig.GITLAB_PROJECT_URL = "https://gitlab.com/hichops/ecoarch"

        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"id": 202, "web_url": "https://example.com/202"}
        mock_post.return_value = mock_resp

        result = trigger_destruction(
            [{"type": "compute"}],
            "destroy-001",
        )

        assert result.success is True
        payload = mock_post.call_args[1]["data"]
        assert payload["variables[ECOARCH_ACTION]"] == "destroy"


# ══════════════════════════════════════════════════════════════════
#  Tests : _enrich_resources_for_terraform
# ══════════════════════════════════════════════════════════════════

class TestEnrichResources:
    """Vérifie l'enrichissement des ressources compute avec startup_script."""

    def test_compute_gets_startup_script(self):
        """Les ressources compute reçoivent le script de leur stack."""
        resources = [{"type": "compute", "machine_type": "e2-micro", "software_stack": "docker"}]
        enriched = _enrich_resources_for_terraform(resources)
        assert len(enriched) == 1
        assert "startup_script" in enriched[0]
        assert "docker" in enriched[0]["startup_script"].lower()

    def test_compute_none_stack_empty_script(self):
        """software_stack='none' → script vide."""
        resources = [{"type": "compute", "machine_type": "e2-micro", "software_stack": "none"}]
        enriched = _enrich_resources_for_terraform(resources)
        assert enriched[0]["startup_script"] == ""

    def test_compute_missing_stack_empty_script(self):
        """Pas de software_stack → script vide (fallback 'none')."""
        resources = [{"type": "compute", "machine_type": "e2-micro"}]
        enriched = _enrich_resources_for_terraform(resources)
        assert enriched[0]["startup_script"] == ""

    def test_sql_not_enriched(self):
        """Les ressources SQL ne sont pas modifiées."""
        resources = [{"type": "sql", "db_tier": "db-f1-micro"}]
        enriched = _enrich_resources_for_terraform(resources)
        assert "startup_script" not in enriched[0]

    def test_storage_not_enriched(self):
        """Les ressources storage ne sont pas modifiées."""
        resources = [{"type": "storage", "storage_class": "STANDARD"}]
        enriched = _enrich_resources_for_terraform(resources)
        assert "startup_script" not in enriched[0]

    def test_original_not_mutated(self):
        """L'enrichissement ne mute pas la liste originale."""
        original = [{"type": "compute", "machine_type": "e2-micro", "software_stack": "docker"}]
        _enrich_resources_for_terraform(original)
        assert "startup_script" not in original[0]

    def test_mixed_resources(self):
        """Seules les compute sont enrichies dans un panier mixte."""
        resources = [
            {"type": "compute", "machine_type": "e2-micro", "software_stack": "web-nginx"},
            {"type": "sql", "db_tier": "db-f1-micro"},
            {"type": "storage", "storage_class": "STANDARD"},
        ]
        enriched = _enrich_resources_for_terraform(resources)
        assert len(enriched) == 3
        assert "startup_script" in enriched[0]
        assert "nginx" in enriched[0]["startup_script"].lower()
        assert "startup_script" not in enriched[1]
        assert "startup_script" not in enriched[2]


# ══════════════════════════════════════════════════════════════════
#  Tests : extract_pipeline_id
# ══════════════════════════════════════════════════════════════════

class TestExtractPipelineId:
    """Tests de l'extraction du pipeline_id depuis une URL."""

    def test_standard_url(self):
        url = "https://gitlab.com/hichops/ecoarch/-/pipelines/2319057640"
        assert extract_pipeline_id(url) == 2319057640

    def test_trailing_slash(self):
        url = "https://gitlab.com/hichops/ecoarch/-/pipelines/12345/"
        assert extract_pipeline_id(url) == 12345

    def test_empty_url(self):
        assert extract_pipeline_id("") is None

    def test_none_url(self):
        assert extract_pipeline_id(None) is None

    def test_invalid_url(self):
        assert extract_pipeline_id("not-a-valid-url") is None


# ══════════════════════════════════════════════════════════════════
#  Tests : check_pipeline_status
# ══════════════════════════════════════════════════════════════════

class TestCheckPipelineStatus:
    """Tests du polling de statut de pipeline GitLab."""

    @patch("src.deployer.requests.get")
    @patch("src.deployer.Config")
    def test_success_status(self, MockConfig, mock_get):
        MockConfig.GITLAB_API_TOKEN = "glpat-xxx"
        MockConfig.GITLAB_PROJECT_ID = "77811562"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "success"}
        mock_get.return_value = mock_resp

        assert check_pipeline_status(123) == "SUCCESS"

    @patch("src.deployer.requests.get")
    @patch("src.deployer.Config")
    def test_failed_status(self, MockConfig, mock_get):
        MockConfig.GITLAB_API_TOKEN = "glpat-xxx"
        MockConfig.GITLAB_PROJECT_ID = "77811562"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "failed"}
        mock_get.return_value = mock_resp

        assert check_pipeline_status(456) == "FAILED"

    @patch("src.deployer.requests.get")
    @patch("src.deployer.Config")
    def test_running_status(self, MockConfig, mock_get):
        MockConfig.GITLAB_API_TOKEN = "glpat-xxx"
        MockConfig.GITLAB_PROJECT_ID = "77811562"

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "running"}
        mock_get.return_value = mock_resp

        assert check_pipeline_status(789) == "RUNNING"

    @patch("src.deployer.Config")
    def test_no_api_token_returns_none(self, MockConfig):
        MockConfig.GITLAB_API_TOKEN = ""
        MockConfig.GITLAB_PROJECT_ID = "77811562"

        assert check_pipeline_status(123) is None

    @patch("src.deployer.requests.get")
    @patch("src.deployer.Config")
    def test_api_error_returns_none(self, MockConfig, mock_get):
        MockConfig.GITLAB_API_TOKEN = "glpat-xxx"
        MockConfig.GITLAB_PROJECT_ID = "77811562"

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.text = "Not found"
        mock_get.return_value = mock_resp

        assert check_pipeline_status(999) is None
