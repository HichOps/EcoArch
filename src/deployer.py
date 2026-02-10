"""Déclencheur de pipeline GitLab CI/CD pour EcoArch.

Remplace l'ancienne logique Celery/Redis.
Envoie une requête POST à l'API GitLab Trigger pour lancer
un pipeline Terraform (init → plan → apply).

Secrets attendus (Secret Manager ou env) :
- GITLAB_TRIGGER_TOKEN : token de déclenchement du pipeline
- GITLAB_PROJECT_ID    : ID numérique du projet GitLab
"""
import json
import logging
from dataclasses import dataclass
from typing import Any

import requests

from src.config import Config

logger = logging.getLogger(__name__)

# ── Constantes ────────────────────────────────────────────────────
_TRIGGER_TIMEOUT = 15  # secondes


@dataclass
class PipelineResult:
    """Résultat d'un déclenchement de pipeline GitLab."""

    success: bool
    pipeline_id: int | None = None
    pipeline_url: str | None = None
    error: str | None = None


def trigger_deployment(
    resources: list[dict[str, Any]],
    deployment_id: str,
    action: str = "apply",
) -> PipelineResult:
    """Déclenche un pipeline GitLab CI/CD via l'API Trigger.

    Args:
        resources: Liste de ressources du panier (sérialisée en JSON).
        deployment_id: Identifiant unique du déploiement.
        action: "apply" pour déployer, "destroy" pour détruire.

    Returns:
        PipelineResult avec l'URL du pipeline ou un message d'erreur.
    """
    token = Config.GITLAB_TRIGGER_TOKEN
    project_id = Config.GITLAB_PROJECT_ID

    if not token:
        msg = "GITLAB_TRIGGER_TOKEN non configuré – impossible de déclencher le pipeline"
        logger.error(msg)
        return PipelineResult(success=False, error=msg)

    if not project_id:
        msg = "GITLAB_PROJECT_ID non configuré"
        logger.error(msg)
        return PipelineResult(success=False, error=msg)

    # Sérialiser le panier en JSON compact
    architecture_json = json.dumps(resources, separators=(",", ":"))

    url = f"https://gitlab.com/api/v4/projects/{project_id}/trigger/pipeline"

    payload = {
        "token": token,
        "ref": Config.GITLAB_REF,
        "variables[TF_VAR_architecture_json]": architecture_json,
        "variables[ECOARCH_DEPLOYMENT_ID]": deployment_id,
        "variables[ECOARCH_ACTION]": action,
    }

    logger.info(
        "Triggering GitLab pipeline: project=%s, ref=%s, action=%s, deployment=%s",
        project_id,
        Config.GITLAB_REF,
        action,
        deployment_id,
    )

    try:
        resp = requests.post(url, data=payload, timeout=_TRIGGER_TIMEOUT)

        if resp.status_code == 201:
            data = resp.json()
            pipeline_id = data.get("id")
            pipeline_url = data.get("web_url", "")

            # Construire l'URL si absente
            if not pipeline_url:
                pipeline_url = (
                    f"{Config.GITLAB_PROJECT_URL}/-/pipelines/{pipeline_id}"
                )

            logger.info(
                "Pipeline déclenché: id=%s, url=%s",
                pipeline_id,
                pipeline_url,
            )

            return PipelineResult(
                success=True,
                pipeline_id=pipeline_id,
                pipeline_url=pipeline_url,
            )
        else:
            error_msg = f"GitLab API {resp.status_code}: {resp.text[:200]}"
            logger.error("Échec déclenchement pipeline: %s", error_msg)
            return PipelineResult(success=False, error=error_msg)

    except requests.Timeout:
        msg = "Timeout lors de l'appel à l'API GitLab"
        logger.error(msg)
        return PipelineResult(success=False, error=msg)

    except requests.ConnectionError as exc:
        msg = f"Connexion impossible à GitLab: {exc}"
        logger.error(msg)
        return PipelineResult(success=False, error=msg)

    except Exception as exc:
        msg = f"Erreur inattendue lors du trigger: {exc}"
        logger.error(msg, exc_info=True)
        return PipelineResult(success=False, error=msg)


def trigger_destruction(
    resources: list[dict[str, Any]],
    deployment_id: str,
) -> PipelineResult:
    """Raccourci pour déclencher une destruction via GitLab CI/CD."""
    return trigger_deployment(resources, deployment_id, action="destroy")
