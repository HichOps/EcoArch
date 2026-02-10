# infra/main.tf

terraform {
  # Backend HTTP : le Terraform State est stocké dans GitLab.
  # Les paramètres (address, lock_address, etc.) sont injectés
  # via -backend-config dans le pipeline CI/CD.
  backend "http" {}
}

locals {
  common_labels = {
    project     = "ecoarch"
    environment = "test"
    managed_by  = "terraform"
    owner       = "hichops"
  }
}

resource "google_compute_instance" "ecoarch_vm" {
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
  }

  labels = local.common_labels
}