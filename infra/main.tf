# infra/main.tf

terraform {
  # Backend HTTP : le Terraform State est stocké dans GitLab.
  # Les paramètres (address, lock_address, etc.) sont injectés
  # via -backend-config dans le pipeline CI/CD.
  backend "http" {}
}

# ── Décodage du panier EcoArch ────────────────────────────────
# TF_VAR_architecture_json est injecté par le pipeline GitLab
# sous forme de JSON sérialisé.  On le décode ici pour créer
# dynamiquement les ressources demandées par l'utilisateur.

locals {
  common_labels = {
    project     = "ecoarch"
    environment = "test"
    managed_by  = "terraform"
    owner       = "hichops"
  }

  # Décode le JSON du panier utilisateur
  cart = jsondecode(var.architecture_json)

  # Filtrage par type de ressource
  compute_items = [
    for i, item in local.cart : merge(item, { index = i })
    if lookup(item, "type", "") == "compute"
  ]

  sql_items = [
    for i, item in local.cart : merge(item, { index = i })
    if lookup(item, "type", "") == "sql"
  ]

  storage_items = [
    for i, item in local.cart : merge(item, { index = i })
    if lookup(item, "type", "") == "storage"
  ]
}

# ── Compute Engine (VM) ────────────────────────────────────────
resource "google_compute_instance" "vm" {
  count = length(local.compute_items)

  name         = "ea-${var.deployment_id}-vm-${count.index}"
  machine_type = lookup(local.compute_items[count.index], "machine_type", "e2-micro")
  zone         = var.zone
  project      = var.project_id

  boot_disk {
    initialize_params {
      image = var.boot_disk_image
      size  = lookup(local.compute_items[count.index], "disk_size", var.boot_disk_size)
    }
  }

  network_interface {
    network = "default"
    access_config {} # IP publique pour accès SSH / téléchargements
  }

  # ✅ Script de démarrage = logiciel pré-installé (Docker, Nginx, LAMP…)
  metadata_startup_script = lookup(local.compute_items[count.index], "startup_script", "")

  labels = merge(local.common_labels, {
    deployment_id  = var.deployment_id
    software_stack = lookup(local.compute_items[count.index], "software_stack", "none")
  })
}

# ── Cloud SQL ──────────────────────────────────────────────────
resource "google_sql_database_instance" "db" {
  count = length(local.sql_items)

  name             = "ea-${var.deployment_id}-sql-${count.index}"
  database_version = lookup(local.sql_items[count.index], "db_version", "POSTGRES_15")
  region           = var.region
  project          = var.project_id

  deletion_protection = false

  settings {
    tier = lookup(local.sql_items[count.index], "db_tier", "db-f1-micro")

    user_labels = merge(local.common_labels, {
      deployment_id = var.deployment_id
    })
  }
}

# ── Cloud Storage ──────────────────────────────────────────────
resource "google_storage_bucket" "bucket" {
  count = length(local.storage_items)

  name          = "${var.project_id}-ea-${var.deployment_id}-${count.index}"
  location      = var.region
  project       = var.project_id
  storage_class = lookup(local.storage_items[count.index], "storage_class", "STANDARD")

  force_destroy = true

  labels = merge(local.common_labels, {
    deployment_id = var.deployment_id
  })
}