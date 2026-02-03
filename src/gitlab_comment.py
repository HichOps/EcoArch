"""Poste un commentaire de rapport de coûts sur une Merge Request GitLab."""
import os

import requests

from parser import EcoArchParser

REPORT_PATH = "infracost-report.json"
TIMEOUT_SECONDS = 30


def post_gitlab_comment() -> None:
    """Poste le rapport Infracost comme commentaire sur la MR GitLab."""
    # Variables GitLab CI
    mr_iid = os.getenv("CI_MERGE_REQUEST_IID")
    
    if not mr_iid:
        print("⏭️ Pas de Merge Request, commentaire ignoré.")
        return
    
    project_id = os.getenv("CI_PROJECT_ID")
    token = os.getenv("GITLAB_TOKEN")
    server_url = os.getenv("CI_SERVER_URL")
    
    if not all([project_id, token, server_url]):
        print("❌ Variables GitLab manquantes (CI_PROJECT_ID, GITLAB_TOKEN, CI_SERVER_URL)")
        return
    
    # Génération du rapport
    parser = EcoArchParser(REPORT_PATH)
    report = parser.generate_markdown_report()
    
    # Envoi du commentaire
    url = f"{server_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": token}
    
    try:
        response = requests.post(
            url,
            headers=headers,
            json={"body": report},
            timeout=TIMEOUT_SECONDS,
        )
        
        if response.status_code == 201:
            print("✅ Commentaire posté sur la MR")
        else:
            print(f"❌ Erreur API: {response.status_code} - {response.text}")
            
    except requests.RequestException as e:
        print(f"❌ Erreur réseau: {e}")


if __name__ == "__main__":
    post_gitlab_comment()