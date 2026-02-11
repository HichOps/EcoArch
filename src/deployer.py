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

from src.config import Config, GCPConfig

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


def _enrich_resources_for_terraform(
    resources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Enrichit les ressources compute avec le contenu du startup_script.

    Le script est récupéré depuis GCPConfig.SOFTWARE_STACKS en fonction
    du champ ``software_stack`` de chaque ressource.
    Cela permet à Terraform d'utiliser ``metadata_startup_script``
    pour installer Docker, Nginx, LAMP, etc. au boot de la VM.
    """
    enriched: list[dict[str, Any]] = []
    for res in resources:
        res = dict(res)  # copie pour ne pas muter l'original
        if res.get("type") == "compute":
            stack_id = res.get("software_stack", "none")
            res["startup_script"] = GCPConfig.get_startup_script(stack_id)
        enriched.append(res)
    return enriched


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

    # Enrichir les ressources compute avec les startup_scripts
    enriched = _enrich_resources_for_terraform(resources)

    # Sérialiser le panier enrichi en JSON compact
    architecture_json = json.dumps(enriched, separators=(",", ":"))

    url = f"https://gitlab.com/api/v4/projects/{project_id}/trigger/pipeline"

    payload = {
        "token": token,
        "ref": Config.GITLAB_REF,
        "variables[TF_VAR_architecture_json]": architecture_json,
        "variables[TF_VAR_deployment_id]": deployment_id,
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


# ── Pipeline Status Polling ───────────────────────────────────

# Mapping GitLab pipeline status → EcoArch audit status
_GITLAB_STATUS_MAP: dict[str, str] = {
    "success": "SUCCESS",
    "failed": "FAILED",
    "canceled": "CANCELLED",
}

# Statuts "en cours" de GitLab (on ne met pas à jour l'audit)
_GITLAB_RUNNING_STATUSES = {
    "created", "waiting_for_resource", "preparing",
    "pending", "running", "manual", "scheduled",
}


def check_pipeline_status(pipeline_id: int | str) -> str | None:
    """Interroge l'API GitLab pour récupérer le statut d'un pipeline.

    Retourne le statut EcoArch (SUCCESS / FAILED / CANCELLED / RUNNING)
    ou None si impossible de récupérer le statut.

    Nécessite GITLAB_API_TOKEN avec scope ``read_api``.
    """
    api_token = Config.GITLAB_API_TOKEN
    project_id = Config.GITLAB_PROJECT_ID

    if not api_token or not project_id:
        return None

    url = f"https://gitlab.com/api/v4/projects/{project_id}/pipelines/{pipeline_id}"
    headers = {"PRIVATE-TOKEN": api_token}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.warning(
                "GitLab API %s pour pipeline %s: %s",
                resp.status_code, pipeline_id, resp.text[:200],
            )
            return None

        gitlab_status = resp.json().get("status", "")

        if gitlab_status in _GITLAB_STATUS_MAP:
            return _GITLAB_STATUS_MAP[gitlab_status]
        if gitlab_status in _GITLAB_RUNNING_STATUSES:
            return "RUNNING"

        logger.info("Statut GitLab inconnu: %s", gitlab_status)
        return None

    except Exception as exc:
        logger.warning("Erreur polling pipeline %s: %s", pipeline_id, exc)
        return None


def extract_pipeline_id(pipeline_url: str) -> int | None:
    """Extrait le pipeline_id depuis une URL GitLab.

    Format attendu : https://gitlab.com/…/-/pipelines/12345
    """
    if not pipeline_url:
        return None
    try:
        return int(pipeline_url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        return None
