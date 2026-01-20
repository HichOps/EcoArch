# infra/main.tf

# On laisse les valeurs vides ici pour les injecter via la CI/CD
# C'est ce qu'on appelle la configuration partielle.
terraform {
  backend "gcs" {
    bucket = "" # Sera injecté par GitLab
    prefix = "" # Sera injecté par GitLab
  }
}

# --- Ressources à créer ---

resource "ecoarch_vm" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = var.boot_disk_image
      size  = var.boot_disk_size
    }
  }

  network_interface {
    network = "default"
    # On peut ajouter access_config {} ici si on veut une IP publique
  }
}