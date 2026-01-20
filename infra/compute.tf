resource "google_compute_instance" "demo_vm" {
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