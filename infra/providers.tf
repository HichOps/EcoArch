# Configuration du provider GCP (versions verrouillées)
terraform {
  required_version = ">= 1.10.0"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.15.0" # Verrouillage de la version majeure/mineure
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
  zone    = var.zone
}