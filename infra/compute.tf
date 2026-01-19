resource "google_compute_instance" "demo_vm" {
  name         = "ecoarch-test-vm"
  machine_type = "e2-standard-4" # On prend une instance moyenne pour voir le coût
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "debian-cloud/debian-11"
      size  = 50 # 50GB pour générer un coût de stockage
    }
  }

  network_interface {
    network = "default"
  }

  labels = local.common_labels
}