"""Tests unitaires pour le module de sécurité (InputSanitizer)."""

import pytest

from src.security import InputSanitizer, ValidationError


class TestInputSanitizerDeploymentId:
    """Validation du deployment_id (anti-injection HCL)."""

    def test_valid_deployment_id_passes(self):
        assert InputSanitizer.validate_deployment_id("abc-123") == "abc-123"

    @pytest.mark.parametrize(
        "value",
        [
            "ABC",  # majuscules interdites
            "a" * 40,  # trop long
            " invalid",  # espace
            "évil",  # caractère non ASCII sûr
        ],
    )
    def test_invalid_deployment_id_raises(self, value: str):
        with pytest.raises(ValidationError):
            InputSanitizer.validate_deployment_id(value)


class TestInputSanitizerResource:
    """Validation des ressources complètes."""

    def test_invalid_resource_type_rejected(self):
        with pytest.raises(ValidationError, match="type non autorisé"):
            InputSanitizer.validate_resource({"type": "unknown_thing"})

    def test_invalid_machine_type_rejected(self):
        with pytest.raises(ValidationError, match="machine_type non autorisé"):
            InputSanitizer.validate_resource(
                {"type": "compute", "machine_type": "totally-invalid", "disk_size": 50}
            )

    def test_valid_compute_resource_passes(self):
        res = InputSanitizer.validate_resource(
            {
                "type": "compute",
                "machine_type": "e2-medium",
                "disk_size": 50,
                "software_stack": "none",
            }
        )
        assert res["machine_type"] == "e2-medium"
        assert res["disk_size"] == 50
        assert res["software_stack"] == "none"

