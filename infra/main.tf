# infra/main.tf

# On laisse les valeurs vides ici pour les injecter via la CI/CD
# C'est ce qu'on appelle la configuration partielle.
terraform {
  backend "gcs" {
    bucket = "" # Sera injecté par GitLab
    prefix = "" # Sera injecté par GitLab
  }
}