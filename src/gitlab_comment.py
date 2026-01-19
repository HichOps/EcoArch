import os
import requests
import sys
from parser import EcoArchParser

def post_gitlab_comment():
    # Récupération des variables GitLab CI
    project_id = os.getenv("CI_PROJECT_ID")
    mr_iid = os.getenv("CI_MERGE_REQUEST_IID")
    token = os.getenv("GITLAB_TOKEN")
    server_url = os.getenv("CI_SERVER_URL")

    if not mr_iid:
        print("⏭️ Not a Merge Request pipeline, skipping comment.")
        return

    # Préparation du rapport
    parser = EcoArchParser("infracost-report.json")
    report_content = parser.generate_markdown_report()

    # Appel à l'API GitLab
    url = f"{server_url}/api/v4/projects/{project_id}/merge_requests/{mr_iid}/notes"
    headers = {"PRIVATE-TOKEN": token}
    payload = {"body": report_content}

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 201:
        print("✅ Comment posted successfully on MR!")
    else:
        print(f"❌ Failed to post comment: {response.status_code} - {response.text}")

if __name__ == "__main__":
    post_gitlab_comment()