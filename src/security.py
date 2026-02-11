"""Sanitisation et validation des entrées utilisateur pour Terraform/Infracost.

Cette couche applique une stratégie de whitelist stricte (GreenOps & Security):
- Aucune interpolation directe de valeurs utilisateur dans du HCL.
- Toutes les valeurs critiques (machine_type, db_tier, storage_class, deployment_id)
  sont validées contre des Regex ou des listes autorisées.
"""
from __future__ import annotations

import re
from typing import Any

from .config import Config, GCPConfig


class ValidationError(ValueError):
    """Erreur de validation des entrées utilisateur destinées à Terraform."""


class InputSanitizer:
    """Sanitise et valide les champs critiques avant génération Terraform.

    Cette classe centralise toute la logique de validation afin d'éviter les
    divergences (DRY) entre les différents modules (simulation, déploiement…).
    """

    # Patterns de sécurité
    _RE_DEPLOYMENT_ID = re.compile(r"^[a-z0-9][a-z0-9\-]{1,30}$")
    _RE_SAFE_VALUE = re.compile(r"^[a-zA-Z0-9_\-./]+$")

    # Whitelists construites depuis la configuration GCP
    _ALLOWED_MACHINE_TYPES: set[str] = set(GCPConfig.INSTANCE_TYPES) | {
        "e2-highcpu-2",
        "e2-highmem-2",
    }
    _ALLOWED_DB_TIERS: set[str] = set(GCPConfig.DB_TIERS) | {"db-custom-2-3840"}
    _ALLOWED_DB_VERSIONS: set[str] = set(GCPConfig.DB_VERSIONS)
    _ALLOWED_STORAGE_CLASSES: set[str] = set(GCPConfig.STORAGE_CLASSES) | {
        "MULTI_REGIONAL"
    }
    _ALLOWED_DISK_TYPES: set[str] = set(GCPConfig.DISK_TYPES)
    _ALLOWED_SOFTWARE_STACKS: set[str] = set(GCPConfig.get_stack_names())

    @classmethod
    def validate_deployment_id(cls, value: str) -> str:
        """Valide et retourne un deployment_id sûr.

        Format imposé: [a-z0-9][a-z0-9-]{1,30}
        """
        if not cls._RE_DEPLOYMENT_ID.match(value):
            raise ValidationError(
                f"deployment_id invalide (alphanum + tirets, 2-31 chars): {value!r}"
            )
        return value

    @classmethod
    def _validate_pattern(cls, value: str, field_name: str) -> str:
        """Vérifie qu'une valeur correspond au pattern alphanumérique sécurisé."""
        if not cls._RE_SAFE_VALUE.match(value):
            raise ValidationError(
                f"{field_name} contient des caractères interdits: {value!r}"
            )
        return value

    @classmethod
    def _validate_whitelist(
        cls,
        value: str,
        field_name: str,
        allowed: set[str],
    ) -> str:
        """Vérifie qu'une valeur appartient à une whitelist stricte."""
        if value not in allowed:
            raise ValidationError(
                f"{field_name} non autorisé: {value!r}. Valeurs acceptées: {sorted(allowed)}"
            )
        return value

    @classmethod
    def validate_int(
        cls,
        value: Any,
        field_name: str,
        min_val: int = 1,
        max_val: int = 64000,
    ) -> int:
        """Valide un entier dans une plage autorisée."""
        try:
            v = int(value)
        except (ValueError, TypeError):
            raise ValidationError(f"{field_name} doit être un entier: {value!r}")
        if not (min_val <= v <= max_val):
            raise ValidationError(
                f"{field_name} hors limites [{min_val}, {max_val}]: {v}"
            )
        return v

    # ── Helpers publics spécialisés ────────────────────────────────

    @classmethod
    def validate_machine_type(cls, value: str) -> str:
        """Valide un type de machine Compute Engine contre la whitelist GCPConfig."""
        return cls._validate_whitelist(
            value, "machine_type", cls._ALLOWED_MACHINE_TYPES
        )

    @classmethod
    def validate_db_tier(cls, value: str) -> str:
        """Valide un tier Cloud SQL contre la whitelist GCPConfig."""
        return cls._validate_whitelist(value, "db_tier", cls._ALLOWED_DB_TIERS)

    @classmethod
    def validate_db_version(cls, value: str) -> str:
        """Valide une version de base de données contre la whitelist GCPConfig."""
        return cls._validate_whitelist(value, "db_version", cls._ALLOWED_DB_VERSIONS)

    @classmethod
    def validate_storage_class(cls, value: str) -> str:
        """Valide une classe de stockage Cloud Storage contre la whitelist GCPConfig."""
        return cls._validate_whitelist(
            value, "storage_class", cls._ALLOWED_STORAGE_CLASSES
        )

    @classmethod
    def validate_disk_type(cls, value: str) -> str:
        """Valide un type de disque persistant contre la whitelist GCPConfig."""
        return cls._validate_whitelist(value, "disk_type", cls._ALLOWED_DISK_TYPES)

    @classmethod
    def validate_software_stack(cls, value: str) -> str:
        """Valide un identifiant de stack logicielle contre la whitelist GCPConfig."""
        return cls._validate_whitelist(
            value, "software_stack", cls._ALLOWED_SOFTWARE_STACKS
        )

    @classmethod
    def validate_wizard_answers(cls, answers: dict[str, Any]) -> dict[str, str]:
        """Valide l'ensemble des réponses du Wizard."""
        validated = {}
        
        # Environment
        env = str(answers.get("environment", "dev"))
        if env not in {"dev", "prod"}:
            env = "dev"
        validated["environment"] = env
        
        # Traffic
        traffic = str(answers.get("traffic", "low"))
        if traffic not in {"low", "medium", "high"}:
            traffic = "low"
        validated["traffic"] = traffic
        
        # Workload
        workload = str(answers.get("workload", "general"))
        if workload not in {"general", "cpu", "memory"}:
            workload = "general"
        validated["workload"] = workload
        
        # Criticality
        crit = str(answers.get("criticality", "low"))
        if crit not in {"low", "high"}:
            crit = "low"
        validated["criticality"] = crit
        
        # Type
        atype = str(answers.get("type", "web"))
        if atype not in {"web", "api", "backend", "batch", "microservices"}:
            atype = "web"
        validated["type"] = atype
        
        # Region (optionnel)
        if "region" in answers:
            region = str(answers["region"])
            if region in GCPConfig.REGIONS:
                validated["region"] = region
            else:
                validated["region"] = Config.DEFAULT_REGION

        return validated

    # ── Validation de ressource complète ───────────────────────────

    @classmethod
    def validate_resource(cls, res: dict[str, Any]) -> dict[str, Any]:
        """Valide et normalise une ressource avant génération Terraform.

        Champs vérifiés:
        - type ∈ {compute, sql, storage, load_balancer}
        - machine_type, db_tier, storage_class, software_stack via whitelist
        - disk_size borné [10, 64000]
        """
        resource_type = str(res.get("type", "compute"))
        cls._validate_whitelist(
            resource_type,
            "type",
            {"compute", "sql", "storage", "load_balancer"},
        )

        validated: dict[str, Any] = {"type": resource_type}

        if resource_type == "compute":
            machine = str(res.get("machine_type", "e2-medium"))
            stack = str(res.get("software_stack", "none"))
            disk = res.get("disk_size", 50)
            disk_type = str(res.get("disk_type", GCPConfig.DEFAULT_DISK_TYPE))

            validated["machine_type"] = cls.validate_machine_type(machine)
            validated["disk_size"] = cls.validate_int(
                disk, "disk_size", min_val=GCPConfig.MIN_STORAGE_GB, max_val=GCPConfig.MAX_STORAGE_GB
            )
            validated["disk_type"] = cls.validate_disk_type(disk_type)
            validated["software_stack"] = cls.validate_software_stack(stack)

        elif resource_type == "sql":
            tier = str(res.get("db_tier", "db-f1-micro"))
            version = str(res.get("db_version", "POSTGRES_14"))
            validated["db_tier"] = cls.validate_db_tier(tier)
            validated["db_version"] = cls.validate_db_version(version)

        elif resource_type == "storage":
            storage_class = str(res.get("storage_class", "STANDARD"))
            validated["storage_class"] = cls.validate_storage_class(storage_class)

        # load_balancer: aucun champ contrôlé par l'utilisateur

        return validated


__all__ = ["InputSanitizer", "ValidationError"]

