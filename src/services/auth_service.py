"""Service d'authentification pour EcoArch.

Encapsule la vérification des credentials via Supabase et la
validation des tokens HMAC. Aucune logique UI (Reflex) ici.

Sécurité :
- Message d'erreur générique pour prévenir l'énumération d'utilisateurs.
- Token HMAC-SHA256 pour preuve d'identité côté serveur.
- Mode dégradé explicite quand Supabase est indisponible.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass

from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class AuthResult:
    """Résultat d'une tentative d'authentification."""

    authenticated: bool
    username: str = ""
    role: str = ""
    error: str = ""
    degraded: bool = False  # True quand Supabase a échoué (mode dégradé)


class AuthService:
    """Service d'authentification centralisé (séparation State ↔ métier)."""

    # ── Vérification credentials ──────────────────────────────────

    @staticmethod
    def verify_credentials(username: str) -> AuthResult:
        """Vérifie les credentials via la table Supabase ``profiles``.

        Returns:
            AuthResult avec le statut d'authentification et le rôle.
        """
        logger.info("Tentative de connexion pour: %s", username)

        sb = Config.get_supabase_client()
        if sb is not None:
            try:
                res = (
                    sb.table("profiles")
                    .select("role")
                    .eq("username", username)
                    .limit(1)
                    .execute()
                )

                if res.data:
                    role = res.data[0].get("role", "viewer")
                    logger.info("Utilisateur validé: %s (role=%s)", username, role)
                    return AuthResult(
                        authenticated=True, username=username, role=role
                    )

                logger.warning("Échec login: %s", username)
                return AuthResult(
                    authenticated=False, error="Identifiants invalides"
                )

            except Exception as exc:
                logger.warning(
                    "Erreur Supabase profiles: %s", exc, exc_info=True
                )
                return AuthResult(
                    authenticated=True,
                    username=username,
                    role="viewer",
                    degraded=True,
                )

        # Pas de Supabase (dev local) → accepter tout le monde
        logger.info("Supabase non configuré – auth locale pour: %s", username)
        return AuthResult(authenticated=True, username=username, role="admin")

    # ── Tokens HMAC ───────────────────────────────────────────────

    @staticmethod
    def generate_token(username: str) -> str:
        """Génère un token HMAC-SHA256 pour un utilisateur (côté serveur)."""
        if not Config.AUTH_SECRET_KEY:
            return ""
        return hmac.new(
            Config.AUTH_SECRET_KEY.encode(),
            username.encode(),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def verify_token(username: str, token: str) -> bool:
        """Vérifie le token d'authentification d'un utilisateur."""
        if not Config.AUTH_ENABLED:
            return True  # Auth désactivée en dev
        expected = AuthService.generate_token(username)
        return hmac.compare_digest(expected, token)
