# Logique de tags/labels (Essentiel pour le FinOps)
locals {
  common_labels = {
    project     = "ecoarch-demo"
    environment = "dev"
    managed_by  = "terraform"
    owner       = "expert-devops"
  }
}