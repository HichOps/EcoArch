resource "google_compute_instance" "demo_vm" {
  name         = var.instance_name
  machine_type = var.machine_type # Variabilisé pour le test FinOps
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = var.boot_disk_image
      size  = var.boot_disk_size # Variabilisé (ex: 50GB)
    }
  }

  network_interface {
    network = "default"
  }

  labels = local.common_labels
}