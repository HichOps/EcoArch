"""Poste un commentaire de rapport de coûts sur une Merge Request GitLab.

Sécurité :
- CRIT-5 : Validation whitelist de CI_SERVER_URL pour empêcher SSRF.
- ARCH-4 : Utilisation de logging au lieu de print().
- ARCH-5 : Import corrigé (src.parser au lieu de parser).
"""
import logging
import os
from urllib.parse import urlparse

import requests

from src.parser import EcoArchParser

logger = logging.getLogger(__name__)

REPORT_PATH = "infracost-report.json"
TIMEOUT_SECONDS = 30

# ── CRIT-5 : Whitelist des serveurs GitLab autorisés ──────────────
_ALLOWED_GITLAB_HOSTS = {
    "gitlab.com",
    "gitlab. music-music.net",
}
# Permet d'ajouter un hôte custom via variable d'environnement
_EXTRA_HOST = os.getenv("ECOARCH_GITLAB_HOST", "")
if _EXTRA_HOST:
    _ALLOWED_GITLAB_HOSTS.add(_EXTRA_HOST.lower().strip())


def _validate_server_url(url: str) -> bool:
    """Vérifie que l'URL du serveur GitLab est dans la whitelist.

    Protège contre les attaques SSRF où un attaquant manipulerait
    CI_SERVER_URL pour pointer vers un serveur interne.
    """
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""

        if parsed.scheme not in ("https", "http"):
            logger.error("SSRF blocked: schéma non autorisé '%s'", parsed.scheme)
            return False

        if host.lower() not in _ALLOWED_GITLAB_HOSTS:
            logger.error("SSRF blocked: hôte non autorisé '%s'", host)
            return False

        return True
    except Exception:
        logger.error("SSRF blocked: URL invalide '%s'", url, exc_info=True)
        return False


def post_gitlab_comment() -> None:
    """Poste le rapport Infracost comme commentaire sur la MR GitLab."""
    mr_iid = os.getenv("CI_MERGE_REQUEST_IID")

    if not mr_iid:
        logger.info("Pas de Merge Request, commentaire ignoré.")
        return

    project_id = os.getenv("CI_PROJECT_ID")
    token = os.getenv("GITLAB_TOKEN")
    server_url = os.getenv("CI_SERVER_URL", "")

    if not all([project_id, token, server_url]):
        logger.error("Variables GitLab manquantes (CI_PROJECT_ID, GITLAB_TOKEN, CI_SERVER_URL)")
        return

    # ── CRIT-5 : Validation SSRF ──
    if not _validate_server_url(server_url):
        return

    # Génération du rapport
    parser = EcoArchParser(REPORT_PATH)
    report = parser.generate_markdown_report()

    # Construction de l'URL avec des composants validés
    url = f"{server_url.rstrip('/')}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": token}

    try:
        response = requests.post(
            url,
            headers=headers,
            json={"body": report},
            timeout=TIMEOUT_SECONDS,
        )

        if response.status_code == 201:
            logger.info("Commentaire posté sur la MR #%s", mr_iid)
        else:
            logger.error("Erreur API: %s - %s", response.status_code, response.text[:200])

    except requests.RequestException as e:
        logger.error("Erreur réseau: %s", e)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    post_gitlab_comment()
