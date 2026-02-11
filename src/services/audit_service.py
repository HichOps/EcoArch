"""Service de gestion des logs d'audit.

Centralise les interactions avec Supabase pour l'historique des actions (Audit Logs).
Extrait la logique métier de frontend/state.py.
"""
import logging
from typing import Any

from src.config import Config
from src.deployer import check_pipeline_status, extract_pipeline_id

logger = logging.getLogger(__name__)


class AuditService:
    """Service d'audit (Singleton sans état ou méthodes statiques)."""

    @staticmethod
    def create_log(
        user: str,
        action: str,
        target_id: str,
        resources_summary: str,
        cost: float,
        pipeline_url: str = "",
    ) -> int | None:
        """Crée une entrée dans la table audit_logs."""
        sb = Config.get_supabase_client()
        if not sb:
            return None

        try:
            row = {
                "user": user,
                "action": action,
                "resources_summary": resources_summary,
                "total_cost": cost,
                "status": "PENDING",
            }
            if pipeline_url:
                row["pipeline_url"] = pipeline_url

            res = sb.table("audit_logs").insert(row).execute()
            return res.data[0]["id"] if res.data else None
        except Exception:
            logger.warning(
                "Échec création audit log pour %s/%s", action, target_id, exc_info=True
            )
            return None

    @staticmethod
    def update_log(audit_id: int | None, status: str, pipeline_url: str = "") -> None:
        """Met à jour le statut d'un log existant."""
        if not audit_id:
            return

        sb = Config.get_supabase_client()
        if not sb:
            return

        try:
            update_data: dict[str, Any] = {"status": status}
            if pipeline_url:
                update_data["pipeline_url"] = pipeline_url
            
            sb.table("audit_logs").update(update_data).eq("id", audit_id).execute()
        except Exception:
            logger.warning(
                "Échec mise à jour audit #%s → %s", audit_id, status, exc_info=True
            )

    @staticmethod
    def fetch_recent_logs(limit: int = 50) -> list[dict[str, Any]]:
        """Récupère les derniers logs."""
        sb = Config.get_supabase_client()
        if not sb:
            return []

        try:
            res = (
                sb.table("audit_logs")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return res.data or []
        except Exception:
            logger.warning("Échec chargement audit logs", exc_info=True)
            return []

    @staticmethod
    def sync_pipeline_statuses(logs: list[dict[str, Any]]) -> bool:
        """Vérifie et met à jour le statut des pipelines GitLab en attente.
        
        Retourne True si au moins un statut a changé.
        """
        if check_pipeline_status is None or extract_pipeline_id is None:
            return False

        sb = Config.get_supabase_client()
        if not sb:
            return False

        any_change = False

        for row in logs:
            status = row.get("status", "")
            # On ne vérifie que les statuts intermédiaires
            if status not in ("PENDING", "PIPELINE_SENT"):
                continue

            p_url = row.get("pipeline_url", "")
            p_id = extract_pipeline_id(p_url)
            if not p_id:
                continue

            new_status = check_pipeline_status(p_id)
            if new_status and new_status != status:
                any_change = True
                try:
                    sb.table("audit_logs").update({"status": new_status}).eq(
                        "id", row["id"]
                    ).execute()
                    row["status"] = new_status  # Update in-place for UI
                except Exception:
                    logger.warning(
                        "Échec sync pipeline #%s → %s",
                        row.get("id"),
                        new_status,
                        exc_info=True,
                    )
        
        return any_change
