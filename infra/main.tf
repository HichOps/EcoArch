provider "google" {
  project = var.project_id
  region  = var.region
}

resource "google_compute_instance" "demo_vm" {
  name         = var.instance_name
  machine_type = var.machine_type
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
    }
  }

  network_interface {
    network = "default"
    access_config {
      # Ajoute une IP publique
    }
  }
}