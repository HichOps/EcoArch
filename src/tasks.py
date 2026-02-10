"""Tâches Celery asynchrones pour l'exécution Terraform.

Ce module découple l'exécution Terraform du thread Reflex principal.
Chaque tâche met à jour son état via `self.update_state()` pour
permettre au frontend de sonder la progression en temps réel.

Broker : Redis (déjà déployé dans docker-compose.yml)
"""
import json
import logging
import os
import re
from typing import Any

from celery import Celery

from src.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Celery App ────────────────────────────────────────────────────
REDIS_URL = Config.REDIS_URL

app = Celery(
    "ecoarch_workers",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    task_acks_late=True,              # Re-queue si le worker meurt
    worker_prefetch_multiplier=1,     # 1 tâche à la fois par worker
    result_expires=3600,              # Nettoyage résultats après 1h
    task_time_limit=600,              # Hard kill après 10 min
    task_soft_time_limit=540,         # Signal SoftTimeLimitExceeded à 9 min
)

# ── Patterns de filtrage pour les logs sensibles ──────────────────
_SENSITIVE_PATTERNS = [
    re.compile(r"(password|secret|key|token|credential)\s*[:=]\s*\S+", re.I),
    re.compile(r"-----BEGIN (RSA |EC )?PRIVATE KEY-----"),
    re.compile(r"supabase_service_key\s*[:=]\s*\S+", re.I),
]


def _sanitize_log_line(line: str) -> str:
    """Filtre les données sensibles d'une ligne de log Terraform."""
    for pattern in _SENSITIVE_PATTERNS:
        line = pattern.sub("[REDACTED]", line)
    return line


# ── Tâche : Déploiement ──────────────────────────────────────────
@app.task(bind=True, name="ecoarch.deploy")
def deploy_task(
    self,
    resources: list[dict[str, Any]],
    deployment_id: str,
    project_id: str,
    timeout: int = 300,
) -> dict:
    """Exécute le déploiement Terraform de manière asynchrone.

    Retourne un dict avec le résultat final.
    Met à jour self.update_state() à chaque étape pour le polling côté UI.
    """
    # Import tardif pour éviter les imports circulaires au chargement
    from src.simulation import InfracostSimulator

    logs: list[str] = []

    def _push(msg: str, phase: str = "running") -> None:
        safe = _sanitize_log_line(msg)
        logs.append(safe)
        # Garder les 100 dernières lignes dans le state Celery
        self.update_state(
            state="PROGRESS",
            meta={
                "phase": phase,
                "logs": logs[-100:],
                "current": safe,
            },
        )

    try:
        sim = InfracostSimulator(project_id=project_id, timeout=timeout)

        _push(f"📝 Tâche Celery démarrée – ID: {deployment_id}", "init")

        for line in sim.deploy(resources, deployment_id):
            _push(line)

        _push("✅ Déploiement terminé", "success")

        return {
            "status": "SUCCESS",
            "deployment_id": deployment_id,
            "logs": logs[-100:],
        }

    except Exception as exc:
        error_msg = _sanitize_log_line(str(exc))
        logs.append(f"❌ ERROR: {error_msg}")
        logger.exception("deploy_task failed for %s", deployment_id)
        # Marquer la tâche comme échouée mais retourner un résultat exploitable
        return {
            "status": "ERROR",
            "deployment_id": deployment_id,
            "error": error_msg,
            "logs": logs[-100:],
        }


# ── Tâche : Destruction ──────────────────────────────────────────
@app.task(bind=True, name="ecoarch.destroy")
def destroy_task(
    self,
    resources: list[dict[str, Any]],
    deployment_id: str,
    project_id: str,
    timeout: int = 300,
) -> dict:
    """Exécute la destruction Terraform de manière asynchrone."""
    from src.simulation import InfracostSimulator

    logs: list[str] = []

    def _push(msg: str, phase: str = "running") -> None:
        safe = _sanitize_log_line(msg)
        logs.append(safe)
        self.update_state(
            state="PROGRESS",
            meta={
                "phase": phase,
                "logs": logs[-100:],
                "current": safe,
            },
        )

    try:
        sim = InfracostSimulator(project_id=project_id, timeout=timeout)

        _push(f"🔥 Destruction – Cible: {deployment_id}", "init")

        for line in sim.destroy(resources, deployment_id):
            _push(line)

        _push("🗑️ Destruction terminée", "success")

        return {
            "status": "SUCCESS",
            "deployment_id": deployment_id,
            "logs": logs[-100:],
        }

    except Exception as exc:
        error_msg = _sanitize_log_line(str(exc))
        logs.append(f"❌ ERROR: {error_msg}")
        logger.exception("destroy_task failed for %s", deployment_id)
        return {
            "status": "ERROR",
            "deployment_id": deployment_id,
            "error": error_msg,
            "logs": logs[-100:],
        }
